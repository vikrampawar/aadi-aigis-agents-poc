"""
PDF ingestion for Agent 02 — VDR Financial & Operational Data Store.

Uses pdfplumber to extract tables from each page, then LLM to label
each table's columns with semantic context (metric, unit, period, category).
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from aigis_agents.agent_02_data_store import db_manager as db


# ── Public API ─────────────────────────────────────────────────────────────────

def ingest_pdf(
    file_path: str | Path,
    deal_id: str,
    doc_id: str,
    conn: sqlite3.Connection,
    case_name: str | None = None,
    main_llm: Any = None,
    dk_context: str = "",
) -> dict[str, Any]:
    """
    Ingest a PDF document into the DB.

    Args:
        file_path:  Path to the PDF file.
        deal_id:    Deal UUID.
        doc_id:     Source document UUID.
        conn:       Open SQLite connection.
        case_name:  Default case tag.
        main_llm:   LangChain chat model for table labeling.
        dk_context: Domain knowledge context for LLM.

    Returns dict with: pages_processed, tables_found, data_points_extracted, errors
    """
    try:
        import pdfplumber
    except ImportError:
        return {"error": "pdfplumber not installed — run: pip install pdfplumber"}

    path = Path(file_path)
    stats = {
        "pages_processed":     0,
        "tables_found":        0,
        "data_points_extracted": 0,
        "errors":              [],
    }

    with pdfplumber.open(str(path)) as pdf:
        total_pages = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            try:
                tables = page.extract_tables()
                if not tables:
                    continue

                stats["pages_processed"] += 1
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue

                    stats["tables_found"] += 1
                    rows_extracted = _process_table(
                        table=table,
                        deal_id=deal_id,
                        doc_id=doc_id,
                        conn=conn,
                        page_num=page_num,
                        case_name=case_name,
                        main_llm=main_llm,
                        dk_context=dk_context,
                    )
                    stats["data_points_extracted"] += rows_extracted

            except Exception as e:
                stats["errors"].append(f"Page {page_num}: {e}")

    return stats


# ── Table processing ───────────────────────────────────────────────────────────

def _process_table(
    table: list[list[str | None]],
    deal_id: str,
    doc_id: str,
    conn: sqlite3.Connection,
    page_num: int,
    case_name: str | None,
    main_llm: Any,
    dk_context: str,
) -> int:
    """
    Process a single extracted PDF table.
    Returns number of data points written.
    """
    if not table or len(table) < 2:
        return 0

    # Clean None values
    cleaned = [[str(cell).strip() if cell else "" for cell in row] for row in table]
    headers = cleaned[0]
    data_rows = cleaned[1:]

    # Filter empty data rows
    data_rows = [r for r in data_rows if any(c for c in r)]
    if not data_rows:
        return 0

    # Use LLM if available to classify columns
    if main_llm:
        extracted = _classify_and_extract_with_llm(
            headers=headers,
            data_rows=data_rows,
            page_num=page_num,
            case_name=case_name,
            main_llm=main_llm,
            dk_context=dk_context,
        )
    else:
        # Heuristic fallback: look for numeric columns
        extracted = _heuristic_extract(headers, data_rows, page_num, case_name)

    if not extracted:
        return 0

    # Route extracted points to correct tables
    return _route_extracted_points(extracted, deal_id, doc_id, conn)


def _classify_and_extract_with_llm(
    headers: list[str],
    data_rows: list[list[str]],
    page_num: int,
    case_name: str | None,
    main_llm: Any,
    dk_context: str,
) -> list[dict[str, Any]]:
    """Call LLM to classify columns and extract typed data points."""
    from langchain_core.messages import HumanMessage, SystemMessage

    table_md = _table_to_markdown(headers, data_rows[:10])  # cap at 10 rows for token efficiency

    dk_block = f"Domain context:\n{dk_context[:2000]}" if dk_context else ""
    prompt = f"""You are extracting numerical data from an upstream oil & gas due diligence document.

{dk_block}

PDF Page {page_num} — Extracted table:
{table_md}

Extract ALL numerical data points from this table. For each data point return:
- metric_name: descriptive name (e.g., "Oil Production Rate", "LOE per BOE", "Royalty Rate")
- metric_key: snake_case key (e.g., "oil_production_boepd", "loe_per_boe", "royalty_rate_pct")
- value: numeric value (float)
- unit: unit of measure (e.g., "bopd", "USD/boe", "%", "mmboe", "USD")
- period: ISO date range "YYYY-MM-DD/YYYY-MM-DD" or null if point-in-time
- category: one of [production, financial, reserve, cost, fiscal, asset, well, other]
- case_name: one of [management_case, cpr_base_case, cpr_low_case, cpr_high_case, conservative_case, base_case]
  (infer from context, default to "{case_name or 'base_case'}")
- confidence: HIGH | MEDIUM | LOW
- row_label: the row label/name from the table
- col_label: the column header this value came from

Return ONLY a JSON array. If no numerical data, return [].
Example:
[
  {{"metric_name": "Oil Production Rate", "metric_key": "oil_production_boepd", "value": 2450.0,
    "unit": "bopd", "period": "2024-01-01/2024-12-31", "category": "production",
    "case_name": "management_case", "confidence": "HIGH", "row_label": "Total Field", "col_label": "2024A"}}
]"""

    try:
        messages = [
            SystemMessage(content="You are an expert upstream oil & gas financial analyst. Return only valid JSON."),
            HumanMessage(content=prompt),
        ]
        response = main_llm.invoke(messages)
        content = response.content.strip()
        # Strip markdown code blocks if present
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        parsed = json.loads(content)
        if isinstance(parsed, list):
            for p in parsed:
                p["source_page"] = page_num
            return parsed
    except Exception:
        pass

    return []


def _heuristic_extract(
    headers: list[str],
    data_rows: list[list[str]],
    page_num: int,
    case_name: str | None,
) -> list[dict[str, Any]]:
    """Simple heuristic extraction: numeric cells with row labels."""
    results = []
    for row in data_rows:
        if not row:
            continue
        row_label = row[0] if row else ""
        for col_idx, header in enumerate(headers[1:], start=1):
            if col_idx >= len(row):
                continue
            cell_val = row[col_idx].replace(",", "").replace("$", "").replace("%", "").strip()
            try:
                value = float(cell_val)
            except ValueError:
                continue
            unit = "%" if "%" in row[col_idx] else ("USD" if "$" in row[col_idx] else "unknown")
            results.append({
                "metric_name": f"{row_label} — {header}",
                "metric_key":  None,
                "value":       value,
                "unit":        unit,
                "period":      None,
                "category":    "other",
                "case_name":   case_name or "base_case",
                "confidence":  "LOW",
                "row_label":   row_label,
                "col_label":   header,
                "source_page": page_num,
            })
    return results


def _route_extracted_points(
    points: list[dict[str, Any]],
    deal_id: str,
    doc_id: str,
    conn: sqlite3.Connection,
) -> int:
    """Route extracted data points to the correct typed table."""
    production_rows: list[dict[str, Any]] = []
    reserve_rows:    list[dict[str, Any]] = []
    financial_rows:  list[dict[str, Any]] = []
    cost_rows:       list[dict[str, Any]] = []
    fiscal_rows:     list[dict[str, Any]] = []
    scalar_rows:     list[dict[str, Any]] = []

    for p in points:
        category  = p.get("category", "other")
        period    = p.get("period", "")
        has_period = bool(period and "/" in (period or ""))

        base = {
            "deal_id":  deal_id,
            "doc_id":   doc_id,
            "case_name": p.get("case_name", "base_case"),
            "value":    p["value"],
            "unit":     p.get("unit", "unknown"),
            "confidence": p.get("confidence", "MEDIUM"),
            "source_page": p.get("source_page"),
            "extraction_note": p.get("metric_name"),
        }

        if category == "production" and has_period:
            ps, pe = _parse_period(period)
            production_rows.append({
                **base,
                "product":     _infer_product(p),
                "period_type": _infer_period_type(ps, pe),
                "period_start": ps,
                "period_end":   pe,
                "entity_name": p.get("row_label"),
            })
        elif category == "reserve":
            reserve_rows.append({
                **base,
                "reserve_class": _infer_reserve_class(p),
                "product":       _infer_product(p),
                "entity_name":   p.get("row_label"),
                "source_section": p.get("row_label"),
            })
        elif category == "financial" and has_period:
            ps, pe = _parse_period(period)
            financial_rows.append({
                **base,
                "line_item":     _infer_line_item(p),
                "line_item_label": p.get("metric_name"),
                "period_type":   _infer_period_type(ps, pe),
                "period_start":  ps,
                "period_end":    pe,
            })
        elif category == "cost":
            cost_rows.append({
                **base,
                "metric": p.get("metric_key") or p.get("metric_name", "unknown_cost"),
            })
        elif category == "fiscal":
            fiscal_rows.append({
                **base,
                "term_name":  p.get("metric_key") or p.get("metric_name", "unknown_term"),
                "term_label": p.get("metric_name"),
            })
        else:
            scalar_rows.append({
                **base,
                "category":    category,
                "metric_name": p.get("metric_name", "unknown"),
                "metric_key":  p.get("metric_key"),
                "as_of_date":  None,
                "context":     p.get("col_label"),
            })

    total = 0
    total += db.bulk_insert_production(conn, production_rows)
    total += db.bulk_insert_reserves(conn, reserve_rows)
    total += db.bulk_insert_financials(conn, financial_rows)
    total += db.bulk_insert_costs(conn, cost_rows)
    total += db.bulk_insert_fiscal(conn, fiscal_rows)
    total += db.bulk_insert_scalars(conn, scalar_rows)
    return total


# ── Utility helpers ────────────────────────────────────────────────────────────

def _table_to_markdown(headers: list[str], rows: list[list[str]]) -> str:
    cols = len(headers)
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join(["---"] * cols) + " |"]
    for row in rows:
        padded = row + [""] * (cols - len(row))
        lines.append("| " + " | ".join(padded[:cols]) + " |")
    return "\n".join(lines)


def _parse_period(period_str: str) -> tuple[str, str]:
    parts = period_str.split("/", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return parts[0].strip(), parts[0].strip()


def _infer_period_type(start: str, end: str) -> str:
    try:
        from datetime import datetime
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
        delta_days = (e - s).days
        if delta_days <= 32:
            return "monthly"
        if delta_days <= 95:
            return "quarterly"
        return "annual"
    except Exception:
        return "annual"


def _infer_product(p: dict) -> str:
    name = (p.get("metric_name", "") + " " + p.get("metric_key", "")).lower()
    if "gas" in name:
        return "gas"
    if "ngl" in name:
        return "ngl"
    if "water" in name:
        return "water"
    if "boe" in name and "bop" not in name:
        return "boe"
    return "oil"


def _infer_reserve_class(p: dict) -> str:
    name = (p.get("metric_name", "") + " " + p.get("col_label", "")).upper()
    for cls in ["PDP", "PNP", "PDnP", "1P", "2P", "3P"]:
        if cls in name:
            return cls
    return "2P"


def _infer_line_item(p: dict) -> str:
    name = (p.get("metric_name", "") + " " + p.get("metric_key", "")).lower()
    mapping = {
        "revenue": "revenue", "loe": "loe", "opex": "loe",
        "ebitda": "ebitda", "capex": "capex",
        "g&a": "g_and_a", "g_and_a": "g_and_a",
        "net income": "net_income", "net_income": "net_income",
        "cash flow": "fcf", "fcf": "fcf",
    }
    for key, val in mapping.items():
        if key in name:
            return val
    return "other"
