"""
AuditLayer — dual-LLM input/output auditing for all Aigis agents.

Every agent run passes through two audit stages:

  1. INPUT AUDIT  (before core logic)
     The audit LLM reviews inputs for completeness, plausibility, unit
     consistency, and purpose alignment.  Any ERROR-severity issue aborts the
     run before any LLM cost is incurred.

  2. OUTPUT AUDIT  (after core logic)
     The audit LLM reviews outputs for citation completeness, internal
     consistency, missed red flags, and value reasonableness.  It also
     generates improvement suggestions for the memory system.

All audit results are appended to {deal_id}/_audit_log.jsonl (one JSON
record per line) so every run has a full, queryable audit trail.

The audit LLM is intentionally the *cheaper* model (default: gpt-4.1-mini)
since the prompts are structured and relatively simple.  The main LLM does
the heavy reasoning and extraction work inside the agent.

Robustness: if the audit LLM returns malformed JSON, the layer falls back to
a permissive default (valid=True for input audit; HIGH confidence for output
audit) so a transient LLM failure never blocks an agent run.  The fallback is
flagged clearly in the audit log.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aigis_agents.mesh.toolkit_registry import ToolkitRegistry

logger = logging.getLogger(__name__)


# ── Prompt templates ───────────────────────────────────────────────────────────

_INPUT_AUDIT_PROMPT = """\
You are the Input Quality Auditor for the Aigis Analytics platform.
You are auditing inputs for: {agent_name}
Agent purpose: {agent_description}
Domain context: Upstream oil & gas M&A due diligence

Inputs received:
{inputs_json}

Review the inputs for ALL of the following:
1. COMPLETENESS — are all required parameters present and non-null?
2. PLAUSIBILITY — are values within reasonable ranges for upstream O&G?
   Examples: production rates (0–100,000 bopd), oil prices ($30–$200/bbl),
   discount rates (5–25%), working interest (0–100%), IRR (0–100%)
3. PURPOSE ALIGNMENT — does this invocation make sense for this agent's role?
4. UNIT CONSISTENCY — flag likely unit mismatches (e.g. bopd vs Mbbl/month,
   MMboe vs Mbbl, USD vs kUSD)

Return ONLY a valid JSON object — no markdown, no explanation outside JSON:
{{
  "valid": true,
  "confidence": "HIGH",
  "issues": [],
  "notes": "Inputs look complete and plausible."
}}

Severity rules:
  "ERROR"   → missing required field or clearly implausible value → sets valid=false
  "WARNING" → suspicious but not definitely wrong → valid stays true
"""

_OUTPUT_AUDIT_PROMPT = """\
You are the Output Quality Auditor for the Aigis Analytics platform.
You are auditing outputs from: {agent_name}
Agent purpose: {agent_description}
Domain context: Upstream oil & gas M&A due diligence

Inputs used (summary):
{inputs_summary}

Outputs produced (summary):
{outputs_summary}

Audit for ALL of the following:
1. CITATION COMPLETENESS — does every extracted fact carry source_doc, section,
   page reference, and confidence level?
2. INTERNAL CONSISTENCY — are outputs internally consistent? Do conclusions
   logically follow from the data?
3. RED FLAG COVERAGE — given upstream O&G DD context, are there obvious risks
   or warning signs that appear to have been missed?
4. REASONABLENESS — are numeric values within expected ranges for this asset
   type and jurisdiction?
5. IMPROVEMENT SUGGESTIONS — specific, actionable changes that would improve
   future runs of this agent (be concrete, not generic)

Return ONLY a valid JSON object — no markdown, no explanation outside JSON:
{{
  "confidence_score": 85,
  "confidence_label": "HIGH",
  "citation_coverage": 0.95,
  "flags": [],
  "improvement_suggestions": [],
  "auditor_notes": "Outputs are complete, well-cited, and internally consistent."
}}

confidence_label: "HIGH" (>=80), "MEDIUM" (60-79), "LOW" (<60)
flag types: "missing_citation", "inconsistency", "missed_red_flag", "out_of_range"
flag severities: "CRITICAL", "WARNING", "INFO"
"""


# ── AuditLayer ─────────────────────────────────────────────────────────────────

class AuditLayer:
    """Input and output auditor. Uses a separate (cheaper) audit LLM."""

    def __init__(self, audit_llm: Any) -> None:
        """
        Args:
            audit_llm: A LangChain chat model instance (e.g. ChatOpenAI).
                       This should be the *cheaper* model (e.g. gpt-4.1-mini).
        """
        self._llm = audit_llm

    # ── Input audit ───────────────────────────────────────────────────────────

    def check_inputs(self, agent_id: str, inputs: dict) -> dict:
        """Audit agent inputs before core logic runs.

        Returns:
            {
              "valid": bool,
              "confidence": "HIGH" | "MEDIUM" | "LOW",
              "issues": [{"field": str, "severity": "ERROR"|"WARNING", "message": str}],
              "notes": str
            }

        If valid=False (any ERROR-severity issue), the caller should abort.
        """
        entry = ToolkitRegistry.get(agent_id)
        prompt = _INPUT_AUDIT_PROMPT.format(
            agent_name=entry["name"],
            agent_description=entry["description"],
            inputs_json=json.dumps(inputs, indent=2, default=str),
        )
        return self._call_audit_llm(prompt, _safe_input_default)

    # ── Output audit ──────────────────────────────────────────────────────────

    def check_outputs(self, agent_id: str, inputs: dict, outputs: dict) -> dict:
        """Audit agent outputs after core logic completes.

        Returns:
            {
              "confidence_score": int (0–100),
              "confidence_label": "HIGH" | "MEDIUM" | "LOW",
              "citation_coverage": float (0.0–1.0),
              "flags": [{"type": str, "severity": str, "detail": str}],
              "improvement_suggestions": [{"target_agent": str, "suggestion": str, "confidence": float}],
              "auditor_notes": str
            }
        """
        entry = ToolkitRegistry.get(agent_id)
        prompt = _OUTPUT_AUDIT_PROMPT.format(
            agent_name=entry["name"],
            agent_description=entry["description"],
            inputs_summary=_summarise(inputs, max_chars=800),
            outputs_summary=_summarise(outputs, max_chars=1200),
        )
        return self._call_audit_llm(prompt, _safe_output_default)

    # ── Audit log ─────────────────────────────────────────────────────────────

    def log(
        self,
        agent_id: str,
        deal_id: str,
        mode: str,
        inputs: dict,
        input_audit: dict,
        output_audit: dict,
        main_model: str,
        audit_model: str,
        cost: dict | None = None,
        output_dir: str | Path = "./outputs",
    ) -> str:
        """Append one audit record to {output_dir}/{deal_id}/_audit_log.jsonl.

        Returns the run_id used for this record.
        """
        run_id = str(uuid.uuid4())[:8]
        record = {
            "run_id":       run_id,
            "agent":        agent_id,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "mode":         mode,
            "main_model":   main_model,
            "audit_model":  audit_model,
            "input_audit":  input_audit,
            "output_audit": output_audit,
            "cost":         cost or {},
        }

        log_path = Path(output_dir) / deal_id / "_audit_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return run_id

    # ── Internal ──────────────────────────────────────────────────────────────

    def _call_audit_llm(self, prompt: str, fallback_factory) -> dict:
        """Call the audit LLM with *prompt* and parse the JSON response.

        Falls back to fallback_factory() if the LLM returns invalid JSON or
        raises an exception.
        """
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=(
                    "You are a precision JSON output machine. "
                    "Always return valid JSON only. No markdown fences, no explanation outside the JSON."
                )),
                HumanMessage(content=prompt),
            ]
            response = self._llm.invoke(messages)
            raw = response.content if hasattr(response, "content") else str(response)
            return _parse_json_response(raw, fallback_factory)
        except Exception as exc:
            logger.warning("Audit LLM call failed: %s — using safe default.", exc)
            result = fallback_factory()
            result["_audit_fallback"] = True
            result["_audit_error"]    = str(exc)
            return result


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_json_response(raw: str, fallback_factory) -> dict:
    """Extract JSON from the LLM response string."""
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first {...} block
        start = text.find("{")
        end   = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

    logger.warning("Could not parse audit LLM response as JSON. Using fallback.")
    result = fallback_factory()
    result["_audit_fallback"]      = True
    result["_raw_audit_response"]  = raw[:500]   # cap length in log
    return result


def _safe_input_default() -> dict:
    """Safe default for a failed input audit — allows the run to proceed."""
    return {
        "valid":      True,
        "confidence": "LOW",
        "issues":     [],
        "notes":      "Audit LLM unavailable — defaulting to permissive pass.",
    }


def _safe_output_default() -> dict:
    """Safe default for a failed output audit — marks confidence LOW."""
    return {
        "confidence_score":      50,
        "confidence_label":      "LOW",
        "citation_coverage":     0.0,
        "flags":                 [],
        "improvement_suggestions": [],
        "auditor_notes":         "Audit LLM unavailable — output not verified.",
    }


def _summarise(data: dict, max_chars: int = 1000) -> str:
    """Compact JSON summary of *data*, truncated to *max_chars*."""
    try:
        text = json.dumps(data, indent=2, default=str)
    except (TypeError, ValueError):
        text = str(data)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [truncated]"
    return text
