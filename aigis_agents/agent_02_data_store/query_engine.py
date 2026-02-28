"""
Query engine for Agent 02 — VDR Financial & Operational Data Store.

Two query modes:
  1. Natural language (query_text) — LLM translates to SQL, audit LLM validates
  2. Direct SQL (query_sql)       — parameterised query execution

Scenario mode: if a `scenario` dict is provided, triggers formula re-evaluation
before returning results.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from aigis_agents.agent_02_data_store import db_manager as db


# ── Table registry (for LLM query generation) ─────────────────────────────────

_SCHEMA_SUMMARY = """
Available tables (SQLite):
- production_series (deal_id, case_name, entity_name, period_start, period_end, period_type, product, value, unit, confidence, source_sheet, source_page)
- reserve_estimates (deal_id, case_name, reserve_class, product, entity_name, value, unit, effective_date, report_date, confidence)
- financial_series  (deal_id, case_name, line_item, line_item_label, period_start, period_end, period_type, value, unit, confidence)
- cost_benchmarks   (deal_id, case_name, metric, period_start, period_end, value, unit, confidence)
- fiscal_terms      (deal_id, case_name, term_name, term_label, value, unit, effective_from, effective_to)
- scalar_datapoints (deal_id, case_name, category, metric_name, metric_key, value, unit, as_of_date, context, confidence)
- excel_cells       (deal_id, doc_id, sheet_name, cell_address, row_num, col_num, raw_value, numeric_value, formula, data_type, semantic_label, unit, row_header, col_header, is_assumption, is_output, case_name)
- source_documents  (doc_id, deal_id, filename, file_type, doc_category, doc_label, source_date, status)
- data_conflicts    (deal_id, conflict_type, metric_name, period_start, period_end, source_a_doc_id, source_a_value, source_b_value, discrepancy_pct, severity, resolved)
- cases             (deal_id, case_name, case_type, display_label, description)

All queries MUST include WHERE deal_id = '{deal_id}'.
Use ISO date strings for period filtering (e.g., '2024-01-01').
line_item values: revenue, loe, g_and_a, ebitda, capex, net_income, fcf, other
product values: oil, gas, ngl, water, boe, boepd
reserve_class values: 1P, 2P, 3P, PDP, PNP, PDnP
"""

# Safety: block these SQL keywords in user-provided SQL
_BLOCKED_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|ALTER|CREATE|ATTACH|DETACH)\b", re.I
)


# ── Public API ─────────────────────────────────────────────────────────────────

def run_query(
    conn: sqlite3.Connection,
    deal_id: str,
    query_text: str | None = None,
    query_sql: str | None = None,
    data_type: str | None = None,
    case_name: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    include_metadata: bool = True,
    main_llm: Any = None,
    audit_llm: Any = None,
    scenario: dict | None = None,
    formula_engine_fn: Any | None = None,
) -> dict[str, Any]:
    """
    Execute a query against the deal DB.

    Returns QueryResult-compatible dict.
    """
    result: dict[str, Any] = {
        "operation":     "query",
        "query":         query_text or query_sql or "",
        "sql_executed":  "",
        "data":          [],
        "row_count":     0,
        "cases_present": db.get_cases(conn, deal_id),
        "conflicts":     [],
        "scenario_result": None,
        "metadata":      {},
        "cost_usd":      0.0,
    }

    # Translate NL to SQL
    if query_text and not query_sql:
        sql, error = _nl_to_sql(query_text, deal_id, data_type, case_name,
                                 period_start, period_end, main_llm, audit_llm)
        if error:
            result["metadata"]["error"] = error
            return result
        query_sql = sql

    # Direct SQL mode
    if query_sql:
        # Safety check
        if _BLOCKED_KEYWORDS.search(query_sql):
            result["metadata"]["error"] = "Query contains disallowed SQL keywords"
            return result

        try:
            rows = db.query_all(conn, query_sql, ())
            result["sql_executed"] = query_sql
            result["data"] = rows
            result["row_count"] = len(rows)
        except Exception as e:
            result["metadata"]["error"] = f"SQL execution error: {e}"
            return result
    else:
        # No query at all — return summary
        result["data"] = _build_summary(conn, deal_id)
        result["row_count"] = len(result["data"])

    # Attach conflicts if requested
    if include_metadata:
        result["conflicts"] = db.get_conflicts(conn, deal_id, severity=None)
        result["metadata"]["total_data_points"] = db.count_data_points(conn, deal_id)
        result["metadata"]["source_docs"] = [
            d.get("filename") for d in db.get_source_docs(conn, deal_id)
        ]

    # Scenario re-evaluation
    if scenario and formula_engine_fn:
        result["scenario_result"] = formula_engine_fn(scenario)

    return result


# ── NL → SQL translation ───────────────────────────────────────────────────────

def _nl_to_sql(
    query_text: str,
    deal_id: str,
    data_type: str | None,
    case_name: str | None,
    period_start: str | None,
    period_end: str | None,
    main_llm: Any,
    audit_llm: Any,
) -> tuple[str | None, str | None]:
    """
    Translate natural language query to SQL using LLM.
    Returns (sql, error_message).
    """
    if not main_llm:
        return None, "LLM not available for natural language query translation"

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        filters = []
        if case_name:
            filters.append(f"case_name = '{case_name}'")
        if period_start:
            filters.append(f"period_start >= '{period_start}'")
        if period_end:
            filters.append(f"period_end <= '{period_end}'")
        filter_hint = ("Additional filters to apply: " + " AND ".join(filters)) if filters else ""

        prompt = f"""You are translating a natural language query about an oil & gas deal database into SQL.

{_SCHEMA_SUMMARY}

Deal ID: '{deal_id}'
{f"Focus on data_type: {data_type}" if data_type else ""}
{filter_hint}

User query: "{query_text}"

Generate a single SQLite SELECT statement that answers this query.
Always include WHERE deal_id = '{deal_id}' (or join via deal_id).
Use proper aggregations (AVG, SUM, MAX) when the query asks for averages/totals.
IMPORTANT: Return ONLY the SQL statement, no explanation."""

        messages = [
            SystemMessage(content="You are an expert SQL query writer for SQLite. Return only valid SQL."),
            HumanMessage(content=prompt),
        ]
        response = main_llm.invoke(messages)
        sql = response.content.strip()
        sql = re.sub(r"^```(?:sql)?\n?", "", sql)
        sql = re.sub(r"\n?```$", "", sql).strip()

        # Audit LLM validates the SQL
        if audit_llm:
            validated, error = _audit_sql(sql, query_text, deal_id, audit_llm)
            if error:
                return None, f"SQL validation failed: {error}"
            sql = validated

        if _BLOCKED_KEYWORDS.search(sql):
            return None, "Generated SQL contains disallowed keywords"

        return sql, None

    except Exception as e:
        return None, f"NL→SQL translation failed: {e}"


def _audit_sql(
    sql: str,
    original_query: str,
    deal_id: str,
    audit_llm: Any,
) -> tuple[str, str | None]:
    """
    Audit LLM validates and optionally corrects the generated SQL.
    Returns (possibly_corrected_sql, error_or_None).
    """
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = f"""Validate this SQLite query:

Original question: "{original_query}"
Generated SQL:
{sql}

Rules:
1. Must have WHERE deal_id = '{deal_id}' somewhere in the query
2. Must be a SELECT statement only (no INSERT, UPDATE, DELETE, DROP, etc.)
3. Must reference valid table/column names from this schema:
{_SCHEMA_SUMMARY}
4. Must correctly answer the original question

If the SQL is valid, return it unchanged.
If there are issues, fix them and return the corrected SQL.
If it cannot be fixed, return INVALID: <reason>

Return ONLY the SQL or INVALID: <reason>."""

        messages = [
            SystemMessage(content="You are a SQL validator. Return only SQL or INVALID: <reason>."),
            HumanMessage(content=prompt),
        ]
        response = audit_llm.invoke(messages)
        content = response.content.strip()

        if content.upper().startswith("INVALID:"):
            return sql, content[8:].strip()

        # Strip any code fences the audit LLM may add
        content = re.sub(r"^```(?:sql)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content).strip()
        return content, None

    except Exception as e:
        # Audit failure is non-fatal — use original SQL
        return sql, None


# ── Summary query ──────────────────────────────────────────────────────────────

def _build_summary(conn: sqlite3.Connection, deal_id: str) -> list[dict[str, Any]]:
    """Return a high-level data summary when no query is specified."""
    summary = []
    for table, col in [
        ("production_series",  "product"),
        ("financial_series",   "line_item"),
        ("reserve_estimates",  "reserve_class"),
        ("cost_benchmarks",    "metric"),
        ("scalar_datapoints",  "category"),
    ]:
        try:
            rows = db.query_all(
                conn,
                f"SELECT '{table}' as table_name, {col} as group_by, COUNT(*) as count "
                f"FROM {table} WHERE deal_id = ? GROUP BY {col}",
                (deal_id,),
            )
            summary.extend(rows)
        except Exception:
            continue
    return summary
