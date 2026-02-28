"""
Self-learning novelty detector.

Identifies VDR documents that were not matched to any checklist item with
≥ MEDIUM confidence. Groups similar unmatched files and asks the LLM whether
they should be added to the gold-standard checklist.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from rapidfuzz import fuzz

from aigis_agents.agent_01_vdr_inventory.models import (
    Checklist,
    ChecklistProposal,
    ClassificationResult,
    Confidence,
    DealType,
    DocumentTier,
    VDRFile,
)

# Two files with filename similarity ≥ this threshold are grouped together
_GROUPING_THRESHOLD = 75


def _group_unmatched(files: list[VDRFile]) -> list[list[VDRFile]]:
    """Cluster unmatched files by filename similarity + folder proximity."""
    groups: list[list[VDRFile]] = []
    assigned = set()

    for i, f in enumerate(files):
        if i in assigned:
            continue
        group = [f]
        assigned.add(i)
        for j, g in enumerate(files):
            if j <= i or j in assigned:
                continue
            # Same folder or high filename similarity
            same_folder = f.folder_path.lower() == g.folder_path.lower()
            name_sim = fuzz.token_set_ratio(f.filename.lower(), g.filename.lower())
            if same_folder or name_sim >= _GROUPING_THRESHOLD:
                group.append(g)
                assigned.add(j)
        groups.append(group)
    return groups


def _build_llm_prompt(groups: list[list[VDRFile]], checklist: Checklist, deal_type: str) -> str:
    category_list = [f"  - {cat_key}: {cat.label}" for cat_key, cat in checklist.categories.items()]

    group_descriptions = []
    for i, grp in enumerate(groups):
        examples = ", ".join(f.filename for f in grp[:3])
        folder = grp[0].folder_path or "(root)"
        group_descriptions.append(f"{i+1}. Folder: {folder} | Examples: {examples} ({len(grp)} file(s))")

    return f"""You are a senior upstream oil & gas M&A analyst reviewing a Virtual Data Room.

The following document groups were found in the VDR but do NOT match any item in our current
gold-standard due diligence checklist. Please review each group and decide:

1. Should this type of document be ADDED to the gold-standard checklist?
2. If yes: which category, what description, what tier (need_to_have / good_to_have)?
3. Which deal types is it relevant for? (producing_asset, exploration, development, corporate)

EXISTING CHECKLIST CATEGORIES:
{chr(10).join(category_list)}

CURRENT DEAL TYPE: {deal_type}

UNMATCHED DOCUMENT GROUPS:
{chr(10).join(group_descriptions)}

Return a JSON array — one object per group, in the same order.
For groups that SHOULD be added:
{{
  "group_index": 1,
  "add_to_checklist": true,
  "suggested_category": "financial",
  "suggested_item_description": "Seller's information memorandum financial appendix",
  "suggested_tier": "need_to_have",
  "applicable_deal_types": ["producing_asset", "development"],
  "reasoning": "This type of document provides..."
}}
For groups that should NOT be added (deal-specific, duplicates, system files):
{{
  "group_index": 2,
  "add_to_checklist": false,
  "reasoning": "Deal-specific correspondence not relevant to future VDRs"
}}
Return ONLY the JSON array, no other text."""


def detect_novel_documents(
    classifications: list[ClassificationResult],
    checklist: Checklist,
    deal_id: str,
    deal_type: str,
    run_timestamp: str,
    llm: Any = None,
    primer_content: str | None = None,
) -> list[ChecklistProposal]:
    """
    Find unmatched/LOW-confidence files, group them, and use LLM to propose
    checklist additions. Returns list of ChecklistProposal objects.
    """
    # Find files with LOW or UNCLASSIFIED confidence (not matched to checklist)
    unmatched = [
        r.file
        for r in classifications
        if r.confidence in (Confidence.LOW, Confidence.UNCLASSIFIED)
        and r.matched_item_id is None
    ]

    if not unmatched or llm is None:
        return []

    groups = _group_unmatched(unmatched)
    if not groups:
        return []

    # Only process groups with ≥ 1 file (trivially true, but filter noise)
    substantive_groups = [g for g in groups if g]

    prompt = _build_llm_prompt(substantive_groups, checklist, deal_type)

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = []
        if primer_content:
            from aigis_agents.agent_01_vdr_inventory.primer import build_system_prompt
            messages.append(SystemMessage(content=build_system_prompt(primer_content)))
        messages.append(HumanMessage(content=prompt))
        response = llm.invoke(messages)
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        raw_results = json.loads(text.strip())
    except Exception:
        return []

    proposals: list[ChecklistProposal] = []
    for r in raw_results:
        if not r.get("add_to_checklist", False):
            continue
        idx = r.get("group_index", 1) - 1
        if idx < 0 or idx >= len(substantive_groups):
            continue
        group = substantive_groups[idx]

        raw_tier = r.get("suggested_tier", "good_to_have")
        try:
            tier = DocumentTier(raw_tier)
        except ValueError:
            tier = DocumentTier.good_to_have

        raw_deal_types = r.get("applicable_deal_types", [deal_type])
        applicable = []
        for dt in raw_deal_types:
            try:
                applicable.append(DealType(dt))
            except ValueError:
                pass
        if not applicable:
            applicable = [DealType(deal_type)]

        proposals.append(
            ChecklistProposal(
                proposal_id=str(uuid.uuid4()),
                deal_id=deal_id,
                run_timestamp=run_timestamp,
                filenames=[f.filename for f in group[:5]],
                folder_path=group[0].folder_path,
                suggested_category=r.get("suggested_category", "other"),
                suggested_item_description=r.get("suggested_item_description", "Unknown"),
                suggested_tier=tier,
                applicable_deal_types=applicable,
                reasoning=r.get("reasoning", ""),
            )
        )

    return proposals
