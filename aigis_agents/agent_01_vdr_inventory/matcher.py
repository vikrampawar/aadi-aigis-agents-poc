"""
3-stage hybrid document matching pipeline.

Stage 1: Keyword match (fast, deterministic, zero LLM cost)
Stage 2: RapidFuzz fuzzy string match (fast, zero LLM cost)
Stage 3: LLM classification (slow, only for uncertain cases)
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from rapidfuzz import fuzz

from aigis_agents.agent_01_vdr_inventory.models import (
    Checklist,
    ChecklistItem,
    ClassificationResult,
    Confidence,
    VDRFile,
)

# Confidence thresholds
FUZZY_HIGH_THRESHOLD = 88
FUZZY_MEDIUM_THRESHOLD = 70

# Max files to send to LLM per batch (to control cost)
LLM_BATCH_SIZE = 20


def _candidate_string(file: VDRFile) -> str:
    """Build a normalised string from filename + folder for matching."""
    # Remove extension, replace underscores/hyphens with spaces
    name = re.sub(r"[_\-]", " ", file.filename)
    name = re.sub(r"\.[a-zA-Z0-9]{1,5}$", "", name)
    folder = re.sub(r"[_/\-\\]", " ", file.folder_path)
    return f"{folder} {name}".lower().strip()


def _keyword_match(
    candidate: str, checklist: Checklist
) -> tuple[ChecklistItem | None, str | None, Confidence]:
    """Stage 1: exact keyword matching against checklist search_keywords."""
    best_item = None
    best_category = None
    best_count = 0

    for cat_key, cat in checklist.categories.items():
        for item in cat.items:
            count = sum(1 for kw in item.search_keywords if kw.lower() in candidate)
            if count > best_count:
                best_count = count
                best_item = item
                best_category = cat_key

    if best_count >= 2:
        return best_item, best_category, Confidence.HIGH
    if best_count == 1:
        return best_item, best_category, Confidence.MEDIUM
    return None, None, Confidence.UNCLASSIFIED


def _fuzzy_match(
    candidate: str, checklist: Checklist
) -> tuple[ChecklistItem | None, str | None, Confidence, float]:
    """Stage 2: RapidFuzz token_set_ratio against item descriptions and keywords."""
    best_item = None
    best_category = None
    best_score = 0.0

    for cat_key, cat in checklist.categories.items():
        for item in cat.items:
            # Match against description
            desc_score = fuzz.token_set_ratio(candidate, item.description.lower())
            # Also match against joined keywords
            kw_string = " ".join(item.search_keywords).lower()
            kw_score = fuzz.token_set_ratio(candidate, kw_string)
            score = max(desc_score, kw_score)

            if score > best_score:
                best_score = score
                best_item = item
                best_category = cat_key

    if best_score >= FUZZY_HIGH_THRESHOLD:
        return best_item, best_category, Confidence.HIGH, best_score
    if best_score >= FUZZY_MEDIUM_THRESHOLD:
        return best_item, best_category, Confidence.MEDIUM, best_score
    return None, None, Confidence.UNCLASSIFIED, best_score


def _llm_classify_batch(
    files: list[VDRFile],
    checklist: Checklist,
    llm: Any,
    primer_content: str | None = None,
) -> list[tuple[str | None, str | None, str]]:
    """
    Stage 3: LLM classification for files that scored below MEDIUM in stages 1+2.
    Returns list of (item_id, category_key, reasoning) per file.
    """
    if not files or llm is None:
        return [(None, None, "LLM not available")] * len(files)

    category_list = [
        f"{cat_key}: {cat.label} — items: {', '.join(i.description for i in cat.items[:3])}..."
        for cat_key, cat in checklist.categories.items()
    ]

    # Build file descriptions list
    file_descs = []
    for i, f in enumerate(files):
        file_descs.append(f"{i+1}. Path: {f.folder_path}/{f.filename}")

    prompt = f"""You are a document classifier for upstream oil and gas M&A due diligence.
Classify each file into the most appropriate checklist category and item.

CHECKLIST CATEGORIES:
{chr(10).join(category_list)}

ITEM DETAILS (abbreviated):
{chr(10).join(
    f"  {cat_key}/{item.id}: {item.description} (keywords: {', '.join(item.search_keywords[:4])})"
    for cat_key, cat in checklist.categories.items()
    for item in cat.items
)}

FILES TO CLASSIFY:
{chr(10).join(file_descs)}

Return a JSON array with one object per file, in the same order:
[{{"item_id": "tech_001", "category_key": "technical", "reasoning": "short explanation"}}, ...]
If a file does not match any checklist item, use: {{"item_id": null, "category_key": null, "reasoning": "not a DD document: [reason]"}}
Return ONLY the JSON array, no other text."""

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = []
        if primer_content:
            from aigis_agents.agent_01_vdr_inventory.primer import build_system_prompt
            messages.append(SystemMessage(content=build_system_prompt(primer_content)))
        messages.append(HumanMessage(content=prompt))
        response = llm.invoke(messages)
        text = response.content.strip()
        # Strip markdown code block if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        import json
        results_raw = json.loads(text.strip())
        results = []
        for r in results_raw:
            results.append((r.get("item_id"), r.get("category_key"), r.get("reasoning", "")))
        return results
    except Exception as e:
        return [(None, None, f"LLM error: {e}")] * len(files)


def _check_outdated(file: VDRFile, item: ChecklistItem) -> bool:
    """Returns True if the document is older than the item's age_threshold_years."""
    if item.age_threshold_years is None:
        return False
    if not file.date_modified:
        return False
    try:
        mod_date = datetime.strptime(file.date_modified, "%Y-%m-%d")
        threshold = datetime.utcnow() - timedelta(days=365 * item.age_threshold_years)
        return mod_date < threshold
    except ValueError:
        return False


def classify_file(
    file: VDRFile,
    checklist: Checklist,
    llm: Any = None,
) -> ClassificationResult:
    """Classify a single file through the 3-stage pipeline."""
    # Files already classified in DB — accept as-is with HIGH confidence
    if file.source.value == "db" and file.classification:
        # Try to find matching checklist item by doc_type
        for cat_key, cat in checklist.categories.items():
            for item in cat.items:
                if file.classification in item.doc_types:
                    return ClassificationResult(
                        file=file,
                        matched_item_id=item.id,
                        matched_category=cat_key,
                        confidence=Confidence.HIGH,
                        match_stage="db",
                    )
        # No checklist item maps to this doc_type
        return ClassificationResult(
            file=file,
            matched_item_id=None,
            matched_category=None,
            confidence=Confidence.LOW,
            match_stage="db",
            llm_reasoning=f"DB doc_type '{file.classification}' has no checklist mapping",
        )

    candidate = _candidate_string(file)

    # Stage 1: keyword
    item, cat_key, conf = _keyword_match(candidate, checklist)
    if conf == Confidence.HIGH:
        is_old = _check_outdated(file, item) if item else False
        return ClassificationResult(
            file=file,
            matched_item_id=item.id if item else None,
            matched_category=cat_key,
            confidence=Confidence.MEDIUM if is_old else Confidence.HIGH,
            match_stage="keyword",
            is_outdated=is_old,
        )

    # Stage 2: fuzzy
    f_item, f_cat, f_conf, f_score = _fuzzy_match(candidate, checklist)
    if f_conf in (Confidence.HIGH, Confidence.MEDIUM):
        # If stage 1 gave MEDIUM and stage 2 gives HIGH, use stage 2 result
        best_item = f_item if f_conf == Confidence.HIGH else (item or f_item)
        best_cat = f_cat if f_conf == Confidence.HIGH else (cat_key or f_cat)
        best_conf = f_conf if f_conf == Confidence.HIGH else Confidence.MEDIUM
        is_old = _check_outdated(file, best_item) if best_item else False
        return ClassificationResult(
            file=file,
            matched_item_id=best_item.id if best_item else None,
            matched_category=best_cat,
            confidence=Confidence.MEDIUM if is_old else best_conf,
            match_stage="fuzzy",
            fuzzy_score=f_score,
            is_outdated=is_old,
        )

    # Stage 1 gave MEDIUM (1 keyword hit) but Stage 2 didn't confirm — preserve Stage 1 result
    if conf == Confidence.MEDIUM and item is not None:
        is_old = _check_outdated(file, item)
        return ClassificationResult(
            file=file,
            matched_item_id=item.id,
            matched_category=cat_key,
            confidence=Confidence.MEDIUM,
            match_stage="keyword",
            fuzzy_score=f_score,
            is_outdated=is_old,
        )

    # Stage 3: LLM (deferred — called via batch_classify)
    return ClassificationResult(
        file=file,
        matched_item_id=None,
        matched_category=None,
        confidence=Confidence.UNCLASSIFIED,
        match_stage="none",
        fuzzy_score=f_score,
    )


def batch_classify(
    files: list[VDRFile],
    checklist: Checklist,
    llm: Any = None,
    primer_content: str | None = None,
) -> list[ClassificationResult]:
    """
    Classify all files. Files that score UNCLASSIFIED after stages 1+2 are
    sent to the LLM in batches. If primer_content is provided it is injected
    as a SystemMessage to prime the LLM with domain knowledge.
    """
    results = [classify_file(f, checklist, llm=None) for f in files]

    # Collect unclassified files for LLM pass
    unclassified_indices = [
        i for i, r in enumerate(results) if r.confidence == Confidence.UNCLASSIFIED
    ]

    if llm and unclassified_indices:
        # Process in batches to control cost
        for batch_start in range(0, len(unclassified_indices), LLM_BATCH_SIZE):
            batch_idx = unclassified_indices[batch_start: batch_start + LLM_BATCH_SIZE]
            batch_files = [files[i] for i in batch_idx]
            llm_results = _llm_classify_batch(batch_files, checklist, llm, primer_content=primer_content)

            for arr_pos, file_idx in enumerate(batch_idx):
                item_id, cat_key, reasoning = llm_results[arr_pos]
                item = checklist.get_item(item_id) if item_id else None
                is_old = _check_outdated(files[file_idx], item) if item else False

                conf = Confidence.MEDIUM if item_id else Confidence.LOW
                if is_old:
                    conf = Confidence.MEDIUM

                results[file_idx] = ClassificationResult(
                    file=files[file_idx],
                    matched_item_id=item_id,
                    matched_category=cat_key,
                    confidence=conf,
                    match_stage="llm",
                    llm_reasoning=reasoning,
                    is_outdated=is_old,
                )

    # Write classification back to the VDRFile object
    for result in results:
        result.file.classification_confidence = result.confidence
        result.file.checklist_item_matched = result.matched_item_id
        result.file.checklist_category = result.matched_category
        result.file.classification_reasoning = result.llm_reasoning

    return results
