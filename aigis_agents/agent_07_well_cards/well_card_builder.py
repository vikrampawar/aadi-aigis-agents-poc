"""
Well Card Builder for Agent 07.

Orchestrates:
  1. Load production history from Agent 02 SQLite DB
  2. Downtime normalization
  3. Secondary metrics (GOR, WC, trends)
  4. DCA fitting via dca_engine
  5. RAG classification via rag_classifier
  6. LLM narrative + anomaly flags via DCA_REVIEW_PROMPT
  7. Chart generation via chart_generator
  8. Assemble final WellCard dict
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from aigis_agents.agent_07_well_cards.dca_engine import fit_decline_curve
from aigis_agents.agent_07_well_cards.production_processor import (
    load_production_series,
    load_reserve_estimates,
    load_scalar_metrics,
    pivot_production,
    pivot_forecast,
    normalize_production,
    compute_secondary_metrics,
    compute_summary_stats,
    extract_cpr_eur,
)
from aigis_agents.agent_07_well_cards.rag_classifier import (
    classify_well,
    RAGResult,
)

log = logging.getLogger(__name__)

# ── LLM prompt template ───────────────────────────────────────────────────────

DCA_REVIEW_PROMPT = """You are a senior reservoir engineer conducting M&A due diligence.
Review the Decline Curve Analysis (DCA) and production trends for well {well_name}.

DOMAIN KNOWLEDGE CONTEXT:
{dk_context}

ENTITY CONTEXT:
{entity_context}

DCA PARAMETERS:
  Curve type:     {curve_type}
  qi (initial):   {qi:.0f} boe/d
  Di (annual):    {di:.1f}%/yr
  b-factor:       {b:.3f}
  EUR (DCA):      {eur:.3f} MMboe
  Fit R²:         {r2:.3f}
  Months of data: {months}

CPR RESERVE ESTIMATES:
  1P EUR: {cpr_1p}
  2P EUR: {cpr_2p}
  3P EUR: {cpr_3p}

PRODUCTION TRENDS:
  Current rate:       {current_rate:.0f} boe/d
  Peak rate:          {peak_rate:.0f} boe/d
  Cumulative:         {cumulative:.3f} MMboe
  12-month trend:     {trend_12m:+.1f}%
  GOR (latest):       {gor_latest} scf/stb
  GOR trend 12m:      {gor_trend:+.1f}%
  Water cut (latest): {wc_latest:.1f}%
  WC trend 12m:       {wc_trend:+.1f} ppts
  Uptime:             {uptime:.1f}% ({uptime_source})

DCA FLAGS FROM AUTOMATED ANALYSIS:
{dca_flags}

RAG STATUS: {rag_status} — {rag_label}
RAG FLAGS:
{rag_flags}

TASKS — respond ONLY with the JSON object below (no markdown, no prose outside JSON):
1. Validate the b-factor ({b:.3f}) against the stated drive mechanism in entity context. Flag if inconsistent with GoM Miocene deepwater benchmarks (b=0.3–0.7 for partial water drive).
2. Comment on the annual decline rate ({di:.1f}%/yr) vs. GoM deepwater benchmarks (15–25%/yr initial; 3–6%/yr terminal). Is it plausible given the well's age and production history?
3. If DCA EUR ({eur:.3f} MMboe) deviates more than ±15% from CPR 2P ({cpr_2p}), identify the likely cause.
4. List the top 2–3 reservoir engineering red flags relevant to this well.
5. Write a 3–4 sentence well card narrative suitable for a due diligence report, citing specific numbers and comparing against CPR forecasts.

Return JSON ONLY:
{{
  "b_flag": "<string or null>",
  "di_flag": "<string or null>",
  "eur_flag": "<string or null>",
  "red_flags": ["<flag 1>", "<flag 2>"],
  "narrative": "<3-4 sentence narrative>"
}}"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(val: Any, fmt: str = ".1f", fallback: str = "N/A") -> str:
    if val is None:
        return fallback
    try:
        return format(val, fmt)
    except (TypeError, ValueError):
        return fallback


def _format_flags(flags: list[str]) -> str:
    if not flags:
        return "  None"
    return "\n".join(f"  - {f}" for f in flags)


def _call_llm_for_narrative(
    well_name: str,
    dca_result: Any,
    rag_result: RAGResult,
    summary: dict,
    reserve_estimates: dict,
    dk_context: str,
    entity_context: str,
    main_llm: Any,
) -> dict:
    """
    Call main_llm with DCA_REVIEW_PROMPT and parse the JSON response.
    Returns dict with keys: b_flag, di_flag, eur_flag, red_flags, narrative.
    Falls back to empty values on any failure.
    """
    cpr_1p = f"{reserve_estimates.get('1P'):.3f} MMboe" if reserve_estimates.get("1P") else "Not provided"
    cpr_2p = f"{reserve_estimates.get('2P'):.3f} MMboe" if reserve_estimates.get("2P") else "Not provided"
    cpr_3p = f"{reserve_estimates.get('3P'):.3f} MMboe" if reserve_estimates.get("3P") else "Not provided"

    prompt = DCA_REVIEW_PROMPT.format(
        well_name=well_name,
        dk_context=dk_context[:2000] if dk_context else "Not provided",
        entity_context=entity_context[:1500] if entity_context else "Not provided",
        curve_type=dca_result.curve_type if dca_result else "N/A",
        qi=dca_result.qi_boepd if dca_result else 0,
        di=dca_result.Di_annual_pct if dca_result else 0,
        b=dca_result.b_factor if dca_result else 0,
        eur=dca_result.eur_mmboe if dca_result else 0,
        r2=dca_result.fit_r2 if dca_result else 0,
        months=dca_result.months_of_data if dca_result else 0,
        cpr_1p=cpr_1p,
        cpr_2p=cpr_2p,
        cpr_3p=cpr_3p,
        current_rate=summary.get("current_rate_boepd", 0) or 0,
        peak_rate=summary.get("peak_rate_boepd", 0) or 0,
        cumulative=summary.get("cumulative_mmboe", 0) or 0,
        trend_12m=summary.get("trend_12m_pct", 0) or 0,
        gor_latest=_safe(summary.get("gor_scf_stb"), ",.0f"),
        gor_trend=summary.get("gor_trend_12m_pct", 0) or 0,
        wc_latest=summary.get("water_cut_pct", 0) or 0,
        wc_trend=summary.get("wc_trend_12m_ppts", 0) or 0,
        uptime=summary.get("uptime_pct", 90.0) or 90.0,
        uptime_source=summary.get("uptime_source", "assumed"),
        dca_flags=_format_flags(dca_result.flags if dca_result else []),
        rag_status=rag_result.status,
        rag_label=rag_result.label,
        rag_flags=_format_flags(rag_result.flags),
    )

    try:
        from langchain_core.messages import HumanMessage
        response = main_llm.invoke([HumanMessage(content=prompt)])
        raw = response.content if hasattr(response, "content") else str(response)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return result
    except Exception as exc:
        log.warning("LLM narrative call failed for %s: %s", well_name, exc)
        return {
            "b_flag":    None,
            "di_flag":   None,
            "eur_flag":  None,
            "red_flags": [],
            "narrative": (
                f"Well {well_name} shows a current rate of "
                f"{summary.get('current_rate_boepd', 0):,.0f} boe/d. "
                f"DCA analysis yielded {dca_result.curve_type if dca_result else 'insufficient data'} "
                f"decline with EUR {dca_result.eur_mmboe:.3f} MMboe. "
                f"RAG status: {rag_result.status} — {rag_result.label}."
            ) if dca_result else f"No DCA available for {well_name}.",
        }


# ── Main builder ──────────────────────────────────────────────────────────────

def build_well_card(
    deal_id:              str,
    well_name:            str,
    main_llm:             Any,
    dk_context:           str,
    entity_context:       str,
    patterns:             list[dict],
    output_dir:           str       = "./outputs",
    downtime_treatment:   str       = "strip_estimated",
    default_uptime_pct:   float     = 90.0,
    forecast_case:        str       = "cpr_base_case",
    economic_limit_boepd: float     = 25.0,
    projection_years:     int       = 20,
    charts_dir:           str | None = None,
    generate_charts:      bool      = True,
) -> dict:
    """
    Build a complete Well Intelligence Card dict for one well.

    Args:
        deal_id:              Aigis deal identifier.
        well_name:            Exact entity_name in production_series table.
        main_llm:             Langchain-compatible LLM instance.
        dk_context:           Domain knowledge text (GoM benchmarks, playbooks).
        entity_context:       Entity-level context from deal documents.
        patterns:             Learned patterns from MemoryManager.
        output_dir:           Root output directory (Agent 02 DB lives here).
        downtime_treatment:   "strip_estimated" (default) or "use_raw".
        default_uptime_pct:   Assumed uptime % when no actual data (GoM: 90%).
        forecast_case:        Which DB case to use for CPR forecast.
        economic_limit_boepd: EUR integration cut-off rate.
        projection_years:     DCA EUR projection horizon.
        charts_dir:           Directory for PNG charts (None → skip charts).
        generate_charts:      Set False to skip chart generation entirely.

    Returns:
        WellCard dict matching the spec return structure.
    """
    data_flags: list[str] = []

    # ── 1. Load production data ───────────────────────────────────────────────
    records = load_production_series(deal_id, well_name, output_dir)
    reserve_records = load_reserve_estimates(deal_id, well_name, output_dir)
    scalar_records  = load_scalar_metrics(deal_id, well_name, output_dir)

    # ── 2. Pivot actuals + forecast ───────────────────────────────────────────
    actual_periods  = pivot_production(records, case_name=None)
    forecast_data   = pivot_forecast(records, forecast_case=forecast_case)

    # ── 3. Downtime normalization ─────────────────────────────────────────────
    uptime_data = None
    if downtime_treatment == "use_raw":
        normalized_periods, norm_flags = list(actual_periods.values()), []
    else:
        normalized_periods, norm_flags = normalize_production(
            actual_periods, uptime_data=uptime_data, default_uptime=default_uptime_pct
        )
    data_flags.extend(norm_flags)

    # ── 4. Secondary metrics (GOR, WC, trends) ────────────────────────────────
    enriched_periods = compute_secondary_metrics(normalized_periods)
    summary          = compute_summary_stats(enriched_periods)
    reserve_ests     = extract_cpr_eur(reserve_records)

    # ── 5. DCA fitting ────────────────────────────────────────────────────────
    import numpy as np
    times = np.array([p.get("month_idx", i) for i, p in enumerate(enriched_periods)], dtype=float)
    rates = np.array([p.get("boe_norm", p.get("boe_boepd", 0)) or 0.0 for p in enriched_periods], dtype=float)

    dca_result = fit_decline_curve(
        times=times,
        rates=rates,
        economic_limit_boepd=economic_limit_boepd,
        projection_years=projection_years,
    )

    # EUR vs CPR 2P
    eur_vs_cpr_pct: float | None = None
    if dca_result.eur_mmboe > 0 and reserve_ests.get("2P"):
        cpr_2p = reserve_ests["2P"]
        eur_vs_cpr_pct = round((dca_result.eur_mmboe - cpr_2p) / cpr_2p * 100, 1)

    # ── 6. RAG classification ─────────────────────────────────────────────────
    current_rate   = summary.get("current_rate_boepd", 0) or 0.0
    forecast_rate  = forecast_data.get(
        enriched_periods[-1]["period"] if enriched_periods else "", {}
    ).get("boe_boepd") if forecast_data else None

    rag_result = classify_well(
        current_rate_boepd  = current_rate,
        forecast_rate_boepd = forecast_rate,
        gor_trend_12m_pct   = summary.get("gor_trend_12m_pct"),
        wc_trend_12m_ppts   = summary.get("wc_trend_12m_ppts"),
        di_annual_pct       = dca_result.Di_annual_pct if dca_result else None,
        fit_r2              = dca_result.fit_r2        if dca_result else None,
        uptime_pct          = summary.get("uptime_pct"),
        well_status         = scalar_records.get("well_status"),
        patterns            = patterns,
    )

    # ── 7. LLM narrative ─────────────────────────────────────────────────────
    llm_output = _call_llm_for_narrative(
        well_name        = well_name,
        dca_result       = dca_result,
        rag_result       = rag_result,
        summary          = summary,
        reserve_estimates = reserve_ests,
        dk_context       = dk_context,
        entity_context   = entity_context,
        main_llm         = main_llm,
    )

    # Merge LLM red_flags into overall flag list
    all_flags = list(rag_result.flags) + list(dca_result.flags)
    for rf in llm_output.get("red_flags", []):
        if rf and rf not in all_flags:
            all_flags.append(rf)
    for key in ("b_flag", "di_flag", "eur_flag"):
        val = llm_output.get(key)
        if val and val not in all_flags:
            all_flags.append(val)

    # ── 8. Charts ─────────────────────────────────────────────────────────────
    chart_path: str | None = None
    if generate_charts and charts_dir:
        try:
            from aigis_agents.agent_07_well_cards.chart_generator import generate_well_chart
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in well_name)
            chart_path = os.path.join(charts_dir, f"{safe_name}_production.png")
            generate_well_chart(
                well_name     = well_name,
                periods       = enriched_periods,
                dca_result    = dca_result,
                forecast_data = forecast_data,
                rag_status    = rag_result.status,
                output_path   = chart_path,
            )
        except Exception as exc:
            log.warning("Chart generation failed for %s: %s", well_name, exc)
            chart_path = None

    # ── 9. Assemble WellCard ──────────────────────────────────────────────────
    months_of_data   = dca_result.months_of_data if dca_result else len(enriched_periods)
    total_periods    = max(len(enriched_periods), 1)
    completeness_pct = round(months_of_data / total_periods * 100, 1)

    card: dict = {
        "deal_id":   deal_id,
        "well_name": well_name,

        "rag_status": rag_result.status,
        "rag_label":  rag_result.label,
        "rag_emoji":  rag_result.emoji,

        "metrics": {
            "current_rate_boepd":  summary.get("current_rate_boepd"),
            "peak_rate_boepd":     summary.get("peak_rate_boepd"),
            "cumulative_mmboe":    summary.get("cumulative_mmboe"),
            "ip30_boepd":          summary.get("ip30_boepd"),
            "ip90_boepd":          summary.get("ip90_boepd"),
            "ip180_boepd":         summary.get("ip180_boepd"),
            "trend_12m_pct":       summary.get("trend_12m_pct"),
            "gor_scf_stb":         summary.get("gor_scf_stb"),
            "gor_trend_12m_pct":   summary.get("gor_trend_12m_pct"),
            "water_cut_pct":       summary.get("water_cut_pct"),
            "wc_trend_12m_ppts":   summary.get("wc_trend_12m_ppts"),
            "uptime_pct":          summary.get("uptime_pct"),
            "uptime_source":       summary.get("uptime_source", "assumed"),
        },

        "decline_curve": {
            "curve_type":        dca_result.curve_type,
            "qi_boepd":          dca_result.qi_boepd,
            "Di_annual_pct":     dca_result.Di_annual_pct,
            "b_factor":          dca_result.b_factor,
            "eur_mmboe":         dca_result.eur_mmboe,
            "eur_vs_cpr_2p_pct": eur_vs_cpr_pct,
            "fit_r2":            dca_result.fit_r2,
            "insufficient_data": dca_result.insufficient_data,
        },

        "reserve_estimates": reserve_ests,

        "flags":     all_flags,
        "narrative": llm_output.get("narrative", ""),
        "learned_overrides": rag_result.learned_overrides,

        "data_quality": {
            "months_of_data":     months_of_data,
            "completeness_pct":   completeness_pct,
            "data_flags":         data_flags,
        },

        "chart_path": chart_path,

        # Internal — used by fleet dashboard production overlay
        "_production_history": enriched_periods,
        "_reserve_estimates":  reserve_ests,
    }

    return card
