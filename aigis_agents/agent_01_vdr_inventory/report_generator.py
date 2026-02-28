"""
Markdown gap analysis report generator.

Renders the GapReport into a structured Markdown file with:
  Gap Tracker: Changes since last run (only on re-runs)
  Section 1: NTH Missing (❌) — Critical
  Section 2: NTH Partial (⚠️)
  Section 3: GTH Missing (❌)
  Section 4: GTH Partial (⚠️)
  Section 5: Present (✅)
  Section 6: Checklist Evolution Proposals
  Appendix:  Full VDR Inventory
"""

from __future__ import annotations

from pathlib import Path

from aigis_agents.agent_01_vdr_inventory.models import (
    ChecklistItemResult,
    ChecklistProposal,
    GapDelta,
    ChecklistStatus,
    DocumentTier,
    GapReport,
)

_DEAL_TYPE_LABELS = {
    "producing_asset": "Producing Asset",
    "exploration": "Exploration",
    "development": "Development",
    "corporate": "Corporate",
}

_STATUS_EMOJI = {
    ChecklistStatus.present: "✅",
    ChecklistStatus.partial: "⚠️",
    ChecklistStatus.missing: "❌",
    ChecklistStatus.not_applicable: "—",
}


def _format_item(item: ChecklistItemResult, show_files: bool = True) -> str:
    lines = []
    status_emoji = _STATUS_EMOJI.get(item.status, "?")
    lines.append(f"#### `{item.item_id}` — {item.description}")
    lines.append(f"**Status:** {status_emoji} {item.status.value.replace('_', ' ').title()}  "
                 f"**Category:** {item.category_label}")

    if show_files and item.matched_files:
        file_list = ", ".join(
            f"`{f.filename}`" + (f" ({f.folder_path})" if f.folder_path else "")
            for f in item.matched_files[:3]
        )
        if len(item.matched_files) > 3:
            file_list += f" _+ {len(item.matched_files) - 3} more_"
        lines.append(f"**Matched files:** {file_list}")

    if item.notes:
        lines.append(f"**Note:** _{item.notes}_")

    return "\n".join(lines)


def _render_gap_tracker(gap_delta: GapDelta) -> list[str]:
    """Render the Gap Tracker section for re-runs. Returns markdown lines."""
    lines: list[str] = []
    d = gap_delta
    days_label = f"{d.days_between_runs} day{'s' if d.days_between_runs != 1 else ''} ago"
    prev_date = d.prev_timestamp[:10]

    lines += [
        f"## Gap Tracker — Changes Since Last Run ({days_label}, {prev_date})",
        "",
    ]

    # Summary callout
    filled = len(d.gaps_filled)
    opened = len(d.gaps_opened)
    outstanding = len(d.still_missing_nth) + len(d.still_partial_nth)
    fill_icon = "✅" if filled > 0 else "—"
    open_icon = "🔴" if opened > 0 else "✅"
    lines.append(
        f"> {fill_icon} **{filled} gap(s) filled**  |  "
        f"{open_icon} **{opened} regression(s)**  |  "
        f"📋 **{outstanding} NTH item(s) still outstanding**"
    )
    lines.append("")

    # Gaps filled
    lines.append("### Newly Received ✅")
    lines.append("")
    if d.gaps_filled:
        lines += [
            "| Item | Category | Was | Now | Days to Receive |",
            "|------|----------|-----|-----|-----------------|",
        ]
        for item in d.gaps_filled:
            lines.append(
                f"| `{item.item_id}` {item.description} | {item.category_label} "
                f"| {item.prev_status.value} | {item.curr_status.value} "
                f"| {d.days_between_runs} |"
            )
    else:
        lines.append("_No new documents received since last run._")
    lines.append("")

    # Regressions
    lines.append("### Regressions ⚠️ _(previously present, now missing or partial)_")
    lines.append("")
    if d.gaps_opened:
        lines += [
            "| Item | Category | Was | Now |",
            "|------|----------|-----|-----|",
        ]
        for item in d.gaps_opened:
            lines.append(
                f"| `{item.item_id}` {item.description} | {item.category_label} "
                f"| {item.prev_status.value} | {item.curr_status.value} |"
            )
    else:
        lines.append("_No regressions — all previously present items remain confirmed._")
    lines.append("")

    # Still outstanding NTH
    still_outstanding = d.still_missing_nth + d.still_partial_nth
    lines.append("### Still Outstanding — Need to Have")
    lines.append("")
    if still_outstanding:
        lines += [
            "| Item | Category | Status | Days Outstanding |",
            "|------|----------|--------|-----------------|",
        ]
        for item in still_outstanding:
            status_icon = "❌" if item.curr_status.value == "missing" else "⚠️"
            lines.append(
                f"| `{item.item_id}` {item.description} | {item.category_label} "
                f"| {status_icon} {item.curr_status.value} "
                f"| {item.days_outstanding or d.days_between_runs} days |"
            )
    else:
        lines.append("_All Need-to-Have items are now present or not applicable._")
    lines += ["", "---", ""]

    return lines


def generate_gap_report(
    gap_report: GapReport,
    proposals: list[ChecklistProposal],
    output_path: Path,
    gap_delta: GapDelta | None = None,
) -> Path:
    """Write the gap analysis Markdown report. Returns the output file path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    s = gap_report.summary
    deal_type_label = _DEAL_TYPE_LABELS.get(gap_report.deal_type.value, gap_report.deal_type.value)
    run_date = gap_report.run_timestamp[:10]

    lines: list[str] = []

    # ── Header ──────────────────────────────────────────────────────────────
    lines += [
        f"# VDR Gap Analysis — {gap_report.deal_name} — {run_date}",
        "",
        f"**Deal Type:** {deal_type_label} | "
        f"**Jurisdiction:** {gap_report.jurisdiction.value} | "
        f"**Checklist:** {gap_report.checklist_version} | "
        f"**Deal ID:** `{gap_report.deal_id}`",
        "",
        "---",
        "",
    ]

    # ── Executive Summary ────────────────────────────────────────────────────
    lines += [
        "## Executive Summary",
        "",
        "| Tier | ✅ Present | ⚠️ Partial | ❌ Missing | Total |",
        "|------|-----------|-----------|-----------|-------|",
        f"| **Need to Have** | {s.present_nth} | {s.partial_nth} | {s.missing_nth} | "
        f"{s.present_nth + s.partial_nth + s.missing_nth} |",
        f"| **Good to Have** | {s.present_gth} | {s.partial_gth} | {s.missing_gth} | "
        f"{s.present_gth + s.partial_gth + s.missing_gth} |",
        "",
    ]

    # Overall status callout
    if s.missing_nth > 0:
        lines += [
            f"> 🔴 **MATERIAL GAPS IDENTIFIED** — {s.missing_nth} Need-to-Have document(s) "
            f"are missing. Data requests should be issued immediately.",
            "",
        ]
    elif s.partial_nth > 0:
        lines += [
            f"> 🟡 **PARTIAL COVERAGE** — All Need-to-Have categories have some coverage, "
            f"but {s.partial_nth} item(s) require follow-up.",
            "",
        ]
    else:
        lines += [
            "> 🟢 **COMPLETE COVERAGE** — All Need-to-Have items are present with high confidence.",
            "",
        ]

    lines += [
        f"**VDR files reviewed:** {s.total_files}  |  "
        f"High confidence: {s.high_confidence}  |  "
        f"Medium confidence: {s.medium_confidence}  |  "
        f"Low confidence: {s.low_confidence}  |  "
        f"Novel (unmatched): {s.novel_count}",
        "",
        "---",
        "",
    ]

    # ── Gap Tracker (re-runs only) ────────────────────────────────────────────
    if gap_delta is not None:
        lines += _render_gap_tracker(gap_delta)

    # ── Section 1: NTH Missing ───────────────────────────────────────────────
    nth_missing = gap_report.by_status(DocumentTier.need_to_have, ChecklistStatus.missing)
    lines += [
        "## Section 1 — NEED TO HAVE: MISSING (❌) — Request Immediately",
        "",
    ]
    if nth_missing:
        lines.append(
            f"> ⚠️ **{len(nth_missing)} critical document(s) not found in VDR.** "
            f"These must be requested from the seller advisor immediately."
        )
        lines.append("")
        # Group by category
        by_cat: dict[str, list[ChecklistItemResult]] = {}
        for item in nth_missing:
            by_cat.setdefault(item.category_label, []).append(item)
        for cat_label, items in by_cat.items():
            lines.append(f"### {cat_label}")
            for item in items:
                lines.append(_format_item(item, show_files=False))
                lines.append("")
    else:
        lines += ["> ✅ No critical missing documents — all Need-to-Have items are present or partially covered.", ""]

    lines += ["---", ""]

    # ── Section 2: NTH Partial ───────────────────────────────────────────────
    nth_partial = gap_report.by_status(DocumentTier.need_to_have, ChecklistStatus.partial)
    lines += [
        "## Section 2 — NEED TO HAVE: PARTIAL (⚠️) — Follow Up",
        "",
    ]
    if nth_partial:
        lines.append(
            f"> ⚠️ **{len(nth_partial)} item(s) partially covered** — matches found but "
            f"may be incomplete, low-confidence, or outdated."
        )
        lines.append("")
        by_cat = {}
        for item in nth_partial:
            by_cat.setdefault(item.category_label, []).append(item)
        for cat_label, items in by_cat.items():
            lines.append(f"### {cat_label}")
            for item in items:
                lines.append(_format_item(item))
                lines.append("")
    else:
        lines += ["> ✅ No partial Need-to-Have items.", ""]

    lines += ["---", ""]

    # ── Section 3: GTH Missing ───────────────────────────────────────────────
    gth_missing = gap_report.by_status(DocumentTier.good_to_have, ChecklistStatus.missing)
    lines += [
        "## Section 3 — GOOD TO HAVE: MISSING (❌)",
        "",
    ]
    if gth_missing:
        by_cat = {}
        for item in gth_missing:
            by_cat.setdefault(item.category_label, []).append(item)
        for cat_label, items in by_cat.items():
            lines.append(f"### {cat_label}")
            for item in items:
                lines.append(_format_item(item, show_files=False))
                lines.append("")
    else:
        lines += ["> ✅ All Good-to-Have items are present or partially covered.", ""]

    lines += ["---", ""]

    # ── Section 4: GTH Partial ───────────────────────────────────────────────
    gth_partial = gap_report.by_status(DocumentTier.good_to_have, ChecklistStatus.partial)
    lines += [
        "## Section 4 — GOOD TO HAVE: PARTIAL (⚠️)",
        "",
    ]
    if gth_partial:
        by_cat = {}
        for item in gth_partial:
            by_cat.setdefault(item.category_label, []).append(item)
        for cat_label, items in by_cat.items():
            lines.append(f"### {cat_label}")
            for item in items:
                lines.append(_format_item(item))
                lines.append("")
    else:
        lines += ["> ✅ No partial Good-to-Have items.", ""]

    lines += ["---", ""]

    # ── Section 5: Present ───────────────────────────────────────────────────
    all_present = [i for i in gap_report.items if i.status == ChecklistStatus.present]
    lines += [
        "## Section 5 — PRESENT (✅)",
        "",
        f"{len(all_present)} checklist item(s) confirmed present with high confidence.",
        "",
        "| Item ID | Category | Description | Source File(s) |",
        "|---------|----------|-------------|----------------|",
    ]
    for item in all_present:
        files_str = ", ".join(f.filename for f in item.matched_files[:2])
        lines.append(f"| `{item.item_id}` | {item.category_label} | {item.description} | {files_str} |")

    lines += ["", "---", ""]

    # ── Section 6: Proposals ─────────────────────────────────────────────────
    lines += [
        "## Section 6 — CHECKLIST EVOLUTION PROPOSALS",
        "",
    ]
    if proposals:
        lines.append(
            f"The following {len(proposals)} document pattern(s) were found in this VDR "
            f"but are **not covered by the gold-standard checklist** (version {gap_report.checklist_version})."
        )
        lines.append("")
        lines.append("To accept or reject these proposals, run:")
        lines.append("```bash")
        lines.append(f"python -m aigis_agents.agent_01_vdr_inventory.accept_proposals --checklist {gap_report.checklist_version}")
        lines.append("```")
        lines.append("")
        lines.append("| # | File Examples | Folder | Suggested Category | Suggested Item | Tier | Reasoning |")
        lines.append("|---|--------------|--------|-------------------|----------------|------|-----------|")
        for i, p in enumerate(proposals, 1):
            examples = ", ".join(f"`{fn}`" for fn in p.filenames[:2])
            lines.append(
                f"| {i} | {examples} | `{p.folder_path or '(root)'}` | "
                f"{p.suggested_category} | {p.suggested_item_description} | "
                f"{p.suggested_tier.value} | {p.reasoning[:80]}... |"
            )
    else:
        lines += [
            "> No novel documents found. The VDR content is fully covered by the current checklist.",
            "",
            f"_Proposals are saved to `checklists/pending_additions.json` and reviewed "
            f"by running: `python -m aigis_agents.agent_01_vdr_inventory.accept_proposals`_",
        ]

    lines += ["", "---", ""]

    # ── Low Confidence Files ─────────────────────────────────────────────────
    if gap_report.low_confidence_files:
        lines += [
            "## Appendix A — Files Requiring Manual Review (Low Confidence Classification)",
            "",
            "These files could not be classified with confidence. Manual review recommended.",
            "",
            "| Filename | Folder | Size | Modified |",
            "|----------|--------|------|----------|",
        ]
        for f in gap_report.low_confidence_files[:50]:
            lines.append(f"| `{f.filename}` | `{f.folder_path}` | {f.size_kb:.0f}KB | {f.date_modified or 'N/A'} |")
        if len(gap_report.low_confidence_files) > 50:
            lines.append(f"\n_...and {len(gap_report.low_confidence_files) - 50} more. See full inventory JSON._")

    lines += ["", "---", ""]

    # ── Full Inventory Appendix ──────────────────────────────────────────────
    lines += [
        "## Appendix B — Full VDR Inventory Summary",
        "",
        f"Total files: **{s.total_files}** | "
        f"Classified: **{s.high_confidence + s.medium_confidence}** | "
        f"Unclassified: **{s.low_confidence + s.unclassified}**",
        "",
        "_Full inventory with metadata available in `01_vdr_inventory.json`_",
        "",
        "---",
        "",
        f"_Generated by Aigis Analytics · Checklist {gap_report.checklist_version} · {run_date}_",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
