"""
AgentBase — Base class for all Aigis agents.

Every agent in the mesh inherits from AgentBase and only needs to:
  1. Set AGENT_ID = "agent_XX" (class-level)
  2. Set DK_TAGS = [...] (class-level)
  3. Implement _run(deal_id, main_llm, dk_context, patterns, **inputs) -> dict

AgentBase.invoke() handles the full pipeline:
  1.   Resolve models (from params → toolkit defaults)
  2.   Resolve API keys (from params → env vars)
  3.   Instantiate main LLM + audit LLM
  4.   Input audit (abort if any ERROR-severity issue)
  5.   Load domain knowledge (SemanticDKRouter: tag phase always + semantic phase if configured)
  5.5  Load buyer profile context
  5.6  Load deal context (per-deal accumulating markdown)
  6.   Load memory patterns
  7.   Run core logic (_run)
  7.5  Extract _deal_context_section internal key (before audit)
  8.   Output audit
  9.   Queue improvement suggestions for human review
  9.5  Detect buyer preference signals; prompt "Remember this?" in standalone mode
  10.  Log to deal audit trail
  10.5 Update deal context (if agent returned _deal_context_section)
  11.  Format and return (mode-dependent)

Cross-agent calls:
    result = self.call_agent("agent_01", deal_id="...", **inputs)

The caller inherits its own audit_model for the callee's audit layer.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from aigis_agents.mesh.audit_layer import AuditLayer
from aigis_agents.mesh.buyer_profile_manager import BuyerProfileManager
from aigis_agents.mesh.deal_context import DealContextManager, DealContextSection
from aigis_agents.mesh.memory_manager import MemoryManager
from aigis_agents.mesh.semantic_dk_router import SemanticDKRouter
from aigis_agents.mesh.toolkit_registry import ToolkitRegistry
from aigis_agents.shared.llm_bridge import get_chat_model

logger = logging.getLogger(__name__)

# Single session-scoped singletons shared by all agents
_dk_router     = SemanticDKRouter()   # wraps DomainKnowledgeRouter; falls back to tag-only
_memory        = MemoryManager()
_buyer_profile = BuyerProfileManager()


class AgentBase:
    """Abstract base for all Aigis agents.  Subclasses set AGENT_ID and DK_TAGS
    and implement _run().  Everything else is handled here.
    """

    AGENT_ID: str = ""
    DK_TAGS:  list[str] = []

    def __init__(self) -> None:
        if not self.AGENT_ID:
            raise ValueError(
                f"{self.__class__.__name__} must define AGENT_ID as a non-empty class attribute."
            )
        self._dk_router     = _dk_router
        self._memory        = _memory
        self._buyer_profile = _buyer_profile

    # ── Public API ─────────────────────────────────────────────────────────────

    def invoke(
        self,
        mode: str,                           # "standalone" | "tool_call"
        deal_id: str,
        main_model:    str | None = None,    # falls back to toolkit default
        main_api_key:  str | None = None,    # falls back to OPENAI_API_KEY env var
        audit_model:   str | None = None,    # falls back to toolkit default
        audit_api_key: str | None = None,    # falls back to OPENAI_API_KEY env var
        output_dir:    str = "./outputs",
        refresh_dk:    bool = False,         # force domain knowledge reload
        **inputs: Any,
    ) -> dict:
        """Run the agent through the full 10-step mesh pipeline.

        Returns:
            On success: a mode-appropriate dict (see _format_output)
            On input validation failure: an error dict (no LLM cost incurred)
            On execution error: an error dict with traceback details
        """
        start_ts = time.monotonic()

        # ── 1 & 2: Resolve models and API keys ────────────────────────────────
        defaults     = ToolkitRegistry.llm_defaults(self.AGENT_ID)
        _main_model  = main_model  or defaults.get("main_model",  "gpt-4.1")
        _audit_model = audit_model or defaults.get("audit_model", "gpt-4.1-mini")

        # ── 3: Instantiate LLMs ───────────────────────────────────────────────
        main_llm  = get_chat_model(_main_model,  session_keys={"OPENAI_API_KEY": main_api_key}  if main_api_key  else None)
        audit_llm = get_chat_model(_audit_model, session_keys={"OPENAI_API_KEY": audit_api_key} if audit_api_key else None)
        audit_layer = AuditLayer(audit_llm)

        # ── 4: Input audit ────────────────────────────────────────────────────
        input_audit = audit_layer.check_inputs(self.AGENT_ID, inputs)
        if not input_audit.get("valid", True):
            return self._error_response(
                "input_validation_failed",
                "Input audit failed — aborting before any LLM cost.",
                {"issues": input_audit.get("issues", [])},
            )

        # ── 5: Load domain knowledge ──────────────────────────────────────────
        # query derived from tags: used by SemanticDKRouter for Phase 2 search
        _dk_query = " ".join(self.DK_TAGS) if self.DK_TAGS else None
        dk_context = self._dk_router.build_context_block(
            self.DK_TAGS, refresh=refresh_dk, query=_dk_query
        )

        # ── 5.5: Load buyer profile context ───────────────────────────────────
        buyer_context = self._buyer_profile.load_as_context()

        # ── 5.6: Load deal context (per-deal accumulating markdown) ───────────
        deal_context_mgr = DealContextManager(deal_id=deal_id)
        deal_context = deal_context_mgr.load()

        # ── 5.7: Load entity context from concept graph ────────────────────────
        entity_context = ""
        try:
            from pathlib import Path as _Path
            from aigis_agents.mesh.concept_graph import ConceptGraph
            _cg_path = _Path(output_dir) / deal_id / "02_data_store.db"
            entity_context = ConceptGraph(_cg_path).get_deal_context_summary(deal_id)
        except Exception as _exc:
            logger.debug("Step 5.7 entity context load failed (non-blocking): %s", _exc)

        # ── 6: Load memory patterns ───────────────────────────────────────────
        patterns = self._memory.load_patterns(self.AGENT_ID)

        # ── 7: Core logic (_run) ──────────────────────────────────────────────
        try:
            raw_output = self._run(
                deal_id=deal_id,
                main_llm=main_llm,
                dk_context=dk_context,
                buyer_context=buyer_context,
                deal_context=deal_context,
                entity_context=entity_context,
                patterns=patterns,
                mode=mode,
                output_dir=output_dir,
                **inputs,
            )
        except Exception as exc:
            logger.exception("Agent %s _run() raised an exception.", self.AGENT_ID)
            return self._error_response(
                "execution_error",
                str(exc),
                {},
            )

        # ── 7.5: Extract internal metadata before audit ───────────────────────
        _dc_section = raw_output.pop("_deal_context_section", None)

        # ── 8: Output audit ───────────────────────────────────────────────────
        output_audit = audit_layer.check_outputs(self.AGENT_ID, inputs, raw_output)

        # ── 9: Queue improvement suggestions for human review ─────────────────
        for suggestion in output_audit.get("improvement_suggestions", []):
            enriched = {
                **suggestion,
                "from_agent": self.AGENT_ID,
                "deal_id":    deal_id,
            }
            try:
                sid = self._memory.queue_suggestion(enriched)
                logger.debug("Queued improvement suggestion %s for review.", sid)
            except Exception as exc:
                logger.warning("Failed to queue suggestion: %s", exc)

        # ── 9.5: Detect buyer preference signals; prompt to remember ─────────────
        if mode == "standalone":
            try:
                signals = audit_layer.detect_preferences(inputs, raw_output)
                for signal in signals:
                    if signal.confidence >= 0.75:
                        try:
                            confirm = input(
                                f"\n[Buyer Profile] Detected preference: "
                                f"'{signal.value}' for '{signal.key}'.\n"
                                f"Remember this for future runs? [y/N]: "
                            )
                            if confirm.strip().lower() == "y":
                                self._buyer_profile.apply_signal(signal)
                                logger.info(
                                    "Buyer preference saved: %s = %s",
                                    signal.key, signal.value,
                                )
                        except (EOFError, OSError):
                            # Non-interactive context (CI, piped stdin) — skip prompt
                            pass
            except Exception as exc:
                logger.debug("Step 9.5 preference detection failed (non-blocking): %s", exc)

        # ── 10: Log to audit trail ─────────────────────────────────────────────
        duration_s = round(time.monotonic() - start_ts, 2)
        run_id = audit_layer.log(
            agent_id=self.AGENT_ID,
            deal_id=deal_id,
            mode=mode,
            inputs=inputs,
            input_audit=input_audit,
            output_audit=output_audit,
            main_model=_main_model,
            audit_model=_audit_model,
            cost=raw_output.pop("_cost", None),   # agents may embed cost in output
            output_dir=output_dir,
        )

        # Also log to run history
        self._memory.log_run(self.AGENT_ID, {
            "run_id":       run_id,
            "deal_id":      deal_id,
            "mode":         mode,
            "timestamp":    _now(),
            "audit_score":  output_audit.get("confidence_score", 0),
            "duration_s":   duration_s,
            "main_model":   _main_model,
            "audit_model":  _audit_model,
        })

        # ── 10.5: Update deal context ──────────────────────────────────────────
        if _dc_section and isinstance(_dc_section, dict):
            try:
                section = DealContextSection(
                    agent_id=self.AGENT_ID,
                    section_name=_dc_section.get("section_name", self.AGENT_ID),
                    content=_dc_section.get("content", ""),
                    updated_at=_now(),
                    run_id=run_id,
                )
                deal_context_mgr.update_section(section)
                flags_list = [
                    f.get("message", str(f))
                    for f in raw_output.get("flags", [])
                    if isinstance(f, dict)
                ]
                deal_context_mgr.append_run_log(
                    agent_id=self.AGENT_ID,
                    run_id=run_id,
                    flags=flags_list[:3],
                    summary=_dc_section.get("content", "")[:120],
                )
                logger.debug("Deal context updated by %s (run %s).", self.AGENT_ID, run_id)
            except Exception as exc:
                logger.debug("Step 10.5 deal context update failed (non-blocking): %s", exc)

        # ── 11: Format and return ─────────────────────────────────────────────
        return self._format_output(
            mode=mode,
            deal_id=deal_id,
            run_id=run_id,
            raw_output=raw_output,
            output_audit=output_audit,
            main_model=_main_model,
            audit_model=_audit_model,
            duration_s=duration_s,
            input_warnings=[
                i for i in input_audit.get("issues", [])
                if i.get("severity") == "WARNING"
            ],
        )

    def call_agent(
        self,
        agent_id:   str,
        deal_id:    str,
        main_model: str | None = None,
        **inputs: Any,
    ) -> dict:
        """Call another registered agent in tool_call mode.

        Inherits audit_model defaults from the target agent's toolkit entry.
        The caller is responsible for handling any error responses.
        """
        agent_cls = ToolkitRegistry.get_agent_class(agent_id)
        if agent_cls is None:
            raise ValueError(
                f"Agent '{agent_id}' is not yet migrated to AgentBase "
                f"(mesh_class is null in toolkit.json). "
                f"Use ToolkitRegistry.get_invoke_fn('{agent_id}') for legacy invocation."
            )
        return agent_cls().invoke(
            mode="tool_call",
            deal_id=deal_id,
            main_model=main_model,
            **inputs,
        )

    # ── Abstract ───────────────────────────────────────────────────────────────

    def _run(
        self,
        deal_id:        str,
        main_llm:       Any,
        dk_context:     str,
        buyer_context:  str,
        deal_context:   str,
        entity_context: str,
        patterns:       list[dict],
        mode:           str = "standalone",
        output_dir:     str = "./outputs",
        **inputs: Any,
    ) -> dict:
        """Core agent logic.  Must be overridden by each agent subclass.

        Args:
            deal_id:        The deal UUID.
            main_llm:       Instantiated LangChain chat model for core reasoning.
            dk_context:     Formatted domain knowledge block for prompt injection.
            buyer_context:  Buyer profile markdown for prompt injection.
            deal_context:   Per-deal accumulating context markdown for prompt injection.
            entity_context: Concept graph summary (entities + facts) for prompt injection.
            patterns:       List of confirmed learned patterns from memory.
            mode:           "standalone" (write files) or "tool_call" (no file I/O).
            output_dir:     Root output directory (relevant in standalone mode).
            **inputs:       All caller-supplied inputs (validated by audit layer).

        Returns:
            A dict of raw outputs.  May optionally include:
              "_cost": {"main_llm_usd": float, "audit_llm_usd": float, "total_usd": float}
                  — popped by AgentBase and included in the audit log.
              "_deal_context_section": {"section_name": str, "content": str}
                  — popped by AgentBase and used to update deal_context.md (step 10.5).
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _run()."
        )

    # ── Output formatting ──────────────────────────────────────────────────────

    def _format_output(
        self,
        mode:          str,
        deal_id:       str,
        run_id:        str,
        raw_output:    dict,
        output_audit:  dict,
        main_model:    str,
        audit_model:   str,
        duration_s:    float,
        input_warnings: list[dict],
    ) -> dict:
        """Wrap raw_output in the standard mesh response envelope.

        tool_call mode: compact JSON, no file writes
        standalone mode: same envelope (file writes are the agent's responsibility
                         inside _run(); the envelope is returned to the caller)
        """
        audit_block = {
            "input_valid":        True,
            "input_warnings":     input_warnings,
            "output_confidence":  output_audit.get("confidence_label", "UNKNOWN"),
            "output_score":       output_audit.get("confidence_score", 0),
            "citation_coverage":  output_audit.get("citation_coverage", 0.0),
            "flags":              output_audit.get("flags", []),
            "main_model":         main_model,
            "audit_model":        audit_model,
        }

        return {
            "agent":        self.AGENT_ID,
            "status":       "success",
            "deal_id":      deal_id,
            "run_id":       run_id,
            "data":         raw_output,
            "audit":        audit_block,
            "run_metadata": {
                "duration_s": duration_s,
                "mode":       mode,
            },
        }

    # ── Error response ─────────────────────────────────────────────────────────

    def _error_response(
        self,
        error_type: str,
        message:    str,
        details:    dict,
    ) -> dict:
        """Standard error envelope returned on any failure path."""
        return {
            "agent":      self.AGENT_ID,
            "status":     "error",
            "error_type": error_type,
            "message":    message,
            "details":    details,
        }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
