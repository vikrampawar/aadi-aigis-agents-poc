"""
Output generation for Agent 04 — Finance Calculator.

Produces:
  - 04_financial_analysis.md  — analyst-friendly markdown report
  - 04_financial_analysis.json — full AgentResult serialised
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aigis_agents.agent_04_finance_calculator.models import (
    AgentResult,
    CalcResult,
    FinancialAnalysisSummary,
    FinancialInputs,
    FinancialQualityFlag,
    SensitivityRow,
    YearlyCashFlow,
)

OUTPUT_SUBFOLDER = "04_finance_calculator"


def _fmt_usd(v: float | None, scale: float = 1e6, decimals: int = 1) -> str:
    if v is None:
        return "N/A"
    scaled = v / scale
    if scale == 1e6:
        return f"${scaled:.{decimals}f}M"
    return f"${v:,.{decimals}f}"


def _fmt_pct(v: float | None) -> str:
    return f"{v:.1f}%" if v is not None else "N/A"


def _fmt_val(v: float | None, unit: str = "") -> str:
    if v is None:
        return "N/A"
    return f"{v:,.2f} {unit}".strip()


def _status_icon(metric: str, value: float | None, summary: FinancialAnalysisSummary,
                 flags: list[FinancialQualityFlag]) -> str:
    if value is None:
        return "⚪"
    for flag in flags:
        if flag.metric == metric:
            if "CRITICAL" in flag.severity:
                return "🔴"
            if "WARNING" in flag.severity:
                return "🟡"
    return "🟢"


def generate_financial_report(
    inputs: FinancialInputs,
    all_metrics: dict[str, CalcResult],
    cash_flows: list[YearlyCashFlow],
    sensitivity: list[SensitivityRow],
    flags: list[FinancialQualityFlag],
    summary: FinancialAnalysisSummary,
    output_dir: Path,
) -> tuple[Path, Path]:
    """
    Generate markdown report and JSON output.

    Returns (md_path, json_path).
    """
    run_dir = Path(output_dir) / inputs.deal_id / OUTPUT_SUBFOLDER
    run_dir.mkdir(parents=True, exist_ok=True)

    md_path = run_dir / "04_financial_analysis.md"
    json_path = run_dir / "04_financial_analysis.json"

    md_content = _render_markdown(inputs, all_metrics, cash_flows, sensitivity, flags, summary)
    md_path.write_text(md_content, encoding="utf-8")

    return md_path, json_path


def _render_markdown(
    inputs: FinancialInputs,
    all_metrics: dict[str, CalcResult],
    cash_flows: list[YearlyCashFlow],
    sensitivity: list[SensitivityRow],
    flags: list[FinancialQualityFlag],
    summary: FinancialAnalysisSummary,
) -> str:
    now = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    parts = []

    # ── Header ────────────────────────────────────────────────────────────────
    parts.append(f"# Financial Analysis Report — {inputs.deal_name}")
    parts.append(
        f"*Generated {now} | Aigis Analytics Agent 04 | "
        f"{inputs.deal_type.value} | {inputs.jurisdiction.value}*"
    )
    if inputs.buyer:
        parts.append(f"*Buyer: {inputs.buyer}*")
    parts.append("")

    # ── Executive Summary ─────────────────────────────────────────────────────
    parts.append("## Executive Summary")
    parts.append("")
    parts.append("| Metric | Value | Status |")
    parts.append("|--------|-------|--------|")

    def _exec_row(label: str, value: str, metric_key: str) -> str:
        icon = _status_icon(metric_key, getattr(summary, metric_key.replace("-", "_"), None), summary, flags)
        return f"| {label} | {value} | {icon} |"

    # Asset value vs acquisition cost — the core deal attractiveness trio
    parts.append(_exec_row("Asset PV10 (Intrinsic Value)", _fmt_usd(summary.npv_10_usd), "NPV@10%"))
    if summary.acquisition_cost_usd is not None:
        parts.append(f"| Acquisition Cost (Bid Price) | {_fmt_usd(summary.acquisition_cost_usd)} | ⚪ |")
    if summary.value_creation_usd is not None:
        vc_icon = "🟢" if summary.value_creation_usd >= 0 else "🔴"
        vc_label = "Value Creation (PV10 − Bid)" if summary.value_creation_usd >= 0 else "Value Destruction (PV10 − Bid)"
        parts.append(f"| **{vc_label}** | **{_fmt_usd(summary.value_creation_usd)}** | {vc_icon} |")
    parts.append(f"| | | |")  # visual separator
    parts.append(_exec_row("IRR", _fmt_pct(summary.irr_pct), "IRR"))
    parts.append(_exec_row("Payback Period", _fmt_val(summary.payback_years, "years"), "Payback Period"))
    parts.append(_exec_row("MOIC", _fmt_val(summary.moic, "×"), "MOIC"))
    parts.append(_exec_row("Lifting Cost (LOE)", _fmt_val(summary.loe_per_boe, "$/boe"), "LOE/boe"))
    parts.append(_exec_row("Netback", _fmt_val(summary.netback_usd_bbl, "$/bbl"), "Netback"))
    parts.append(_exec_row("Cash Breakeven", _fmt_val(summary.cash_breakeven_usd_bbl, "$/bbl"), "Cash Breakeven Oil Price"))
    parts.append(_exec_row("Full-Cycle Breakeven", _fmt_val(summary.full_cycle_breakeven_usd_bbl, "$/bbl"), "Full-Cycle Breakeven Oil Price"))
    if summary.ev_2p_usd_boe is not None:
        parts.append(_exec_row("EV/2P", _fmt_val(summary.ev_2p_usd_boe, "$/boe"), "EV/2P"))
    if summary.government_take_pct is not None:
        parts.append(_exec_row("Government Take", _fmt_pct(summary.government_take_pct), "Government Take"))
    if summary.borrowing_base_usd is not None:
        parts.append(_exec_row("Borrowing Base (est.)", _fmt_usd(summary.borrowing_base_usd), "RBL Borrowing Base Estimate"))
    if summary.eur_mmboe is not None:
        parts.append(f"| EUR | {summary.eur_mmboe:.2f} mmboe | ⚪ |")
    parts.append("")

    # ── Financial Quality Flags ───────────────────────────────────────────────
    parts.append("## Financial Quality Flags")
    if not flags:
        parts.append("🟢 No material financial quality issues identified.")
    else:
        for flag in flags:
            parts.append(f"- **{flag.severity}** — {flag.message}")
            parts.append(f"  *Metric: {flag.metric} = {_fmt_val(flag.value)} | Threshold: {flag.threshold}*")
    parts.append("")

    # ── Section 1: Valuation ──────────────────────────────────────────────────
    parts.append("## Section 1: Valuation Metrics")
    parts.append("")
    valuation_keys = ["NPV @ 10%", "PV10", "NPV at 10%",
                      "Value Creation (PV10 − Acquisition Cost)",
                      "IRR", "Payback Period", "MOIC",
                      "EV/2P", "EV/1P", "EV/Production", "EV/EBITDA"]
    _append_metrics_table(parts, all_metrics, valuation_keys)
    parts.append("")

    # ── Section 2: Production Profile ────────────────────────────────────────
    parts.append("## Section 2: Production Profile & Cash Flows")
    parts.append("")
    if cash_flows:
        parts.append(
            "| Year | Rate (boepd) | Revenue ($M) | Royalty ($M) | OPEX ($M) | "
            "CAPEX ($M) | Tax ($M) | Net CF ($M) | DCF ($M) |"
        )
        parts.append(
            "|------|-------------|-------------|-------------|----------|"
            "----------|---------|------------|---------|"
        )
        total_ncf = 0.0
        total_dcf = 0.0
        for cf in cash_flows:
            r = cf.gross_revenue_usd / 1e6
            roy = cf.royalty_usd / 1e6
            opex = cf.total_opex_usd / 1e6
            capex = cf.capex_usd / 1e6
            tax = cf.income_tax_usd / 1e6
            ncf = cf.net_cash_flow_usd / 1e6
            dcf = cf.discounted_cash_flow_usd / 1e6
            total_ncf += ncf
            total_dcf += dcf
            parts.append(
                f"| {cf.year} | {cf.production_boepd:,.0f} | ${r:.1f} | ${roy:.1f} | "
                f"${opex:.1f} | ${capex:.1f} | ${tax:.1f} | ${ncf:.1f} | ${dcf:.1f} |"
            )
        parts.append(
            f"| **Total** | — | — | — | — | — | — | **${total_ncf:.1f}M** | **${total_dcf:.1f}M** |"
        )
    else:
        parts.append("*No cash flows generated.*")
    parts.append("")

    # ── Section 3: Cost Analysis ──────────────────────────────────────────────
    parts.append("## Section 3: Cost Analysis")
    parts.append("")
    cost_keys = ["Lifting Cost (LOE/boe)", "Netback", "Cash Breakeven Oil Price",
                 "Full-Cycle Breakeven Oil Price", "Total OPEX/boe", "F&D Cost", "Recycle Ratio"]
    _append_metrics_table(parts, all_metrics, cost_keys)
    parts.append("")
    parts.append(f"**Assumptions:** LOE = ${inputs.costs.loe_per_boe:.2f}/boe | "
                 f"G&A = ${inputs.costs.g_and_a_per_boe:.2f}/boe | "
                 f"Workovers = ${inputs.costs.workovers_annual_usd/1e3:.0f}K/yr | "
                 f"Transport = ${inputs.costs.transport_per_boe:.2f}/boe")
    parts.append("")

    # ── Section 4: Fiscal Analysis ────────────────────────────────────────────
    parts.append("## Section 4: Fiscal Analysis")
    parts.append("")
    parts.append(f"**Regime:** {inputs.fiscal.regime.value}")
    parts.append(f"**Royalty:** {inputs.fiscal.royalty_rate_pct}% | "
                 f"**Severance Tax:** {inputs.fiscal.severance_tax_pct}% | "
                 f"**Income Tax (CT):** {inputs.fiscal.income_tax_rate_pct}%")
    parts.append(f"**WI:** {inputs.fiscal.wi_pct}% | **ORRI:** {inputs.fiscal.orri_pct}%")
    parts.append("")
    fiscal_keys = ["Royalty Payment", "Severance Tax", "Net Revenue Interest (NRI)",
                   "Government Take"]
    _append_metrics_table(parts, all_metrics, fiscal_keys)
    parts.append("")

    # ── Section 5: Leverage / RBL ─────────────────────────────────────────────
    parts.append("## Section 5: Leverage / RBL")
    parts.append("")
    rbl_keys = ["RBL Borrowing Base Estimate", "LLCR", "DSCR", "Net Debt/EBITDA"]
    rbl_metrics = {k: v for k, v in all_metrics.items() if k in rbl_keys}
    if rbl_metrics:
        _append_metrics_table(parts, all_metrics, rbl_keys)
    else:
        parts.append("*RBL assumptions not provided — borrowing base estimate requires PDP PV10 input.*")
    parts.append("")

    # ── Section 6: Sensitivity — Tornado ─────────────────────────────────────
    parts.append("## Section 6: Sensitivity Analysis — Tornado Chart")
    parts.append(f"*Asset PV10 (base case, acquisition cost excluded): {_fmt_usd(summary.npv_10_usd)}*")
    if summary.acquisition_cost_usd is not None:
        parts.append(f"*Acquisition Cost (bid price, fixed): {_fmt_usd(summary.acquisition_cost_usd)}*")
    parts.append("")
    if sensitivity:
        parts.append("| Variable | -20% NPV | -10% NPV | Base NPV | +10% NPV | +20% NPV | Swing |")
        parts.append("|----------|----------|----------|----------|----------|----------|-------|")
        for row in sensitivity:
            def _npv_cell(v: float | None) -> str:
                return _fmt_usd(v) if v is not None else "—"
            parts.append(
                f"| {row.variable_label} | {_npv_cell(row.minus_20_pct_npv)} | "
                f"{_npv_cell(row.minus_10_pct_npv)} | {_fmt_usd(row.base_npv_usd)} | "
                f"{_npv_cell(row.plus_10_pct_npv)} | {_npv_cell(row.plus_20_pct_npv)} | "
                f"{_fmt_usd(row.swing_usd)} |"
            )
    else:
        parts.append("*Sensitivity analysis not computed.*")
    parts.append("")

    # ── Key Assumptions Summary ───────────────────────────────────────────────
    parts.append("## Key Input Assumptions")
    parts.append("")
    parts.append("| Parameter | Value |")
    parts.append("|-----------|-------|")
    parts.append(f"| Oil Price | ${inputs.price.oil_price_usd_bbl:.2f}/bbl |")
    parts.append(f"| Gas Price | ${inputs.price.gas_price_usd_mmbtu:.2f}/MMBtu |")
    parts.append(f"| NGL Price | {inputs.price.ngl_price_pct_wti:.0f}% of WTI |")
    if inputs.price.apply_differential_usd_bbl != 0:
        parts.append(f"| Basis Differential | ${inputs.price.apply_differential_usd_bbl:+.2f}/bbl |")
    parts.append(f"| Initial Rate | {inputs.production.initial_rate_boepd:,.0f} boepd |")
    parts.append(f"| Oil Fraction | {inputs.production.oil_fraction*100:.0f}% |")
    parts.append(f"| Decline Type | {inputs.production.decline_type.value} |")
    parts.append(f"| Annual Decline Rate | {inputs.production.decline_rate_annual_pct:.1f}%/yr |")
    parts.append(f"| Uptime | {inputs.production.uptime_pct:.0f}% |")
    parts.append(f"| Economic Limit | {inputs.production.economic_limit_bopd:.0f} bopd |")
    parts.append(f"| Acquisition Cost | {_fmt_usd(inputs.capex.acquisition_cost_usd)} |")
    parts.append(f"| ARO (P50) | {_fmt_usd(inputs.capex.abandonment_cost_p50_usd)} |")
    if inputs.capex.abandonment_cost_p70_usd:
        parts.append(f"| ARO (P70) | {_fmt_usd(inputs.capex.abandonment_cost_p70_usd)} |")
    parts.append(f"| Discount Rate | {inputs.discount_rate_pct:.1f}% |")
    parts.append(f"| Evaluation Period | {inputs.evaluation_years} years |")
    parts.append("")

    # ── Appendix: Calculation Workings ────────────────────────────────────────
    parts.append("## Appendix: Calculation Workings")
    parts.append("*Full inputs, formula, and step-by-step workings for each metric.*")
    parts.append("")
    for metric_name, result in sorted(all_metrics.items()):
        if result.error:
            parts.append(f"### {metric_name}")
            parts.append(f"⚠️ **Error:** {result.error}")
            parts.append("")
            continue
        if result.metric_result is None:
            continue
        parts.append(f"### {metric_name}")
        parts.append(f"**Result:** {result.metric_result:,.4g} {result.unit}")
        if result.formula:
            parts.append(f"**Formula:** `{result.formula}`")
        if result.workings:
            parts.append("**Workings:**")
            for w in result.workings:
                parts.append(f"- {w}")
        if result.inputs_used:
            inputs_str = " | ".join(f"{k}: {v}" for k, v in result.inputs_used.items() if v is not None)
            parts.append(f"**Inputs:** {inputs_str}")
        if result.caveats:
            parts.append("**Caveats:**")
            for c in result.caveats:
                parts.append(f"- {c}")
        parts.append("")

    parts.append("---")
    parts.append("*Report generated by Aigis Analytics Agent 04 — Upstream Finance Calculator v1.0*")

    return "\n".join(parts)


def _append_metrics_table(
    parts: list[str],
    all_metrics: dict[str, CalcResult],
    keys: list[str],
) -> None:
    found_any = False
    for key in keys:
        result = all_metrics.get(key)
        if result is None:
            continue
        if not found_any:
            parts.append("| Metric | Value | Unit | Confidence |")
            parts.append("|--------|-------|------|------------|")
            found_any = True
        val = f"{result.metric_result:,.2f}" if result.metric_result is not None else "N/A"
        if result.error:
            val = f"Error: {result.error}"
        parts.append(f"| {result.metric_name} | {val} | {result.unit} | {result.confidence.value} |")
    if not found_any:
        parts.append("*No metrics computed for this section.*")


def write_json_result(result: AgentResult, output_dir: Path, deal_id: str) -> Path:
    """Write the full AgentResult to JSON."""
    run_dir = Path(output_dir) / deal_id / OUTPUT_SUBFOLDER
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "04_financial_analysis.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2, default=str)
    return json_path
