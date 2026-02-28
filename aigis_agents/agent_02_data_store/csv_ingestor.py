"""
CSV ingestion for Agent 02 — VDR Financial & Operational Data Store.

Uses pandas for parsing, then LLM (or heuristics) to classify columns.
Each data row = one time-period record.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from aigis_agents.agent_02_data_store import db_manager as db


# ── Public API ─────────────────────────────────────────────────────────────────

def ingest_csv(
    file_path: str | Path,
    deal_id: str,
    doc_id: str,
    conn: sqlite3.Connection,
    case_name: str | None = None,
    main_llm: Any = None,
    dk_context: str = "",
) -> dict[str, Any]:
    """
    Ingest a CSV/TSV file into the DB.

    Returns dict with: rows_read, data_points_extracted, errors
    """
    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas not installed — run: pip install pandas"}

    path = Path(file_path)
    stats = {"rows_read": 0, "data_points_extracted": 0, "errors": []}

    # Try multiple encodings
    df = None
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            sep = "\t" if path.suffix.lower() == ".tsv" else ","
            df = pd.read_csv(str(path), encoding=enc, sep=sep,
                             low_memory=False, na_values=["", "N/A", "-", "—"])
            break
        except Exception:
            continue

    if df is None or df.empty:
        stats["errors"].append("Could not parse CSV with any supported encoding")
        return stats

    df.dropna(how="all", inplace=True)
    df.columns = [str(c).strip() for c in df.columns]
    stats["rows_read"] = len(df)

    # Classify columns using LLM or heuristics
    if main_llm:
        col_meta = _classify_columns_llm(df, main_llm, dk_context, case_name)
    else:
        col_meta = _classify_columns_heuristic(df, case_name)

    if not col_meta:
        stats["errors"].append("No classifiable numeric columns found")
        return stats

    # Extract data points per row
    points = _extract_row_points(df, col_meta, doc_id, deal_id)
    if not points:
        return stats

    # Route to typed tables
    written = _route_points(points, deal_id, doc_id, conn)
    stats["data_points_extracted"] = written
    return stats


# ── Column classification ──────────────────────────────────────────────────────

def _classify_columns_llm(
    df,
    main_llm: Any,
    dk_context: str,
    default_case: str | None,
) -> list[dict[str, Any]]:
    """Ask LLM to classify each column."""
    from langchain_core.messages import HumanMessage, SystemMessage

    col_summary = []
    for col in df.columns:
        sample_vals = df[col].dropna().head(5).tolist()
        col_summary.append({"column": col, "sample_values": [str(v) for v in sample_vals]})

    dk_block = f"Domain context:\n{dk_context[:1500]}" if dk_context else ""
    prompt = f"""You are classifying columns of a CSV from an upstream oil & gas VDR.

{dk_block}

Columns and sample values:
{json.dumps(col_summary, indent=2)}

For each NUMERIC column, return:
- column: the column name (exactly as given)
- metric_key: snake_case key (e.g., "oil_production_boepd", "loe_per_boe")
- metric_name: human-readable name
- unit: unit of measure (bopd, mcfd, boe, USD, USD/boe, %, mmboe, etc.)
- category: production | financial | reserve | cost | fiscal | other
- product: oil | gas | ngl | boe | water | null (for non-production)
- is_period_col: true if this column represents a date/period label
- period_type: monthly | quarterly | annual | null

For the DATE/PERIOD column (if any), set is_period_col=true.
Skip text-only columns with no numeric significance.
Return ONLY a JSON array."""

    try:
        messages = [
            SystemMessage(content="You are an expert upstream O&G data analyst. Return only valid JSON."),
            HumanMessage(content=prompt),
        ]
        response = main_llm.invoke(messages)
        content = response.content.strip()
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        return json.loads(content)
    except Exception:
        return _classify_columns_heuristic(None, default_case)


def _classify_columns_heuristic(df, default_case: str | None) -> list[dict[str, Any]]:
    """Simple heuristic: classify columns by name patterns."""
    if df is None:
        return []

    results = []
    for col in df.columns:
        col_lower = col.lower()
        # Skip obvious non-numeric cols
        if any(k in col_lower for k in ("date", "period", "year", "month", "name", "field",
                                         "well", "description", "notes", "comment")):
            if any(k in col_lower for k in ("date", "period", "year", "month")):
                results.append({"column": col, "is_period_col": True, "metric_key": "period"})
            continue

        # Check if column has any numeric values
        try:
            import pandas as pd
            numeric = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
            if numeric.dropna().empty:
                continue
        except Exception:
            continue

        meta: dict[str, Any] = {"column": col, "is_period_col": False,
                                  "case_name": default_case or "base_case"}
        if any(k in col_lower for k in ("oil", "bopd", "bbl")):
            meta.update({"metric_key": "oil_production", "unit": "bopd",
                         "category": "production", "product": "oil"})
        elif any(k in col_lower for k in ("gas", "mcfd", "mmcfd")):
            meta.update({"metric_key": "gas_production", "unit": "mcfd",
                         "category": "production", "product": "gas"})
        elif "boe" in col_lower:
            meta.update({"metric_key": "total_production_boe", "unit": "boe",
                         "category": "production", "product": "boe"})
        elif any(k in col_lower for k in ("loe", "opex")):
            meta.update({"metric_key": "loe_per_boe", "unit": "USD/boe", "category": "cost"})
        elif any(k in col_lower for k in ("revenue", "rev")):
            meta.update({"metric_key": "revenue", "unit": "USD", "category": "financial"})
        else:
            meta.update({"metric_key": col_lower.replace(" ", "_"), "unit": "unknown",
                         "category": "other"})
        results.append(meta)
    return results


# ── Row data extraction ────────────────────────────────────────────────────────

def _extract_row_points(
    df,
    col_meta: list[dict[str, Any]],
    doc_id: str,
    deal_id: str,
) -> list[dict[str, Any]]:
    """Extract a list of data point dicts from the DataFrame."""
    import pandas as pd

    # Identify period column
    period_col = next((m["column"] for m in col_meta if m.get("is_period_col")), None)
    data_cols  = [m for m in col_meta if not m.get("is_period_col")]

    points: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        period_val = str(row[period_col]).strip() if period_col and period_col in row else None
        period_start, period_end = _parse_period_value(period_val)

        for cm in data_cols:
            col = cm["column"]
            if col not in row:
                continue
            raw = row[col]
            if pd.isna(raw):
                continue
            try:
                value = float(str(raw).replace(",", "").replace("$", "").replace("%", "").strip())
            except ValueError:
                continue

            points.append({
                "deal_id":      deal_id,
                "doc_id":       doc_id,
                "case_name":    cm.get("case_name", "base_case"),
                "metric_name":  cm.get("metric_name", cm["column"]),
                "metric_key":   cm.get("metric_key"),
                "value":        value,
                "unit":         cm.get("unit", "unknown"),
                "category":     cm.get("category", "other"),
                "product":      cm.get("product"),
                "period_type":  cm.get("period_type"),
                "period_start": period_start,
                "period_end":   period_end,
                "confidence":   "MEDIUM",
            })

    return points


def _route_points(
    points: list[dict[str, Any]],
    deal_id: str,
    doc_id: str,
    conn: sqlite3.Connection,
) -> int:
    """Route points to typed tables, same logic as pdf_ingestor."""
    production_rows: list[dict[str, Any]] = []
    financial_rows:  list[dict[str, Any]] = []
    cost_rows:       list[dict[str, Any]] = []
    scalar_rows:     list[dict[str, Any]] = []

    for p in points:
        base = {
            "deal_id":  deal_id, "doc_id": doc_id,
            "case_name": p["case_name"],
            "value":    p["value"], "unit": p["unit"],
            "confidence": p["confidence"],
        }
        cat  = p.get("category", "other")
        has_period = bool(p.get("period_start"))

        if cat == "production" and has_period:
            production_rows.append({
                **base,
                "product":     p.get("product", "boe"),
                "period_type": p.get("period_type") or "annual",
                "period_start": p["period_start"],
                "period_end":   p.get("period_end") or p["period_start"],
                "entity_name": None,
            })
        elif cat == "financial" and has_period:
            financial_rows.append({
                **base,
                "line_item":     p.get("metric_key", "other"),
                "line_item_label": p.get("metric_name"),
                "period_type":   p.get("period_type") or "annual",
                "period_start":  p["period_start"],
                "period_end":    p.get("period_end") or p["period_start"],
            })
        elif cat == "cost":
            cost_rows.append({
                **base,
                "metric": p.get("metric_key", "unknown_cost"),
            })
        else:
            scalar_rows.append({
                **base,
                "category":    cat,
                "metric_name": p.get("metric_name", "unknown"),
                "metric_key":  p.get("metric_key"),
            })

    total = 0
    total += db.bulk_insert_production(conn, production_rows)
    total += db.bulk_insert_financials(conn, financial_rows)
    total += db.bulk_insert_costs(conn, cost_rows)
    total += db.bulk_insert_scalars(conn, scalar_rows)
    return total


# ── Period parsing ─────────────────────────────────────────────────────────────

def _parse_period_value(val: str | None) -> tuple[str | None, str | None]:
    """Parse a period value like '2024', 'Jan-2024', '2024-Q1' into (start, end) ISO dates."""
    if not val or val.lower() in ("nan", "none", ""):
        return None, None

    # Try plain year
    if re.match(r"^\d{4}$", val):
        return f"{val}-01-01", f"{val}-12-31"

    # Try YYYY-MM
    m = re.match(r"^(\d{4})-(\d{2})$", val)
    if m:
        y, mo = m.group(1), m.group(2)
        import calendar
        last = calendar.monthrange(int(y), int(mo))[1]
        return f"{y}-{mo}-01", f"{y}-{mo}-{last:02d}"

    # Try month name
    import datetime
    for fmt in ("%b-%Y", "%B-%Y", "%b %Y", "%B %Y", "%m/%Y"):
        try:
            dt = datetime.datetime.strptime(val, fmt)
            import calendar
            last = calendar.monthrange(dt.year, dt.month)[1]
            return (f"{dt.year}-{dt.month:02d}-01",
                    f"{dt.year}-{dt.month:02d}-{last:02d}")
        except ValueError:
            continue

    # Try ISO date
    try:
        datetime.datetime.fromisoformat(val)
        return val, val
    except ValueError:
        pass

    return None, None
