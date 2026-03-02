"""
Agent 07 — Well Performance Intelligence Cards.

Top-level orchestrator. Extends AgentBase and follows the 10-step pipeline.

Modes:
  - well_name provided  → single-well JSON card
  - well_name=None      → full fleet run (standalone: MD report + charts + HTML dashboard)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aigis_agents.mesh.agent_base import AgentBase

log = logging.getLogger(__name__)


class Agent07(AgentBase):
    """Well Performance Intelligence Cards agent."""

    AGENT_ID = "agent_07"
    DK_TAGS  = ["technical", "upstream_dd", "oil_gas_101"]

    def _run(
        self,
        deal_id:              str,
        main_llm:             Any,
        dk_context:           str,
        buyer_context:        str        = "",
        deal_context:         str        = "",
        entity_context:       str        = "",
        patterns:             list[dict] | None = None,
        mode:                 str        = "standalone",
        output_dir:           str        = "./outputs",
        # ── Agent 07-specific parameters ──────────────────────────────────────
        well_name:            str | None = None,    # None → full fleet run
        downtime_treatment:   str        = "strip_estimated",
        default_uptime_pct:   float      = 90.0,
        forecast_case:        str        = "cpr_base_case",
        economic_limit_boepd: float      = 25.0,
        projection_years:     int        = 20,
        **_,
    ) -> dict:
        """
        Execute the Well Performance Intelligence Cards pipeline.

        Args:
            deal_id:              Aigis deal identifier.
            main_llm:             LangChain-compatible LLM instance.
            dk_context:           Domain knowledge text (GoM playbooks, benchmarks).
            buyer_context:        Buyer profile (injected by AgentBase).
            deal_context:         Accumulated deal context from prior agents.
            entity_context:       Entity-level context (field, company, well details).
            patterns:             Learned patterns from MemoryManager.
            mode:                 "standalone" → full output; "tool_call" → compact JSON.
            output_dir:           Root output directory.
            well_name:            If provided, run single-well only. Otherwise fleet run.
            downtime_treatment:   "strip_estimated" (default) or "use_raw".
            default_uptime_pct:   Uptime assumption when no actuals available.
            forecast_case:        DB case name for CPR forecast.
            economic_limit_boepd: EUR abandonment rate.
            projection_years:     DCA EUR projection horizon.

        Returns:
            Single-well card dict or fleet dict with _deal_context_section.
        """
        patterns = patterns or []
        ts_start = datetime.now(timezone.utc).isoformat()

        # ── Resolve output paths ──────────────────────────────────────────────
        deal_dir    = os.path.join(output_dir, deal_id)
        charts_dir  = os.path.join(deal_dir, "07_well_charts")
        report_path = os.path.join(deal_dir, "07_well_performance_report.md")
        dash_path   = os.path.join(deal_dir, "07_fleet_dashboard.html")
        fleet_chart = os.path.join(charts_dir, "fleet_summary.png")

        if mode == "standalone":
            Path(charts_dir).mkdir(parents=True, exist_ok=True)

        # ── Load well list ────────────────────────────────────────────────────
        from aigis_agents.agent_07_well_cards.production_processor import load_well_names

        if well_name:
            well_names = [well_name]
        else:
            well_names = load_well_names(deal_id, output_dir)

        if not well_names:
            log.warning("Agent07: no wells found for deal %s", deal_id)
            return {
                "deal_id":   deal_id,
                "status":    "no_data",
                "error":     "No wells found in production_series for this deal_id",
                "well_cards": [],
            }

        log.info("Agent07: processing %d well(s) for deal %s", len(well_names), deal_id)

        # ── Build well cards ──────────────────────────────────────────────────
        from aigis_agents.agent_07_well_cards.well_card_builder import build_well_card

        well_cards: list[dict] = []
        for wn in well_names:
            log.info("Agent07: building card for well %s", wn)
            try:
                card = build_well_card(
                    deal_id              = deal_id,
                    well_name            = wn,
                    main_llm             = main_llm,
                    dk_context           = dk_context,
                    entity_context       = entity_context,
                    patterns             = patterns,
                    output_dir           = output_dir,
                    downtime_treatment   = downtime_treatment,
                    default_uptime_pct   = default_uptime_pct,
                    forecast_case        = forecast_case,
                    economic_limit_boepd = economic_limit_boepd,
                    projection_years     = projection_years,
                    charts_dir           = charts_dir if mode == "standalone" else None,
                    generate_charts      = (mode == "standalone"),
                )
                well_cards.append(card)
            except Exception as exc:
                log.error("Agent07: failed to build card for %s: %s", wn, exc)
                well_cards.append({
                    "deal_id":   deal_id,
                    "well_name": wn,
                    "rag_status": "BLACK",
                    "rag_label":  "Error — card generation failed",
                    "rag_emoji":  "⚫",
                    "flags":     [f"Card generation error: {exc}"],
                    "narrative":  "",
                    "metrics":    {},
                    "decline_curve": {},
                    "data_quality": {"months_of_data": 0, "completeness_pct": 0},
                })

        # ── Single-well mode: return card directly ────────────────────────────
        if well_name:
            card = well_cards[0] if well_cards else {}
            return _single_well_result(card, deal_id, well_name, mode, deal_context)

        # ── Fleet mode: aggregate + report + dashboard ────────────────────────
        from aigis_agents.agent_07_well_cards.rag_classifier import summarize_fleet_rag

        fleet_stats = summarize_fleet_rag(well_cards)
        fleet_stats["total_wells"] = len(well_cards)

        # Deal name from deal_context or fallback
        deal_name = _extract_deal_name(deal_context) or deal_id

        output_paths: dict = {}

        if mode == "standalone":
            # Fleet summary chart
            try:
                from aigis_agents.agent_07_well_cards.chart_generator import (
                    generate_fleet_summary_chart,
                    generate_fleet_dashboard,
                )
                generate_fleet_summary_chart(well_cards, fleet_chart)
                generate_fleet_dashboard(well_cards, dash_path, deal_name=deal_name)
            except Exception as exc:
                log.warning("Agent07: chart/dashboard generation failed: %s", exc)

            # MD report
            try:
                from aigis_agents.agent_07_well_cards.report_generator import generate_md_report
                generate_md_report(
                    well_cards           = well_cards,
                    deal_name            = deal_name,
                    deal_id              = deal_id,
                    output_path          = report_path,
                    fleet_chart_path     = fleet_chart if os.path.exists(fleet_chart) else None,
                    dashboard_path       = dash_path   if os.path.exists(dash_path)   else None,
                    downtime_treatment   = downtime_treatment,
                    default_uptime_pct   = default_uptime_pct,
                    forecast_case        = forecast_case,
                    economic_limit_boepd = economic_limit_boepd,
                    projection_years     = projection_years,
                )
            except Exception as exc:
                log.error("Agent07: report generation failed: %s", exc)

            output_paths = {
                "md_report":       report_path,
                "html_dashboard":  dash_path,
                "well_charts_dir": charts_dir,
            }

        # ── _deal_context_section ─────────────────────────────────────────────
        rag = fleet_stats.get("rag_summary", {})
        total_eur = fleet_stats.get("total_eur_mmboe", 0)

        # Try to pull CPR total EUR for comparison
        cpr_total = _sum_cpr_eur(well_cards)
        if cpr_total:
            eur_var_str = f" vs CPR {cpr_total:.1f} MMboe ({(total_eur - cpr_total)/cpr_total:+.0%})"
        else:
            eur_var_str = ""

        deal_context_section = {
            "section_name": "Agent 07 — Well Performance Summary",
            "content": (
                f"Fleet: {len(well_cards)} wells | "
                f"RAG: {rag.get('GREEN',0)}G/{rag.get('AMBER',0)}A/"
                f"{rag.get('RED',0)}R/{rag.get('BLACK',0)}B | "
                f"EUR: {total_eur:.1f} MMboe{eur_var_str} | "
                f"Critical flags: {fleet_stats.get('critical_flag_count', 0)}"
            ),
            "generated_at": ts_start,
        }

        return {
            "deal_id":     deal_id,
            "total_wells": len(well_cards),
            "rag_summary": rag,
            "fleet_metrics": {
                "total_current_rate_boepd":  fleet_stats.get("total_current_rate_boepd", 0),
                "total_eur_mmboe":           total_eur,
                "eur_vs_cpr_pct":            round((total_eur - cpr_total) / cpr_total * 100, 1)
                                             if cpr_total else None,
                "critical_flag_count":       fleet_stats.get("critical_flag_count", 0),
                "weighted_decline_rate_pct": fleet_stats.get("weighted_decline_rate_pct"),
            },
            "well_cards":    well_cards,
            "output_paths":  output_paths,
            "_deal_context_section": deal_context_section,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _single_well_result(
    card: dict,
    deal_id: str,
    well_name: str,
    mode: str,
    deal_context: str,
) -> dict:
    """Strip internal keys and build the single-well return dict."""
    result = {k: v for k, v in card.items() if not k.startswith("_")}
    result["deal_id"]   = deal_id
    result["well_name"] = well_name

    if mode == "standalone":
        rag = card.get("rag_status", "GREEN")
        result["_deal_context_section"] = {
            "section_name": f"Agent 07 — {well_name} Well Card",
            "content": (
                f"Well: {well_name} | RAG: {rag} — {card.get('rag_label', '')} | "
                f"Rate: {card.get('metrics', {}).get('current_rate_boepd', 0):,.0f} boe/d | "
                f"EUR: {card.get('decline_curve', {}).get('eur_mmboe', 0):.3f} MMboe"
            ),
        }

    return result


def _extract_deal_name(deal_context: str) -> str | None:
    """Extract deal name from deal_context string (best effort)."""
    if not deal_context:
        return None
    for line in deal_context.splitlines():
        if "deal" in line.lower() or "asset" in line.lower() or "project" in line.lower():
            stripped = line.strip().lstrip("#").strip()
            if stripped and len(stripped) < 80:
                return stripped
    return None


def _sum_cpr_eur(well_cards: list[dict]) -> float | None:
    """Sum CPR 2P EUR across all wells (returns None if no data)."""
    total = 0.0
    found = False
    for card in well_cards:
        cpr = card.get("reserve_estimates", {}).get("2P")
        if cpr:
            total += cpr
            found = True
    return round(total, 3) if found else None
