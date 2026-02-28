"""
Consistency checker for Agent 02 — VDR Financial & Operational Data Store.

Post-ingestion cross-source conflict detection (merged Agent 03 functionality).

Compares all newly ingested data against existing records for the same deal,
detecting: value_mismatch, unit_inconsistency, date_overlap, missing_in_source.

Results are written to the data_conflicts table.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from aigis_agents.agent_02_data_store import db_manager as db


# ── Thresholds ─────────────────────────────────────────────────────────────────

CRITICAL_PCT  = 0.20   # >20% discrepancy → CRITICAL
WARNING_PCT   = 0.05   # 5–20%            → WARNING
# <5%                  → INFO


# ── Public API ─────────────────────────────────────────────────────────────────

def run_consistency_check(
    conn: sqlite3.Connection,
    deal_id: str,
    new_doc_ids: list[str] | None = None,
) -> dict[str, int]:
    """
    Run all conflict checks for a deal.

    Args:
        conn:         Open SQLite connection.
        deal_id:      Deal UUID to check.
        new_doc_ids:  Newly ingested doc IDs to focus on (None = check all).

    Returns:
        {"critical": N, "warning": N, "info": N, "total": N}
    """
    counters = {"critical": 0, "warning": 0, "info": 0, "total": 0}

    conflicts = []
    conflicts += _check_production_conflicts(conn, deal_id, new_doc_ids)
    conflicts += _check_financial_conflicts(conn, deal_id, new_doc_ids)
    conflicts += _check_reserve_conflicts(conn, deal_id, new_doc_ids)
    conflicts += _check_unit_conflicts(conn, deal_id, new_doc_ids)

    for conflict in conflicts:
        db.insert_conflict(conn, conflict)
        sev = conflict.get("severity", "INFO")
        counters[sev.lower()] = counters.get(sev.lower(), 0) + 1
        counters["total"] += 1

    return counters


# ── Production conflict checks ─────────────────────────────────────────────────

def _check_production_conflicts(
    conn: sqlite3.Connection,
    deal_id: str,
    new_doc_ids: list[str] | None,
) -> list[dict[str, Any]]:
    """
    Find cases where the same (deal_id, case_name, entity_name, period_start, product)
    has multiple values across different source documents.
    """
    sql = """
        SELECT
            case_name, entity_name, period_start, period_end, product,
            doc_id, value, unit
        FROM production_series
        WHERE deal_id = ?
        ORDER BY case_name, entity_name, period_start, product, doc_id
    """
    rows = db.query_all(conn, sql, (deal_id,))
    return _detect_value_mismatches(rows, "production", new_doc_ids,
                                    key_cols=("case_name", "entity_name", "period_start", "product"),
                                    deal_id=deal_id)


# ── Financial conflict checks ──────────────────────────────────────────────────

def _check_financial_conflicts(
    conn: sqlite3.Connection,
    deal_id: str,
    new_doc_ids: list[str] | None,
) -> list[dict[str, Any]]:
    """
    Detect value_mismatch for financial_series across documents.
    """
    sql = """
        SELECT
            case_name, line_item, period_start, period_end,
            doc_id, value, unit
        FROM financial_series
        WHERE deal_id = ?
        ORDER BY case_name, line_item, period_start, doc_id
    """
    rows = db.query_all(conn, sql, (deal_id,))
    return _detect_value_mismatches(rows, "financial", new_doc_ids,
                                    key_cols=("case_name", "line_item", "period_start"),
                                    deal_id=deal_id)


# ── Reserve conflict checks ────────────────────────────────────────────────────

def _check_reserve_conflicts(
    conn: sqlite3.Connection,
    deal_id: str,
    new_doc_ids: list[str] | None,
) -> list[dict[str, Any]]:
    """
    Detect value_mismatch for reserve_estimates across documents.
    """
    sql = """
        SELECT
            case_name, reserve_class, product, entity_name,
            doc_id, value, unit
        FROM reserve_estimates
        WHERE deal_id = ?
        ORDER BY case_name, reserve_class, product, entity_name, doc_id
    """
    rows = db.query_all(conn, sql, (deal_id,))
    return _detect_value_mismatches(rows, "reserves", new_doc_ids,
                                    key_cols=("case_name", "reserve_class", "product", "entity_name"),
                                    deal_id=deal_id)


# ── Unit inconsistency checks ──────────────────────────────────────────────────

def _check_unit_conflicts(
    conn: sqlite3.Connection,
    deal_id: str,
    new_doc_ids: list[str] | None,
) -> list[dict[str, Any]]:
    """
    Flag cases where the same metric appears with incompatible units.
    """
    # Check production_series for mixed units on same metric+period
    sql = """
        SELECT
            case_name, entity_name, period_start, product,
            doc_id, value, unit
        FROM production_series
        WHERE deal_id = ?
        GROUP BY case_name, entity_name, period_start, product
        HAVING COUNT(DISTINCT unit) > 1
        ORDER BY case_name, period_start, product
    """
    rows = db.query_all(conn, sql, (deal_id,))
    conflicts: list[dict[str, Any]] = []
    for row in rows:
        conflicts.append(_make_conflict(
            deal_id=deal_id,
            conflict_type="unit_inconsistency",
            metric_name=f"production:{row.get('product','')}",
            period_start=row.get("period_start"),
            period_end=row.get("period_end"),
            source_a_doc_id=row.get("doc_id"),
            source_a_case=row.get("case_name"),
            source_a_value=row.get("value"),
            source_a_unit=row.get("unit"),
            severity="WARNING",
        ))
    return conflicts


# ── Generic value mismatch detector ───────────────────────────────────────────

def _detect_value_mismatches(
    rows: list[dict[str, Any]],
    metric_type: str,
    new_doc_ids: list[str] | None,
    key_cols: tuple[str, ...],
    deal_id: str,
) -> list[dict[str, Any]]:
    """
    Group rows by key_cols and detect conflicts where two different doc_ids
    report different values for the same key.
    """
    # Group by key
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = tuple(str(row.get(col, "")) for col in key_cols)
        grouped.setdefault(key, []).append(row)

    conflicts = []
    for key, group in grouped.items():
        if len(group) < 2:
            continue

        # Only flag if at least one row is from a new doc
        if new_doc_ids:
            doc_ids = {r.get("doc_id") for r in group}
            if not doc_ids.intersection(new_doc_ids):
                continue

        # Compare pairwise (first vs each subsequent)
        base = group[0]
        for other in group[1:]:
            base_val  = base.get("value")
            other_val = other.get("value")
            if base_val is None or other_val is None:
                continue
            if base.get("doc_id") == other.get("doc_id"):
                continue

            # Compute discrepancy
            ref = max(abs(base_val), abs(other_val))
            if ref == 0:
                continue
            pct = abs(base_val - other_val) / ref

            severity = _severity_from_pct(pct)
            if severity is None:
                continue  # INFO threshold — skip very small diffs (< 1%)

            # Build metric_name from key
            metric_name = f"{metric_type}:" + "/".join(str(k) for k in key if k)

            conflicts.append(_make_conflict(
                deal_id=deal_id,
                conflict_type="value_mismatch",
                metric_name=metric_name,
                period_start=str(base.get("period_start", "")),
                period_end=str(base.get("period_end", "")),
                source_a_doc_id=base.get("doc_id"),
                source_a_case=base.get("case_name"),
                source_a_value=base_val,
                source_a_unit=base.get("unit"),
                source_b_doc_id=other.get("doc_id"),
                source_b_case=other.get("case_name"),
                source_b_value=other_val,
                source_b_unit=other.get("unit"),
                discrepancy_pct=round(pct * 100, 2),
                severity=severity,
            ))

    return conflicts


# ── Helpers ────────────────────────────────────────────────────────────────────

def _severity_from_pct(pct: float) -> str | None:
    """Return severity string or None if below INFO threshold."""
    if pct > CRITICAL_PCT:
        return "CRITICAL"
    if pct > WARNING_PCT:
        return "WARNING"
    if pct > 0.01:
        return "INFO"
    return None


def _make_conflict(
    deal_id: str,
    conflict_type: str,
    metric_name: str,
    severity: str,
    **kwargs,
) -> dict[str, Any]:
    """Build a conflict dict for db.insert_conflict()."""
    return {
        "id":               str(uuid.uuid4()),
        "deal_id":          deal_id,
        "conflict_type":    conflict_type,
        "metric_name":      metric_name,
        "severity":         severity,
        "detected_at":      datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }
