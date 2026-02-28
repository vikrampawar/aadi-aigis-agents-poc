"""
Formula evaluation engine for Agent 02 — VDR Financial & Operational Data Store.

Hybrid strategy:
  - xlcalculator: simple workbook re-evaluation (LOE schedules, royalty/tax tables,
    revenue re-computation with new price deck, simple decline tables)
  - Agent 04 delegation: full financial models (NPV, IRR, payback, full sensitivity)

Scenario overrides are passed as {sheet!cell: new_value} or as named assumption keys
that are resolved to cell addresses using the excel_cells table.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


# ── Public API ─────────────────────────────────────────────────────────────────

def evaluate_scenario(
    conn: sqlite3.Connection,
    deal_id: str,
    workbook_path: str | Path,
    base_case: str,
    overrides: dict[str, Any],
    output_cells: list[str] | None = None,
    agent04: Any | None = None,
) -> dict[str, Any]:
    """
    Evaluate a scenario by applying overrides to an Excel workbook.

    Args:
        conn:          Open SQLite connection.
        deal_id:       Deal UUID.
        workbook_path: Path to the .xlsx file.
        base_case:     Case name to use as the base (e.g., "management_case").
        overrides:     Dict of assumption overrides. Keys can be:
                         - "Sheet!A1" notation (cell address)
                         - Semantic keys like "oil_price_usd_bbl" (resolved via DB)
        output_cells:  List of cells to read after evaluation (e.g., ["Summary!C12"]).
                       None = read all formula output cells.
        agent04:       Agent 04 instance for NPV/IRR delegation (optional).

    Returns:
        {
          "engine": "xlcalculator" | "agent_04" | "unavailable",
          "base_case": ...,
          "overrides_applied": {...},
          "results": {cell_address: value, ...},
          "errors": [...]
        }
    """
    path = Path(workbook_path)
    resolved_overrides = _resolve_overrides(conn, deal_id, base_case, overrides)

    # Decide which engine to use
    if _needs_agent04(overrides, output_cells):
        if agent04 is not None:
            return _run_agent04(agent04, deal_id, base_case, resolved_overrides, output_cells)
        return {
            "engine": "unavailable",
            "base_case": base_case,
            "overrides_applied": resolved_overrides,
            "results": {},
            "errors": ["Agent 04 not available for complex financial model evaluation"],
        }

    return _run_xlcalculator(path, base_case, resolved_overrides, output_cells)


# ── xlcalculator engine ────────────────────────────────────────────────────────

def _run_xlcalculator(
    workbook_path: Path,
    base_case: str,
    overrides: dict[str, Any],
    output_cells: list[str] | None,
) -> dict[str, Any]:
    """
    Use xlcalculator to re-evaluate the workbook with overrides applied.

    xlcalculator supports: SUM, IF, VLOOKUP, and most arithmetic formulas.
    Limitations: no circular references, no VBA, limited function coverage.
    """
    result: dict[str, Any] = {
        "engine": "xlcalculator",
        "base_case": base_case,
        "overrides_applied": overrides,
        "results": {},
        "errors": [],
    }

    try:
        from xlcalculator import ModelCompiler, Evaluator

        model = ModelCompiler().read_and_parse_archive(str(workbook_path))
        evaluator = Evaluator(model)

        # Apply overrides
        applied = {}
        for cell_addr, new_val in overrides.items():
            try:
                evaluator.set_cell_value(cell_addr, new_val)
                applied[cell_addr] = new_val
            except Exception as e:
                result["errors"].append(f"Override {cell_addr}: {e}")

        result["overrides_applied"] = applied

        # Read output cells
        cells_to_read = output_cells or _get_output_cells_from_model(model)
        for cell_addr in cells_to_read:
            try:
                val = evaluator.evaluate(cell_addr)
                result["results"][cell_addr] = val
            except Exception as e:
                result["errors"].append(f"Evaluate {cell_addr}: {e}")

    except ImportError:
        result["engine"] = "unavailable"
        result["errors"].append("xlcalculator not installed — run: pip install xlcalculator")
    except Exception as e:
        result["engine"] = "error"
        result["errors"].append(f"xlcalculator error: {e}")

    return result


def _get_output_cells_from_model(model) -> list[str]:
    """Extract all formula cells from the xlcalculator model as candidates."""
    try:
        return [str(addr) for addr in list(model.cells.keys())[:50]]
    except Exception:
        return []


# ── Agent 04 delegation ────────────────────────────────────────────────────────

def _run_agent04(
    agent04: Any,
    deal_id: str,
    base_case: str,
    overrides: dict[str, Any],
    output_cells: list[str] | None,
) -> dict[str, Any]:
    """
    Delegate scenario evaluation to Agent 04 for full financial model calculations.
    """
    result: dict[str, Any] = {
        "engine": "agent_04",
        "base_case": base_case,
        "overrides_applied": overrides,
        "results": {},
        "errors": [],
    }
    try:
        agent04_result = agent04.invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="scenario_evaluate",
            base_case=base_case,
            assumption_overrides=overrides,
            requested_outputs=output_cells or [],
        )
        if isinstance(agent04_result, dict):
            result["results"] = agent04_result.get("outputs", {})
            result["errors"]  = agent04_result.get("errors", [])
    except Exception as e:
        result["errors"].append(f"Agent 04 delegation failed: {e}")

    return result


# ── Override resolution ────────────────────────────────────────────────────────

def _resolve_overrides(
    conn: sqlite3.Connection,
    deal_id: str,
    base_case: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """
    Resolve semantic keys to cell addresses where possible.

    e.g., "oil_price_usd_bbl" → "Assumptions!B5"
    Keys already in "Sheet!A1" format are passed through unchanged.
    """
    resolved = {}
    for key, val in overrides.items():
        if "!" in key:
            # Already a cell address
            resolved[key] = val
        else:
            # Try to resolve via excel_cells.semantic_label
            cell_addr = _lookup_semantic_label(conn, deal_id, base_case, key)
            if cell_addr:
                resolved[cell_addr] = val
            else:
                # Keep as-is (may be an assumption name for Agent 04)
                resolved[key] = val
    return resolved


def _lookup_semantic_label(
    conn: sqlite3.Connection,
    deal_id: str,
    base_case: str,
    label: str,
) -> str | None:
    """Look up a cell address from semantic_label in excel_cells."""
    try:
        rows = conn.execute(
            """
            SELECT sheet_name, cell_address
            FROM excel_cells
            WHERE deal_id = ? AND case_name = ? AND semantic_label = ? AND is_assumption = 1
            LIMIT 1
            """,
            (deal_id, base_case, label),
        ).fetchall()
        if rows:
            row = rows[0]
            return f"{row[0]}!{row[1]}"
    except Exception:
        pass
    return None


# ── Engine decision ────────────────────────────────────────────────────────────

_AGENT04_METRIC_KEYWORDS = {
    "npv", "irr", "payback", "decline", "dca", "type_curve",
    "sensitivity", "tornado", "full_model",
}


def _needs_agent04(overrides: dict[str, Any], output_cells: list[str] | None) -> bool:
    """
    Heuristic: use Agent 04 if output cells or override keys suggest complex calculations.
    """
    all_keys = set((overrides or {}).keys()) | set(output_cells or [])
    return any(kw in k.lower() for k in all_keys for kw in _AGENT04_METRIC_KEYWORDS)
