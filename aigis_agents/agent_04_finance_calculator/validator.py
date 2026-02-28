"""
Benchmark validation and financial quality flags for Agent 04 — Finance Calculator.

Checks computed metrics against ranges from agent_04_finance_knowledge_bank_v1.0.md.
Generates FinancialQualityFlag objects with severity and actionable message.
"""

from __future__ import annotations

from aigis_agents.agent_04_finance_calculator.models import (
    DealType,
    FinancialAnalysisSummary,
    FinancialQualityFlag,
    Jurisdiction,
)


def _flag(severity: str, metric: str, value: float | None, threshold: str, message: str) -> FinancialQualityFlag:
    return FinancialQualityFlag(severity=severity, metric=metric, value=value, threshold=threshold, message=message)


def validate_metrics(
    summary: FinancialAnalysisSummary,
    jurisdiction: Jurisdiction,
    deal_type: DealType,
) -> list[FinancialQualityFlag]:
    """
    Validate headline financial metrics against benchmark ranges.

    Benchmark sources:
    - agent_04_finance_knowledge_bank_v1.0.md (Red Flag Range column)
    - financial_analyst_playbook.md (Section 3–6)
    - GoM-specific ranges from deal history and industry publications

    Returns list of FinancialQualityFlag sorted by severity (🔴 first).
    """
    flags: list[FinancialQualityFlag] = []

    # ── NPV / IRR ──────────────────────────────────────────────────────────────

    if summary.irr_pct is not None:
        if summary.irr_pct < 10.0:
            flags.append(_flag(
                "🔴 CRITICAL", "IRR", summary.irr_pct,
                ">15% hurdle", f"IRR {summary.irr_pct:.1f}% is below typical 15% hurdle rate — project may not meet investment criteria"
            ))
        elif summary.irr_pct < 15.0:
            flags.append(_flag(
                "🟡 WARNING", "IRR", summary.irr_pct,
                ">15% hurdle", f"IRR {summary.irr_pct:.1f}% is below typical 15% hurdle rate; marginal project economics"
            ))
        elif summary.irr_pct >= 25.0:
            flags.append(_flag(
                "🟢 INFO", "IRR", summary.irr_pct,
                "Benchmark: 15–25% strong", f"IRR {summary.irr_pct:.1f}% is strong — verify assumptions for optimism bias"
            ))

    if summary.npv_10_usd is not None and summary.npv_10_usd < 0:
        flags.append(_flag(
            "🔴 CRITICAL", "NPV@10%", summary.npv_10_usd,
            ">0 required", f"NPV at 10% is negative (${summary.npv_10_usd/1e6:.1f}M) — deal destroys value at this price and production profile"
        ))

    # ── Payback ────────────────────────────────────────────────────────────────

    if summary.payback_years is not None:
        if summary.payback_years > 8.0:
            flags.append(_flag(
                "🔴 CRITICAL", "Payback Period", summary.payback_years,
                "<5yr preferred, <8yr acceptable", f"Payback of {summary.payback_years:.1f} years is very long — significant asset life risk"
            ))
        elif summary.payback_years > 5.0:
            flags.append(_flag(
                "🟡 WARNING", "Payback Period", summary.payback_years,
                "<5yr preferred", f"Payback of {summary.payback_years:.1f} years is above 5yr preference — exposure to oil price cycle risk"
            ))

    # ── Lifting Cost ───────────────────────────────────────────────────────────

    if summary.loe_per_boe is not None:
        # Benchmark varies by jurisdiction and water depth
        if jurisdiction == Jurisdiction.GoM:
            loe_warn = 30.0
            loe_crit = 50.0
            benchmark_desc = "GoM shallow water: $8–$35/boe; deepwater: $25–$80/boe"
        elif jurisdiction == Jurisdiction.UKCS:
            loe_warn = 35.0
            loe_crit = 55.0
            benchmark_desc = "UKCS producing: $15–$50/boe typical"
        elif jurisdiction == Jurisdiction.Norway:
            loe_warn = 20.0
            loe_crit = 35.0
            benchmark_desc = "Norway producing: $8–$25/boe typical (lower cost base)"
        else:
            loe_warn = 30.0
            loe_crit = 50.0
            benchmark_desc = "International: varies widely by location"

        if summary.loe_per_boe > loe_crit:
            flags.append(_flag(
                "🔴 CRITICAL", "LOE/boe", summary.loe_per_boe,
                f"<${loe_crit}/boe ({benchmark_desc})",
                f"LOE of ${summary.loe_per_boe:.1f}/boe is very high — asset likely sub-economic at $60–$70/bbl"
            ))
        elif summary.loe_per_boe > loe_warn:
            flags.append(_flag(
                "🟡 WARNING", "LOE/boe", summary.loe_per_boe,
                f"<${loe_warn}/boe preferred ({benchmark_desc})",
                f"LOE of ${summary.loe_per_boe:.1f}/boe is above typical range — verify OpEx assumptions"
            ))

    # ── Cash Breakeven ─────────────────────────────────────────────────────────

    if summary.cash_breakeven_usd_bbl is not None:
        if summary.cash_breakeven_usd_bbl > 65.0:
            flags.append(_flag(
                "🔴 CRITICAL", "Cash Breakeven", summary.cash_breakeven_usd_bbl,
                "<$50/bbl preferred", f"Cash breakeven ${summary.cash_breakeven_usd_bbl:.1f}/bbl is dangerously close to or above current strip price"
            ))
        elif summary.cash_breakeven_usd_bbl > 50.0:
            flags.append(_flag(
                "🟡 WARNING", "Cash Breakeven", summary.cash_breakeven_usd_bbl,
                "<$50/bbl preferred", f"Cash breakeven ${summary.cash_breakeven_usd_bbl:.1f}/bbl leaves limited downside buffer"
            ))

    # ── Netback ────────────────────────────────────────────────────────────────

    if summary.netback_usd_bbl is not None:
        if summary.netback_usd_bbl < 0:
            flags.append(_flag(
                "🔴 CRITICAL", "Netback", summary.netback_usd_bbl,
                ">$0 required", f"Negative netback (${summary.netback_usd_bbl:.1f}/bbl) — field is cash-flow negative at current price and LOE"
            ))
        elif summary.netback_usd_bbl < 10.0:
            flags.append(_flag(
                "🟡 WARNING", "Netback", summary.netback_usd_bbl,
                ">$10/bbl preferred", f"Thin netback (${summary.netback_usd_bbl:.1f}/bbl) — highly sensitive to LOE increases or price declines"
            ))

    # ── EV/2P ──────────────────────────────────────────────────────────────────

    if summary.ev_2p_usd_boe is not None:
        if jurisdiction == Jurisdiction.GoM:
            ev2p_low, ev2p_high = 5.0, 25.0
        elif jurisdiction == Jurisdiction.UKCS:
            ev2p_low, ev2p_high = 4.0, 20.0
        elif jurisdiction == Jurisdiction.Norway:
            ev2p_low, ev2p_high = 6.0, 22.0
        else:
            ev2p_low, ev2p_high = 3.0, 20.0

        if summary.ev_2p_usd_boe > ev2p_high:
            flags.append(_flag(
                "🟡 WARNING", "EV/2P", summary.ev_2p_usd_boe,
                f"${ev2p_low}–${ev2p_high}/boe typical ({jurisdiction.value})",
                f"EV/2P of ${summary.ev_2p_usd_boe:.1f}/boe is above typical range — seller pricing in significant upside"
            ))
        elif summary.ev_2p_usd_boe < ev2p_low:
            flags.append(_flag(
                "🟢 INFO", "EV/2P", summary.ev_2p_usd_boe,
                f"${ev2p_low}–${ev2p_high}/boe typical ({jurisdiction.value})",
                f"EV/2P of ${summary.ev_2p_usd_boe:.1f}/boe is below typical range — potential value opportunity; verify reserve quality"
            ))

    # ── Government Take ────────────────────────────────────────────────────────

    if summary.government_take_pct is not None:
        if summary.government_take_pct > 80.0:
            flags.append(_flag(
                "🔴 CRITICAL", "Government Take", summary.government_take_pct,
                "<80% typical", f"Government take of {summary.government_take_pct:.1f}% is very high — limited contractor upside; verify fiscal terms"
            ))
        elif summary.government_take_pct > 75.0:
            flags.append(_flag(
                "🟡 WARNING", "Government Take", summary.government_take_pct,
                "<75% preferred", f"Government take of {summary.government_take_pct:.1f}% is elevated — typical for Norway/high-tax regimes"
            ))

    # ── Full-Cycle Breakeven vs LOE Breakeven ─────────────────────────────────

    if summary.full_cycle_breakeven_usd_bbl is not None:
        if summary.full_cycle_breakeven_usd_bbl > 80.0:
            flags.append(_flag(
                "🔴 CRITICAL", "Full-Cycle Breakeven", summary.full_cycle_breakeven_usd_bbl,
                "<$60/bbl required", f"Full-cycle breakeven ${summary.full_cycle_breakeven_usd_bbl:.1f}/bbl — deal does not generate returns at current oil price strip"
            ))
        elif summary.full_cycle_breakeven_usd_bbl > 65.0:
            flags.append(_flag(
                "🟡 WARNING", "Full-Cycle Breakeven", summary.full_cycle_breakeven_usd_bbl,
                "<$65/bbl preferred", f"Full-cycle breakeven ${summary.full_cycle_breakeven_usd_bbl:.1f}/bbl — marginal returns; sensitive to price downturn"
            ))

    # ── DSCR / LLCR (if provided) ─────────────────────────────────────────────

    if summary.borrowing_base_usd is not None and summary.borrowing_base_usd < 0:
        flags.append(_flag(
            "🔴 CRITICAL", "Borrowing Base", summary.borrowing_base_usd,
            ">0 required", "Negative borrowing base — asset cannot support RBL facility"
        ))

    # Sort: 🔴 CRITICAL first, then 🟡 WARNING, then 🟢 INFO
    severity_order = {"🔴 CRITICAL": 0, "🟡 WARNING": 1, "🟢 INFO": 2}
    flags.sort(key=lambda f: severity_order.get(f.severity, 99))

    return flags
