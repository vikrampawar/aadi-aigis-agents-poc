"""
Report generator for Agent 02 — VDR Financial & Operational Data Store.

Produces human-readable Markdown reports for standalone mode.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aigis_agents.agent_02_data_store import db_manager as db


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_ingestion_report(
    conn: sqlite3.Connection,
    deal_id: str,
    output_dir: str | Path,
    ingestion_stats: dict[str, Any],
    conflict_stats: dict[str, int],
) -> Path:
    """
    Generate a Markdown ingestion summary report.

    Returns path to the written file.
    """
    output_path = Path(output_dir) / deal_id / "02_ingestion_report.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = _build_ingestion_report(conn, deal_id, ingestion_stats, conflict_stats)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def generate_conflict_report(
    conn: sqlite3.Connection,
    deal_id: str,
    output_dir: str | Path,
) -> Path:
    """
    Generate a detailed Markdown conflict report.

    Returns path to the written file.
    """
    output_path = Path(output_dir) / deal_id / "02_conflict_report.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = _build_conflict_report(conn, deal_id)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


# ── Ingestion report ───────────────────────────────────────────────────────────

def _build_ingestion_report(
    conn: sqlite3.Connection,
    deal_id: str,
    stats: dict[str, Any],
    conflict_stats: dict[str, int],
) -> list[str]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_dp = db.count_data_points(conn, deal_id)
    cases = db.get_cases(conn, deal_id)
    docs = db.get_source_docs(conn, deal_id)

    lines = [
        "# Agent 02 — VDR Data Store: Ingestion Report",
        f"**Deal ID:** `{deal_id}`  ",
        f"**Generated:** {now}  ",
        "",
        "---",
        "",
        "## Ingestion Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Files processed | {stats.get('files_processed', 0)} |",
        f"| Data points ingested | {total_dp:,} |",
        f"| Cases detected | {len(cases)} |",
        f"| Conflicts (CRITICAL) | {conflict_stats.get('critical', 0)} |",
        f"| Conflicts (WARNING) | {conflict_stats.get('warning', 0)} |",
        f"| Conflicts (INFO) | {conflict_stats.get('info', 0)} |",
        "",
    ]

    # Cases table
    if cases:
        lines += [
            "## Cases Detected",
            "",
            "| Case Name |",
            "|-----------|",
        ]
        for case in cases:
            lines.append(f"| `{case}` |")
        lines.append("")

    # Source documents table
    if docs:
        lines += [
            "## Source Documents",
            "",
            "| Filename | Type | Category | Status |",
            "|----------|------|----------|--------|",
        ]
        for d in docs:
            lines.append(
                f"| {d.get('filename', '')} "
                f"| {d.get('file_type', '')} "
                f"| {d.get('doc_category', '')} "
                f"| {d.get('status', '')} |"
            )
        lines.append("")

    # Data points by table
    lines += [
        "## Data Points by Table",
        "",
        "| Table | Count |",
        "|-------|-------|",
    ]
    for table in [
        "production_series", "reserve_estimates", "financial_series",
        "cost_benchmarks", "fiscal_terms", "scalar_datapoints", "excel_cells",
    ]:
        try:
            rows = db.query_all(conn, f"SELECT COUNT(*) as n FROM {table} WHERE deal_id = ?", (deal_id,))
            n = rows[0]["n"] if rows else 0
        except Exception:
            n = 0
        if n > 0:
            lines.append(f"| {table} | {n:,} |")
    lines.append("")

    # Errors
    errors = stats.get("errors", [])
    if errors:
        lines += [
            "## Errors",
            "",
        ]
        for e in errors[:20]:
            lines.append(f"- {e}")
        if len(errors) > 20:
            lines.append(f"- *(and {len(errors) - 20} more)*")
        lines.append("")

    return lines


# ── Conflict report ────────────────────────────────────────────────────────────

def _build_conflict_report(
    conn: sqlite3.Connection,
    deal_id: str,
) -> list[str]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    all_conflicts = db.get_conflicts(conn, deal_id, severity=None)

    critical = [c for c in all_conflicts if c.get("severity") == "CRITICAL"]
    warning  = [c for c in all_conflicts if c.get("severity") == "WARNING"]
    info     = [c for c in all_conflicts if c.get("severity") == "INFO"]

    lines = [
        "# Agent 02 — VDR Data Store: Conflict Report",
        f"**Deal ID:** `{deal_id}`  ",
        f"**Generated:** {now}  ",
        f"**Total Conflicts:** {len(all_conflicts)}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        f"| 🔴 CRITICAL | {len(critical)} |",
        f"| 🟡 WARNING  | {len(warning)} |",
        f"| 🔵 INFO     | {len(info)} |",
        "",
    ]

    if critical:
        lines += ["---", "", "## 🔴 Critical Conflicts", ""]
        lines += _format_conflict_table(critical)
        lines.append("")

    if warning:
        lines += ["---", "", "## 🟡 Warning Conflicts", ""]
        lines += _format_conflict_table(warning)
        lines.append("")

    if info:
        lines += ["---", "", "## 🔵 Info Conflicts", ""]
        lines += _format_conflict_table(info[:50])  # cap INFO list
        if len(info) > 50:
            lines.append(f"*(showing 50 of {len(info)} INFO conflicts)*")
        lines.append("")

    if not all_conflicts:
        lines.append("*No conflicts detected. All sources are internally consistent.*")

    return lines


def _format_conflict_table(conflicts: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Metric | Period | Source A | Source B | Discrepancy |",
        "|--------|--------|----------|----------|-------------|",
    ]
    for c in conflicts:
        period = f"{c.get('period_start', '')}→{c.get('period_end', '')}" if c.get("period_start") else "—"
        src_a  = f"{c.get('source_a_doc_id', '')[:12]}… ({c.get('source_a_value', '')} {c.get('source_a_unit', '')})"
        src_b  = f"{c.get('source_b_doc_id', '')[:12]}… ({c.get('source_b_value', '')} {c.get('source_b_unit', '')})"
        pct    = f"{c.get('discrepancy_pct', '')}%" if c.get("discrepancy_pct") is not None else "—"
        lines.append(f"| {c.get('metric_name', '')} | {period} | {src_a} | {src_b} | {pct} |")
    return lines
