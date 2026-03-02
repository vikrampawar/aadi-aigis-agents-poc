"""
CLI entry point for Agent 07 — Well Performance Intelligence Cards.

Usage:
    # Full fleet run (standalone)
    python -m aigis_agents.agent_07_well_cards \\
        --deal-id project-corsair-001 \\
        --output-dir ./outputs

    # Single-well card
    python -m aigis_agents.agent_07_well_cards \\
        --deal-id project-corsair-001 \\
        --well-name "THUNDER HAWK-001" \\
        --output-dir ./outputs

    # Compact JSON output (tool_call mode)
    python -m aigis_agents.agent_07_well_cards \\
        --deal-id project-corsair-001 \\
        --mode tool_call
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("agent07.cli")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m aigis_agents.agent_07_well_cards",
        description="Agent 07 — Well Performance Intelligence Cards",
    )
    p.add_argument("--deal-id",              required=True, help="Aigis deal identifier")
    p.add_argument("--well-name",            default=None,  help="Single well name (omit for fleet run)")
    p.add_argument("--output-dir",           default="./outputs", help="Root output directory")
    p.add_argument("--mode",                 default="standalone", choices=["standalone", "tool_call"])
    p.add_argument("--model",                default="gpt-4.1",    help="LLM model key")
    p.add_argument("--downtime-treatment",   default="strip_estimated",
                   choices=["strip_estimated", "use_raw"])
    p.add_argument("--default-uptime-pct",   type=float, default=90.0,
                   help="Assumed uptime %% when no actuals (default: 90)")
    p.add_argument("--forecast-case",        default="cpr_base_case",
                   help="DB case name for CPR forecast")
    p.add_argument("--economic-limit-boepd", type=float, default=25.0,
                   help="EUR economic limit (boe/d)")
    p.add_argument("--projection-years",     type=int,   default=20,
                   help="DCA EUR projection horizon (years)")
    p.add_argument("--entity-context",       default="",
                   help="Entity-level context string (optional, overrides auto-loaded)")
    p.add_argument("--no-charts",            action="store_true",
                   help="Skip chart generation")
    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args   = parser.parse_args(argv)

    # ── Build LLM ─────────────────────────────────────────────────────────────
    try:
        from aigis_agents.shared.llm_bridge import get_chat_model
        llm = get_chat_model(args.model, session_keys={})
        log.info("LLM loaded: %s", args.model)
    except Exception as exc:
        log.error("Could not load LLM (%s): %s — continuing without LLM narrative", args.model, exc)
        llm = _FallbackLLM()

    # ── Invoke agent ──────────────────────────────────────────────────────────
    from aigis_agents.agent_07_well_cards.agent import Agent07

    log.info(
        "Agent 07 | deal=%s | well=%s | mode=%s",
        args.deal_id, args.well_name or "<fleet>", args.mode,
    )

    result = Agent07().invoke(
        mode                 = args.mode,
        deal_id              = args.deal_id,
        output_dir           = args.output_dir,
        well_name            = args.well_name,
        downtime_treatment   = args.downtime_treatment,
        default_uptime_pct   = args.default_uptime_pct,
        forecast_case        = args.forecast_case,
        economic_limit_boepd = args.economic_limit_boepd,
        projection_years     = args.projection_years,
        entity_context       = args.entity_context,
        _llm_override        = llm,
    )

    # ── Output ────────────────────────────────────────────────────────────────
    if args.mode == "tool_call":
        # Print compact JSON (strip internal keys)
        clean = {k: v for k, v in result.items() if not k.startswith("_production")}
        print(json.dumps(clean, indent=2, default=str))
    else:
        # Print summary to stdout; files already written by agent
        _print_summary(result, args.well_name)


def _print_summary(result: dict, well_name: str | None) -> None:
    """Print a human-readable summary to the terminal."""
    if well_name:
        # Single-well
        rag = result.get("rag_status", "?")
        emoji = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴", "BLACK": "⚫"}.get(rag, "")
        print(f"\n{emoji} Well: {result.get('well_name', well_name)}")
        print(f"   RAG:       {rag} — {result.get('rag_label', '')}")
        m = result.get("metrics", {})
        if m.get("current_rate_boepd"):
            print(f"   Rate:      {m['current_rate_boepd']:,.0f} boe/d")
        dc = result.get("decline_curve", {})
        if dc.get("eur_mmboe"):
            print(f"   EUR (DCA): {dc['eur_mmboe']:.3f} MMboe")
        flags = result.get("flags", [])
        if flags:
            print(f"   Flags ({len(flags)}):")
            for f in flags[:3]:
                print(f"     • {f[:100]}")
            if len(flags) > 3:
                print(f"     … +{len(flags)-3} more")
    else:
        # Fleet
        n   = result.get("total_wells", 0)
        rag = result.get("rag_summary", {})
        fm  = result.get("fleet_metrics", {})
        print(f"\n📊 Agent 07 Fleet Report — {n} wells")
        print(f"   RAG:  🟢{rag.get('GREEN',0)}  🟡{rag.get('AMBER',0)}  🔴{rag.get('RED',0)}  ⚫{rag.get('BLACK',0)}")
        if fm.get("total_current_rate_boepd"):
            print(f"   Rate: {fm['total_current_rate_boepd']:,.0f} boe/d")
        if fm.get("total_eur_mmboe"):
            print(f"   EUR:  {fm['total_eur_mmboe']:.2f} MMboe")
        if fm.get("critical_flag_count"):
            print(f"   ⚠️  Critical flags: {fm['critical_flag_count']}")
        paths = result.get("output_paths", {})
        if paths.get("md_report"):
            print(f"\n   Report:    {paths['md_report']}")
        if paths.get("html_dashboard"):
            print(f"   Dashboard: {paths['html_dashboard']}")
    print()


class _FallbackLLM:
    """Minimal stub when LLM is unavailable (e.g. no API key in CI)."""
    def invoke(self, messages):
        class _R:
            content = '{"b_flag":null,"di_flag":null,"eur_flag":null,"red_flags":[],"narrative":"No LLM available — automated DCA analysis only."}'
        return _R()


if __name__ == "__main__":
    main()
