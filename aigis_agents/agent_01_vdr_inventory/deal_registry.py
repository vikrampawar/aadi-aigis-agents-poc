"""
Cross-deal registry and gap delta tracking for Agent 01.

The registry (deals_registry.json) lives at the root of the output directory
alongside the per-deal UUID folders. It accumulates a record of every deal
and every run, enabling:

  1. A human-readable track record of all deals processed.
  2. Gap delta computation when the agent is re-run on the same deal —
     showing which data gaps have been filled, which regressed, and which
     are still outstanding with a days-outstanding count.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from aigis_agents.agent_01_vdr_inventory.models import (
    AgentRegistry,
    AgentRegistryStats,
    ChecklistStatus,
    DealRecord,
    DocumentTier,
    GapDelta,
    GapDeltaItem,
    GapReport,
    RunRecord,
)

REGISTRY_FILENAME = "deals_registry.json"


# ── I/O ───────────────────────────────────────────────────────────────────────

def load_registry(output_dir: Path) -> AgentRegistry:
    """Load deals_registry.json from output_dir. Returns empty registry if absent."""
    path = Path(output_dir) / REGISTRY_FILENAME
    if not path.exists():
        return AgentRegistry()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return AgentRegistry(**data)


def _save_registry(registry: AgentRegistry, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    registry.generated_at = datetime.now(timezone.utc).isoformat()
    path = output_dir / REGISTRY_FILENAME
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry.model_dump(), f, indent=2)


# ── Run Record ────────────────────────────────────────────────────────────────

def _build_run_record(
    gap_report: GapReport,
    cost_usd: float,
    run_output_dir: str,
) -> RunRecord:
    """
    Capture a RunRecord from a GapReport.

    The item_statuses dict (item_id → status string) is the key field —
    it allows compute_gap_delta() to compare any two runs item-by-item.
    """
    s = gap_report.summary
    item_statuses = {item.item_id: item.status.value for item in gap_report.items}
    return RunRecord(
        run_id=str(uuid.uuid4()),
        timestamp=gap_report.run_timestamp,
        checklist_version=gap_report.checklist_version,
        total_files=s.total_files,
        classified=s.high_confidence + s.medium_confidence,
        nth_present=s.present_nth,
        nth_partial=s.partial_nth,
        nth_missing=s.missing_nth,
        gth_present=s.present_gth,
        gth_partial=s.partial_gth,
        gth_missing=s.missing_gth,
        novel_proposals=s.novel_count,
        cost_usd=cost_usd,
        output_dir=run_output_dir,
        item_statuses=item_statuses,
    )


# ── Gap Delta ─────────────────────────────────────────────────────────────────

def compute_gap_delta(
    gap_report: GapReport,
    prev_run: RunRecord,
    curr_run: RunRecord,
) -> GapDelta:
    """
    Compare two consecutive runs on the same deal.

    Classifies every checklist item into one of:
      - gaps_filled:       was missing/partial, now present
      - gaps_opened:       was present, now missing/partial (regression)
      - still_missing_nth: NTH item still missing — with days_outstanding
      - still_partial_nth: NTH item still partial — with days_outstanding
    """
    prev_ts = datetime.fromisoformat(prev_run.timestamp.replace("Z", "+00:00"))
    curr_ts = datetime.fromisoformat(curr_run.timestamp.replace("Z", "+00:00"))
    days_between = max((curr_ts - prev_ts).days, 0)

    # Build item metadata lookup from the current gap_report
    item_meta = {item.item_id: item for item in gap_report.items}

    gaps_filled: list[GapDeltaItem] = []
    gaps_opened: list[GapDeltaItem] = []
    still_missing_nth: list[GapDeltaItem] = []
    still_partial_nth: list[GapDeltaItem] = []

    all_item_ids = set(prev_run.item_statuses) | set(curr_run.item_statuses)

    for item_id in sorted(all_item_ids):
        prev_val = prev_run.item_statuses.get(item_id, "missing")
        curr_val = curr_run.item_statuses.get(item_id, "missing")

        # Skip items not_applicable on both sides
        if prev_val == "not_applicable" and curr_val == "not_applicable":
            continue

        item = item_meta.get(item_id)
        if not item:
            continue

        # Treat not_applicable as present for delta purposes (no gap)
        def _to_status(v: str) -> ChecklistStatus:
            if v == "not_applicable":
                return ChecklistStatus.present
            return ChecklistStatus(v)

        prev_status = _to_status(prev_val)
        curr_status = _to_status(curr_val)

        delta_item = GapDeltaItem(
            item_id=item_id,
            category_label=item.category_label,
            description=item.description,
            tier=item.tier,
            prev_status=prev_status,
            curr_status=curr_status,
            days_outstanding=days_between if curr_status in (
                ChecklistStatus.missing, ChecklistStatus.partial
            ) else None,
        )

        if prev_status == curr_status:
            # No change — only track if it's still an outstanding NTH gap
            if item.tier == DocumentTier.need_to_have:
                if curr_status == ChecklistStatus.missing:
                    still_missing_nth.append(delta_item)
                elif curr_status == ChecklistStatus.partial:
                    still_partial_nth.append(delta_item)
        elif (prev_status in (ChecklistStatus.missing, ChecklistStatus.partial)
              and curr_status == ChecklistStatus.present):
            gaps_filled.append(delta_item)
        elif (prev_status == ChecklistStatus.present
              and curr_status in (ChecklistStatus.missing, ChecklistStatus.partial)):
            gaps_opened.append(delta_item)
        else:
            # Status changed but not a clear fill/open (e.g. partial→missing or missing→partial)
            # Treat as still-outstanding for NTH items
            if item.tier == DocumentTier.need_to_have:
                if curr_status == ChecklistStatus.missing:
                    still_missing_nth.append(delta_item)
                elif curr_status == ChecklistStatus.partial:
                    still_partial_nth.append(delta_item)

    return GapDelta(
        deal_id=gap_report.deal_id,
        deal_name=gap_report.deal_name,
        prev_run_id=prev_run.run_id,
        curr_run_id=curr_run.run_id,
        prev_timestamp=prev_run.timestamp,
        curr_timestamp=curr_run.timestamp,
        days_between_runs=days_between,
        gaps_filled=gaps_filled,
        gaps_opened=gaps_opened,
        still_missing_nth=still_missing_nth,
        still_partial_nth=still_partial_nth,
    )


# ── Main Entry Point ──────────────────────────────────────────────────────────

def register_run(
    gap_report: GapReport,
    cost_usd: float,
    output_dir: Path,
    deal_name: str,
    deal_type: str,
    jurisdiction: str,
    buyer: str | None = None,
) -> GapDelta | None:
    """
    Register a completed run in deals_registry.json.

    - First run for a deal_id: creates a new DealRecord.
    - Repeat run: appends RunRecord, computes and returns a GapDelta.
    - Always updates agent-level aggregate stats.

    Returns GapDelta if this was a repeat run, None if first run.
    """
    output_dir = Path(output_dir)
    registry = load_registry(output_dir)

    run_output_dir = str(output_dir / gap_report.deal_id / "01_vdr_inventory")
    curr_run = _build_run_record(gap_report, cost_usd, run_output_dir)

    gap_delta: GapDelta | None = None
    deal = registry.get_deal(gap_report.deal_id)

    if deal is None:
        # First run for this deal
        deal = DealRecord(
            deal_id=gap_report.deal_id,
            deal_name=deal_name,
            deal_type=deal_type,
            jurisdiction=jurisdiction,
            buyer=buyer,
            first_run_timestamp=gap_report.run_timestamp,
            last_run_timestamp=gap_report.run_timestamp,
            run_count=1,
            runs=[curr_run],
        )
        registry.deals.append(deal)
    else:
        # Repeat run — compute delta against the most recent previous run
        prev_run = deal.runs[-1]
        gap_delta = compute_gap_delta(gap_report, prev_run, curr_run)
        deal.runs.append(curr_run)
        deal.run_count += 1
        deal.last_run_timestamp = gap_report.run_timestamp
        deal.deal_name = deal_name  # allow deal name to be updated

    # Recalculate agent-level stats
    all_runs = [run for d in registry.deals for run in d.runs]
    stats = AgentRegistryStats(
        total_deals=len(registry.deals),
        total_files_reviewed=sum(r.total_files for r in all_runs),
        total_runs=len(all_runs),
        checklist_improvements_contributed=registry.agent_stats.checklist_improvements_contributed,
    )
    timestamps = sorted(r.timestamp for r in all_runs)
    if timestamps:
        stats.first_run_timestamp = timestamps[0]
        stats.last_run_timestamp = timestamps[-1]
    registry.agent_stats = stats

    _save_registry(registry, output_dir)
    return gap_delta
