"""
Domain Knowledge Primer — loader, system prompt builder, and live-VDR updater.

The primer file (agent_01_domain_knowledge_primer.md) is Agent 01's persistent
domain knowledge base. This module handles:

  - Loading the primer at agent startup
  - Building the LangChain SystemMessage from primer content
  - Proposing and appending learned knowledge after each VDR run (additive only)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aigis_agents.agent_01_vdr_inventory.models import (
        ChecklistProposal,
        ClassificationResult,
        GapReport,
    )

PRIMER_PATH = Path(__file__).parent / "agent_01_domain_knowledge_primer.md"

_LEARNED_SECTION_HEADER = "## LEARNED FROM LIVE VDR RUNS"

# Minimum unclassified docs before we bother asking LLM for primer updates
_MIN_UNCLASSIFIED_FOR_UPDATE = 3


# ── Loading ───────────────────────────────────────────────────────────────────

def load_primer() -> str:
    """Load domain knowledge primer from disk. Returns empty string if file missing."""
    if PRIMER_PATH.exists():
        return PRIMER_PATH.read_text(encoding="utf-8")
    return ""


def build_system_prompt(primer_content: str) -> str:
    """
    Wrap primer content as an expert system context string for LangChain SystemMessage.
    """
    return (
        "You are a senior upstream oil & gas M&A due diligence analyst working for "
        "Aigis Analytics. You have extensive domain knowledge about Virtual Data Rooms, "
        "document classification, and due diligence workflows encoded in the primer below. "
        "Apply this knowledge throughout your analysis.\n\n"
        + primer_content
    )


# ── Learning ──────────────────────────────────────────────────────────────────

def propose_primer_updates(
    primer_content: str,
    classifications: list[ClassificationResult],
    proposals: list[ChecklistProposal],
    gap_report: Any,
    deal_id: str,
    deal_type: str,
    jurisdiction: str,
    llm: Any,
    run_timestamp: str,
) -> list[dict]:
    """
    Ask the LLM to identify new domain knowledge from this VDR run.

    Only called when there is something meaningful to learn from:
    - Unclassified documents that couldn't be matched (novel patterns)
    - Novel checklist proposals (new document types encountered)

    Returns a list of proposed primer updates:
        [{"bucket": str, "knowledge_item": str, "rationale": str}]

    Buckets:
        "filename_patterns"    — new filename/path patterns for classification
        "red_flags"            — new automatic escalation triggers
        "quality_signals"      — new positive or negative VDR quality indicators
        "jurisdiction_signals" — new jurisdiction-specific completeness signals
    """
    unclassified = [
        c for c in classifications
        if c.confidence.value == "UNCLASSIFIED" and c.matched_item_id is None
    ]

    # Nothing meaningful to learn — skip the LLM call entirely
    if len(unclassified) < _MIN_UNCLASSIFIED_FOR_UPDATE and not proposals:
        return []

    primer_reference = _extract_primer_reference_sections(primer_content)

    unclassified_summary = "\n".join(
        f"  - {c.file.folder_path}/{c.file.filename}"
        for c in unclassified[:30]
    )
    proposals_summary = "\n".join(
        f"  - [{p.suggested_category}] {p.suggested_item_description}"
        f" (rationale: {p.reasoning[:100]})"
        for p in proposals[:10]
    )

    prompt = f"""You have just completed a VDR document inventory for a {deal_type} asset in {jurisdiction}.

RUN SUMMARY:
- Deal ID: {deal_id[:8]}
- Unclassified documents (not matched to any checklist item): {len(unclassified)}
- Novel checklist proposals generated: {len(proposals)}

UNCLASSIFIED DOCUMENT PATHS (sample, up to 30):
{unclassified_summary or "  (none)"}

NOVEL CHECKLIST PROPOSALS GENERATED:
{proposals_summary or "  (none)"}

CURRENT PRIMER — REFERENCE SECTIONS (filename patterns and red flags already known):
{primer_reference}

TASK:
Based on what you observed in this VDR, identify specific new knowledge items that should
be added to the primer. Focus ONLY on patterns that are:
  1. Genuinely new — not already covered in the reference sections above
  2. Generalisable — would apply to future VDRs of similar type, not just this deal
  3. Actionable — a future analyst could apply the pattern directly

For each new item, assign it to exactly one bucket:
  - "filename_patterns"    → new file naming/path patterns that reliably signal a doc type
  - "red_flags"            → new automatic escalation triggers
  - "quality_signals"      → new positive or negative VDR quality indicators
  - "jurisdiction_signals" → new {jurisdiction}-specific or {deal_type}-specific signals

Return a JSON array. Each object:
  {{"bucket": "...", "knowledge_item": "...", "rationale": "..."}}

  - knowledge_item: ready-to-insert text (concise, 1–3 sentences)
  - rationale: why this was observed and why it generalises (1 sentence)

If there is nothing new to add, return an empty array [].
Return ONLY the JSON array, no other text."""

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        response = llm.invoke([
            SystemMessage(content=build_system_prompt(primer_content)),
            HumanMessage(content=prompt),
        ])
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        updates = json.loads(text.strip())
        # Validate — keep only well-formed entries
        return [
            u for u in updates
            if isinstance(u, dict) and "bucket" in u and "knowledge_item" in u
        ]
    except Exception:
        return []


def apply_primer_updates(
    updates: list[dict],
    primer_content: str,
    run_timestamp: str,
    deal_id: str,
    deal_type: str,
    jurisdiction: str,
) -> str:
    """
    Append learned knowledge to the primer under a persistent
    '## LEARNED FROM LIVE VDR RUNS' section at the end of the file.

    Strictly additive — never modifies the existing primer body.
    Returns the new full primer content.
    """
    if not updates:
        return primer_content

    date_str = datetime.fromisoformat(run_timestamp).strftime("%Y-%m-%d")
    run_header = f"\n### {date_str} | {deal_type} | {jurisdiction} | deal:{deal_id[:8]}\n"

    bucket_labels = {
        "filename_patterns": "**Filename / Classification Patterns**",
        "red_flags": "**Red Flags**",
        "quality_signals": "**Quality Signals**",
        "jurisdiction_signals": "**Jurisdiction Signals**",
    }

    by_bucket: dict[str, list[str]] = {}
    for u in updates:
        bucket = u.get("bucket", "other")
        item = u.get("knowledge_item", "").strip()
        rationale = u.get("rationale", "").strip()
        if not item:
            continue
        entry = f"- {item}"
        if rationale:
            entry += f" *(observed: {rationale})*"
        by_bucket.setdefault(bucket, []).append(entry)

    section_content = run_header
    for bucket, items in by_bucket.items():
        label = bucket_labels.get(bucket, f"**{bucket}**")
        section_content += f"\n{label}\n"
        section_content += "\n".join(items) + "\n"

    if _LEARNED_SECTION_HEADER in primer_content:
        return primer_content + section_content
    else:
        preamble = (
            f"\n\n---\n\n{_LEARNED_SECTION_HEADER}\n\n"
            "*Accumulated knowledge from live VDR analyses. "
            "Each entry is tagged with date, deal type, jurisdiction, and deal ID.*\n"
        )
        return primer_content.rstrip() + preamble + section_content


def save_primer(content: str) -> None:
    """Write updated primer content back to disk."""
    PRIMER_PATH.write_text(content, encoding="utf-8")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_primer_reference_sections(primer_content: str) -> str:
    """
    Extract Sections 6.2 (filename patterns) and Section 10 (red flags) from the
    primer as concise reference context for the update prompt.
    Falls back to the first 40 lines if sections cannot be located.
    """
    if not primer_content:
        return "(primer not loaded)"

    lines = primer_content.splitlines()
    relevant: list[str] = []
    in_target = False

    for line in lines:
        is_target_start = line.startswith("### 6.2") or line.startswith("## SECTION 10")
        is_other_section = (
            line.startswith("## ") or line.startswith("### ")
        ) and not is_target_start

        if is_target_start:
            in_target = True
        elif is_other_section and in_target:
            in_target = False

        if in_target:
            relevant.append(line)

    if not relevant:
        return "\n".join(lines[:40])

    return "\n".join(relevant)
