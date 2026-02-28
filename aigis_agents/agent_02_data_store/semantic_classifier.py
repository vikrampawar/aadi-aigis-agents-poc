"""
Semantic classification for Agent 02 — VDR Financial & Operational Data Store.

Provides LLM-backed sheet classification for Excel ingestors.
The classify_sheet function is passed as classify_fn to excel_ingestor.ingest_excel().
"""

from __future__ import annotations

import json
import re
from typing import Any

from aigis_agents.agent_02_data_store.models import SheetClassification, SheetType, PeriodType


# ── Public API ─────────────────────────────────────────────────────────────────

def make_classify_fn(main_llm: Any, dk_context: str = ""):
    """
    Return a classify_fn suitable for passing to excel_ingestor.ingest_excel().

    Usage:
        classify_fn = make_classify_fn(llm, dk_context)
        ingest_excel(path, deal_id, doc_id, conn, classify_fn=classify_fn)
    """
    def classify_fn(sheet_name: str, headers: list[str], sample_rows: list[list[str]]) -> SheetClassification:
        return classify_sheet(sheet_name, headers, sample_rows, main_llm, dk_context)
    return classify_fn


def classify_sheet(
    sheet_name: str,
    headers: list[str],
    sample_rows: list[list[str]],
    main_llm: Any,
    dk_context: str = "",
) -> SheetClassification:
    """
    Classify an Excel sheet using LLM.

    Returns SheetClassification with sheet_type, primary_metric, unit_system,
    period_type, case_name, is_time_series, and notes.

    Falls back to heuristic classification if LLM is unavailable or fails.
    """
    if main_llm:
        result = _classify_with_llm(sheet_name, headers, sample_rows, main_llm, dk_context)
        if result:
            return result

    return _classify_heuristic(sheet_name, headers)


# ── LLM classification ────────────────────────────────────────────────────────

def _classify_with_llm(
    sheet_name: str,
    headers: list[str],
    sample_rows: list[list[str]],
    main_llm: Any,
    dk_context: str,
) -> SheetClassification | None:
    """Call LLM to classify sheet type and metadata."""
    from langchain_core.messages import HumanMessage, SystemMessage

    # Build sample table
    header_str = " | ".join(str(h) for h in headers[:15])
    sample_str = "\n".join(
        " | ".join(str(v) for v in row[:15])
        for row in sample_rows[:3]
    )

    dk_block = f"Domain context:\n{dk_context[:1000]}" if dk_context else ""
    prompt = f"""You are classifying a spreadsheet tab from an upstream oil & gas financial model or VDR document.

{dk_block}

Sheet name: "{sheet_name}"
Column headers: {header_str}
Sample data rows:
{sample_str}

Classify this sheet. Return JSON with exactly these fields:
- sheet_type: one of [production, financials, assumptions, summary, dcf, sensitivity, reserves, costs, other]
- primary_metric: the dominant metric (e.g., "oil_production_bopd", "revenue_usd", "npv_10") or null
- unit_system: "imperial" | "metric" | "mixed" | null
- period_type: "monthly" | "quarterly" | "annual" | null (null if not time-series)
- case_name: detected case name if identifiable (e.g., "management_case", "cpr_base_case") or null
- is_time_series: true if columns represent time periods
- notes: brief note on any unusual structure or interpretation

Return ONLY a JSON object."""

    try:
        messages = [
            SystemMessage(content="You are an expert upstream O&G financial analyst. Return only valid JSON."),
            HumanMessage(content=prompt),
        ]
        response = main_llm.invoke(messages)
        content = response.content.strip()
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        data = json.loads(content)

        return SheetClassification(
            sheet_type=SheetType(data.get("sheet_type", "other")),
            primary_metric=data.get("primary_metric"),
            unit_system=data.get("unit_system"),
            period_type=PeriodType(data["period_type"]) if data.get("period_type") else None,
            case_name=data.get("case_name"),
            is_time_series=bool(data.get("is_time_series", False)),
            notes=data.get("notes", ""),
        )
    except Exception:
        return None


# ── Heuristic classification ──────────────────────────────────────────────────

# Sheet name keywords → SheetType
_SHEET_TYPE_KEYWORDS: list[tuple[list[str], SheetType]] = [
    (["prod", "production", "output", "rate", "bopd", "mcfd", "boe"], SheetType.production),
    (["fin", "financial", "p&l", "income", "revenue", "ebitda", "cash"], SheetType.financials),
    (["assume", "assumption", "input", "param", "driver"], SheetType.assumptions),
    (["summary", "overview", "dashboard", "exec", "highlight"], SheetType.summary),
    (["dcf", "npv", "irr", "discounted", "cash flow", "cashflow"], SheetType.dcf),
    (["sensit", "tornado", "spider", "scenario"], SheetType.sensitivity),
    (["reserv", "reserve", "1p", "2p", "3p", "pdp", "cpr"], SheetType.reserves),
    (["cost", "loe", "opex", "capex", "g&a"], SheetType.costs),
]

# Header keywords for period detection
_PERIOD_MONTHLY  = re.compile(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2}/\d{2,4})", re.I)
_PERIOD_QUARTERLY = re.compile(r"q[1-4][\s\-_]\d{2,4}|\d{4}[\s\-_]q[1-4]", re.I)
_PERIOD_ANNUAL   = re.compile(r"^\d{4}$|fy\d{2,4}|full.?year", re.I)


def _classify_heuristic(sheet_name: str, headers: list[str]) -> SheetClassification:
    """Rule-based sheet classification from sheet name and headers."""
    name_lower = sheet_name.lower()

    sheet_type = SheetType.other
    for keywords, stype in _SHEET_TYPE_KEYWORDS:
        if any(kw in name_lower for kw in keywords):
            sheet_type = stype
            break

    # Detect period type from headers
    header_str = " ".join(str(h) for h in headers)
    period_type: PeriodType | None = None
    is_time_series = False

    if _PERIOD_MONTHLY.search(header_str):
        period_type = PeriodType.monthly
        is_time_series = True
    elif _PERIOD_QUARTERLY.search(header_str):
        period_type = PeriodType.quarterly
        is_time_series = True
    elif _PERIOD_ANNUAL.search(header_str):
        period_type = PeriodType.annual
        is_time_series = True

    # Detect primary metric from headers
    primary_metric: str | None = None
    header_lower = header_str.lower()
    if any(k in header_lower for k in ("bopd", "oil prod", "oil rate")):
        primary_metric = "oil_production_bopd"
    elif any(k in header_lower for k in ("mcfd", "gas prod", "gas rate")):
        primary_metric = "gas_production_mcfd"
    elif any(k in header_lower for k in ("boe", "boepd", "total prod")):
        primary_metric = "total_production_boepd"
    elif any(k in header_lower for k in ("revenue", "rev")):
        primary_metric = "revenue_usd"
    elif any(k in header_lower for k in ("npv", "net present")):
        primary_metric = "npv_usd"
    elif any(k in header_lower for k in ("loe", "opex")):
        primary_metric = "loe_per_boe"
    elif any(k in header_lower for k in ("reserve", "1p", "2p")):
        primary_metric = "reserve_estimate_mmboe"

    return SheetClassification(
        sheet_type=sheet_type,
        primary_metric=primary_metric,
        unit_system=None,
        period_type=period_type,
        case_name=None,
        is_time_series=is_time_series,
        notes="heuristic classification",
    )
