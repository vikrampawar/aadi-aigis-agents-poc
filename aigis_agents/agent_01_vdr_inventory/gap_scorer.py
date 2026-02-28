"""
Gap scorer: maps ClassificationResults to checklist statuses.
Produces a GapReport with ✅/⚠️/❌ per item and NTH/GTH tier.
"""

from __future__ import annotations

from aigis_agents.agent_01_vdr_inventory.models import (
    Checklist,
    ChecklistItemResult,
    ChecklistStatus,
    ClassificationResult,
    Confidence,
    DealType,
    DocumentTier,
    GapReport,
    GapReportSummary,
    Jurisdiction,
    VDRFile,
)


def _is_applicable(item, deal_type: str, jurisdiction: str) -> bool:
    """Returns True if this checklist item applies to the given deal_type + jurisdiction."""
    deal_types_in_tier = set(item.tier.keys())
    if deal_type not in deal_types_in_tier:
        return False
    # Check jurisdiction
    if "all" in item.jurisdictions:
        return True
    return jurisdiction in item.jurisdictions


def _get_tier(item, deal_type: str) -> DocumentTier:
    """Look up NTH/GTH tier for this item given the deal_type."""
    return item.tier.get(deal_type, DocumentTier.good_to_have)


def score_checklist(
    classifications: list[ClassificationResult],
    checklist: Checklist,
    deal_type: str,
    jurisdiction: str,
    deal_id: str,
    deal_name: str,
    run_timestamp: str,
) -> GapReport:
    """
    For each checklist item, determine ✅/⚠️/❌ based on classification results.
    Returns a full GapReport with tier, status, matched files, and summary.
    """
    # Build lookup: item_id → list of matching ClassificationResults
    item_matches: dict[str, list[ClassificationResult]] = {}
    for r in classifications:
        if r.matched_item_id:
            item_matches.setdefault(r.matched_item_id, []).append(r)

    item_results: list[ChecklistItemResult] = []
    summary = GapReportSummary(total_files=len(classifications))
    low_confidence_files: list[VDRFile] = []

    for cat_key, cat in checklist.categories.items():
        for item in cat.items:
            if not _is_applicable(item, deal_type, jurisdiction):
                item_results.append(
                    ChecklistItemResult(
                        item_id=item.id,
                        category_key=cat_key,
                        category_label=cat.label,
                        description=item.description,
                        tier=_get_tier(item, deal_type),
                        status=ChecklistStatus.not_applicable,
                        notes=f"Not required for {deal_type} / {jurisdiction}",
                    )
                )
                continue

            tier = _get_tier(item, deal_type)
            matches = item_matches.get(item.id, [])

            # Determine status
            if not matches:
                status = ChecklistStatus.missing
            else:
                high_matches = [m for m in matches if m.confidence == Confidence.HIGH and not m.is_outdated]
                if high_matches:
                    status = ChecklistStatus.present
                else:
                    # Only MEDIUM matches or outdated HIGH matches → Partial
                    status = ChecklistStatus.partial

            matched_files = [m.file for m in matches]

            item_results.append(
                ChecklistItemResult(
                    item_id=item.id,
                    category_key=cat_key,
                    category_label=cat.label,
                    description=item.description,
                    tier=tier,
                    status=status,
                    matched_files=matched_files,
                    notes=item.notes,
                    drl_request_text=item.drl_request_text,
                )
            )

            # Update summary counts
            if tier == DocumentTier.need_to_have:
                if status == ChecklistStatus.present:
                    summary.present_nth += 1
                elif status == ChecklistStatus.partial:
                    summary.partial_nth += 1
                elif status == ChecklistStatus.missing:
                    summary.missing_nth += 1
            else:  # good_to_have
                if status == ChecklistStatus.present:
                    summary.present_gth += 1
                elif status == ChecklistStatus.partial:
                    summary.partial_gth += 1
                elif status == ChecklistStatus.missing:
                    summary.missing_gth += 1

    # Confidence stats
    for r in classifications:
        if r.confidence == Confidence.HIGH:
            summary.high_confidence += 1
        elif r.confidence == Confidence.MEDIUM:
            summary.medium_confidence += 1
        elif r.confidence == Confidence.LOW:
            summary.low_confidence += 1
            low_confidence_files.append(r.file)
        else:
            summary.unclassified += 1
            low_confidence_files.append(r.file)

    return GapReport(
        deal_id=deal_id,
        deal_name=deal_name,
        deal_type=DealType(deal_type),
        jurisdiction=Jurisdiction(jurisdiction),
        checklist_version=checklist.version,
        run_timestamp=run_timestamp,
        summary=summary,
        items=item_results,
        low_confidence_files=low_confidence_files,
    )
