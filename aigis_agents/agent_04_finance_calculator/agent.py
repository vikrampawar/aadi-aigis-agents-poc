"""
Agent 04 — Upstream Finance Calculator: Main Orchestrator.

Architecture-agnostic: callable from CLI, FastAPI, LangGraph, notebook, or other agents.

Usage (Python API):
    from aigis_agents.agent_04_finance_calculator.agent import finance_calculator_agent
    result = finance_calculator_agent("./inputs/corsair.json", output_dir="./outputs")
    print(result.summary.npv_10_usd)

Usage (single metric — called by other agents):
    from aigis_agents.agent_04_finance_calculator.calculator import calculate_lifting_cost
    loe = calculate_lifting_cost(loe_annual_usd=9_000_000, production_boe=500_000)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aigis_agents.agent_04_finance_calculator.calculator import (
    METRIC_REGISTRY,
    build_cash_flow_schedule,
    calculate_borrowing_base,
    calculate_cash_breakeven,
    calculate_decline_rate,
    calculate_dscr,
    calculate_eur,
    calculate_ev_1p,
    calculate_ev_2p,
    calculate_ev_ebitda,
    calculate_ev_production,
    calculate_full_cycle_breakeven,
    calculate_fnd_cost,
    calculate_gor,
    calculate_irr,
    calculate_lifting_cost,
    calculate_llcr,
    calculate_moic,
    calculate_net_debt_ebitda,
    calculate_netback,
    calculate_npv,
    calculate_opex_per_boe,
    calculate_payback,
    calculate_pv10,
    calculate_recycle_ratio,
    calculate_reserve_replacement,
    calculate_water_cut,
    calculate_wi_net_production,
)
from aigis_agents.agent_04_finance_calculator.deal_registry import register_run
from aigis_agents.agent_04_finance_calculator.fiscal_engine import (
    calculate_government_take,
    calculate_net_revenue_interest,
    calculate_royalty_payment,
    calculate_severance_tax,
)
from aigis_agents.agent_04_finance_calculator.models import (
    AgentResult,
    CalcResult,
    Confidence,
    FinancialAnalysisSummary,
    FinancialInputs,
)
from aigis_agents.agent_04_finance_calculator.primer import get_full_context
from aigis_agents.agent_04_finance_calculator.report_generator import (
    generate_financial_report,
    write_json_result,
)
from aigis_agents.agent_04_finance_calculator.sensitivity import run_sensitivity
from aigis_agents.agent_04_finance_calculator.validator import validate_metrics

log = logging.getLogger(__name__)


def finance_calculator_agent(
    inputs: FinancialInputs | dict | str | Path,
    output_dir: str | Path = ".",
    model_key: str = "gpt-4o-mini",          # Reserved for future LLM narrative synthesis
    session_keys: dict[str, str] | None = None,
    run_sensitivity_analysis: bool = True,
    sensitivity_variables: list[tuple[str, str]] | None = None,
) -> AgentResult:
    """
    Main entry point for Agent 04 — Upstream Finance Calculator.

    Pipeline:
      Step 1 — Load domain knowledge (primer, knowledge bank, playbooks)
      Step 2 — Parse + validate inputs (JSON path / dict / model)
      Step 3 — Build cash flow schedule
      Step 4 — Compute all financial metrics
      Step 5 — Sensitivity analysis (tornado chart data)
      Step 6 — Validate + flag against benchmarks
      Step 7 — Register run + write outputs (markdown + JSON)

    Args:
        inputs: FinancialInputs model, dict, or path to JSON file
        output_dir: Root output directory (deal subfolder created automatically)
        model_key: LLM model key (reserved for future use; no LLM cost in Sprint 1)
        session_keys: Optional API keys for LLM (not used in Sprint 1)
        run_sensitivity_analysis: Whether to run tornado sensitivity (default True)
        sensitivity_variables: Override default sensitivity variables

    Returns:
        AgentResult with all computed metrics, cash flows, sensitivity, flags, and output paths
    """
    output_dir = Path(output_dir)
    run_timestamp = datetime.now(timezone.utc).isoformat()

    # ── Step 1: Load domain knowledge ─────────────────────────────────────────
    log.info("Step 1: Loading domain knowledge")
    try:
        _domain_context = get_full_context()
        log.debug("Domain knowledge loaded (%d chars)", len(_domain_context))
    except Exception as e:
        log.warning("Could not load domain knowledge: %s", e)

    # ── Step 2: Parse + validate inputs ───────────────────────────────────────
    log.info("Step 2: Parsing and validating inputs")
    try:
        parsed_inputs = _parse_inputs(inputs)
    except Exception as e:
        return AgentResult(
            status="error",
            deal_id=str(inputs) if isinstance(inputs, (str, Path)) else "unknown",
            deal_name="Unknown",
            run_timestamp=run_timestamp,
            error_message=f"Input parsing failed: {e}",
        )

    log.info(
        "Inputs valid: %s | %s | %s | %.0f boepd | $%.0f/bbl | %.0f%% decline",
        parsed_inputs.deal_name,
        parsed_inputs.deal_type.value,
        parsed_inputs.jurisdiction.value,
        parsed_inputs.production.initial_rate_boepd,
        parsed_inputs.price.oil_price_usd_bbl,
        parsed_inputs.production.decline_rate_annual_pct,
    )

    # ── Step 3: Build cash flow schedule ──────────────────────────────────────
    log.info("Step 3: Building %d-year cash flow schedule", parsed_inputs.evaluation_years)
    try:
        cash_flows = build_cash_flow_schedule(parsed_inputs)
        log.info("Cash flow schedule: %d active years", len(cash_flows))
    except Exception as e:
        return AgentResult(
            status="error",
            deal_id=parsed_inputs.deal_id,
            deal_name=parsed_inputs.deal_name,
            run_timestamp=run_timestamp,
            error_message=f"Cash flow build failed: {e}",
        )

    # ── Step 4: Compute all metrics ────────────────────────────────────────────
    log.info("Step 4: Computing financial metrics")
    all_metrics: dict[str, CalcResult] = {}

    try:
        acq_cost = parsed_inputs.capex.acquisition_cost_usd

        # Valuation — asset-level NPV (intrinsic value; acquisition cost excluded)
        npv_result = calculate_npv(cash_flows, parsed_inputs.discount_rate_pct)
        pv10_result = calculate_pv10(cash_flows)
        # Investment return metrics (include acquisition cost as Year 0 outflow)
        irr_result = calculate_irr(cash_flows, acq_cost)
        payback_result = calculate_payback(cash_flows, acq_cost)
        moic_result = calculate_moic(cash_flows, acq_cost) if acq_cost > 0 else None

        all_metrics[npv_result.metric_name] = npv_result
        all_metrics[pv10_result.metric_name] = pv10_result
        all_metrics[irr_result.metric_name] = irr_result
        all_metrics[payback_result.metric_name] = payback_result
        if moic_result:
            all_metrics[moic_result.metric_name] = moic_result

        # Value creation = Asset PV10 − Acquisition Cost (investment attractiveness)
        if acq_cost > 0 and pv10_result.metric_result is not None:
            vc = pv10_result.metric_result - acq_cost
            all_metrics["Value Creation (PV10 − Acquisition Cost)"] = CalcResult(
                metric_name="Value Creation (PV10 − Acquisition Cost)",
                metric_result=round(vc, 0),
                unit="USD",
                inputs_used={
                    "asset_pv10_usd": round(pv10_result.metric_result, 0),
                    "acquisition_cost_usd": acq_cost,
                },
                formula="Value Creation = Asset PV10 − Acquisition Cost",
                workings=[
                    f"Asset PV10 (intrinsic value): ${pv10_result.metric_result/1e6:.1f}M",
                    f"Acquisition cost (bid price): ${acq_cost/1e6:.1f}M",
                    f"Value creation: ${vc/1e6:.1f}M {'✅ positive — deal creates value' if vc > 0 else '❌ negative — overpaying vs PV10'}",
                ],
                caveats=["Positive = paying less than intrinsic PV10 value; negative = paying premium to PV10"],
                confidence=Confidence.HIGH,
            )

        # EV multiples (only if reserves provided)
        ev_usd = acq_cost  # Use acquisition cost as EV proxy
        if parsed_inputs.reserves:
            res = parsed_inputs.reserves
            if res.p2_mmboe:
                r = calculate_ev_2p(ev_usd, res.p2_mmboe)
                all_metrics[r.metric_name] = r
            if res.p1_mmboe:
                r = calculate_ev_1p(ev_usd, res.p1_mmboe)
                all_metrics[r.metric_name] = r

        # EV/production
        r = calculate_ev_production(ev_usd, parsed_inputs.production.initial_rate_boepd)
        all_metrics[r.metric_name] = r

        # Year-1 EBITDA for EV/EBITDA
        if cash_flows:
            yr1 = cash_flows[0]
            r = calculate_ev_ebitda(ev_usd, yr1.ebitda_usd)
            all_metrics[r.metric_name] = r

        # Production metrics
        yr1_boe = cash_flows[0].production_boe if cash_flows else 0.0
        yr1_loe = cash_flows[0].loe_usd if cash_flows else 0.0
        yr1_opex = cash_flows[0].total_opex_usd if cash_flows else 0.0

        loe_result = calculate_lifting_cost(yr1_loe, yr1_boe)
        all_metrics[loe_result.metric_name] = loe_result

        opex_result = calculate_opex_per_boe(yr1_opex, yr1_boe)
        all_metrics[opex_result.metric_name] = opex_result

        # Netback and breakevens
        netback_result = calculate_netback(
            oil_price_usd_bbl=parsed_inputs.price.oil_price_usd_bbl,
            royalty_rate_pct=parsed_inputs.fiscal.royalty_rate_pct,
            severance_tax_pct=parsed_inputs.fiscal.severance_tax_pct,
            loe_per_boe=parsed_inputs.costs.loe_per_boe,
            transport_per_boe=parsed_inputs.costs.transport_per_boe,
            differential_usd_bbl=parsed_inputs.price.apply_differential_usd_bbl,
        )
        all_metrics[netback_result.metric_name] = netback_result

        breakeven_result = calculate_cash_breakeven(
            royalty_rate_pct=parsed_inputs.fiscal.royalty_rate_pct,
            severance_tax_pct=parsed_inputs.fiscal.severance_tax_pct,
            loe_per_boe=parsed_inputs.costs.loe_per_boe,
            transport_per_boe=parsed_inputs.costs.transport_per_boe,
            differential_usd_bbl=parsed_inputs.price.apply_differential_usd_bbl,
        )
        all_metrics[breakeven_result.metric_name] = breakeven_result

        if acq_cost > 0:
            fcbe_result = calculate_full_cycle_breakeven(cash_flows, acq_cost, parsed_inputs)
            all_metrics[fcbe_result.metric_name] = fcbe_result

        # EUR
        prod = parsed_inputs.production
        eur_result = calculate_eur(
            q_i=prod.initial_rate_boepd * (prod.uptime_pct / 100.0),
            D_nominal=prod.decline_rate_annual_pct / 100.0,
            b=prod.b_factor,
            q_econ=prod.economic_limit_bopd,
            decline_type=prod.decline_type,
        )
        all_metrics[eur_result.metric_name] = eur_result

        # F&D and recycle ratio (only if reserve additions provided)
        dev_capex_total = sum(parsed_inputs.capex.development_capex_by_year_usd)
        if dev_capex_total > 0 and parsed_inputs.reserves and parsed_inputs.reserves.p2_mmboe:
            fnd = calculate_fnd_cost(dev_capex_total, parsed_inputs.reserves.p2_mmboe)
            all_metrics[fnd.metric_name] = fnd
            if netback_result.metric_result is not None and fnd.metric_result is not None:
                rr = calculate_recycle_ratio(netback_result.metric_result, fnd.metric_result)
                all_metrics[rr.metric_name] = rr

        # Fiscal metrics
        if cash_flows:
            total_gross_rev = sum(cf.gross_revenue_usd for cf in cash_flows)
            total_royalty = sum(cf.royalty_usd for cf in cash_flows)
            total_tax = sum(cf.income_tax_usd for cf in cash_flows)
            total_opex_all = sum(cf.total_opex_usd for cf in cash_flows)

            r = calculate_royalty_payment(total_gross_rev, parsed_inputs.fiscal.royalty_rate_pct)
            all_metrics[r.metric_name] = r

            r = calculate_severance_tax(total_gross_rev, parsed_inputs.fiscal.severance_tax_pct)
            all_metrics[r.metric_name] = r

            r = calculate_net_revenue_interest(
                parsed_inputs.fiscal.wi_pct,
                parsed_inputs.fiscal.royalty_rate_pct,
                parsed_inputs.fiscal.orri_pct,
            )
            all_metrics[r.metric_name] = r

            gov_take = calculate_government_take(
                total_gross_rev, total_royalty, 0.0, total_tax
            )
            all_metrics[gov_take.metric_name] = gov_take

        # RBL / leverage — borrowing base based directly on asset PV10
        pv10_val = pv10_result.metric_result
        if pv10_val is not None and pv10_val > 0:
            r = calculate_borrowing_base(pv10_val)
            all_metrics[r.metric_name] = r

        # RBL DSCR/LLCR if RBL inputs provided
        if parsed_inputs.rbl:
            rbl = parsed_inputs.rbl
            if rbl.debt_service_annual_usd and cash_flows:
                yr1_ncf = cash_flows[0].net_cash_flow_usd
                r = calculate_dscr(yr1_ncf, rbl.debt_service_annual_usd)
                all_metrics[r.metric_name] = r

    except Exception as e:
        log.error("Metric computation error: %s", e, exc_info=True)
        return AgentResult(
            status="partial",
            deal_id=parsed_inputs.deal_id,
            deal_name=parsed_inputs.deal_name,
            run_timestamp=run_timestamp,
            cash_flows=cash_flows,
            error_message=f"Metric computation partially failed: {e}",
        )

    # ── Build Summary ──────────────────────────────────────────────────────────
    summary = _build_summary(all_metrics)

    # ── Step 5: Sensitivity analysis ──────────────────────────────────────────
    sensitivity_rows = []
    if run_sensitivity_analysis:
        log.info("Step 5: Running sensitivity analysis")
        try:
            # Base NPV = asset-level PV10 (no acquisition cost deducted)
            base_npv = pv10_result.metric_result or 0.0
            sensitivity_rows = run_sensitivity(
                inputs=parsed_inputs,
                base_npv_usd=base_npv,
                variables=sensitivity_variables,
            )
            log.info("Sensitivity: %d variables computed", len(sensitivity_rows))
        except Exception as e:
            log.warning("Sensitivity analysis failed: %s", e)

    # ── Step 6: Validate + flag ────────────────────────────────────────────────
    log.info("Step 6: Validating metrics against benchmarks")
    flags = validate_metrics(summary, parsed_inputs.jurisdiction, parsed_inputs.deal_type)
    summary.flag_count_critical = sum(1 for f in flags if "CRITICAL" in f.severity)
    summary.flag_count_warning = sum(1 for f in flags if "WARNING" in f.severity)
    log.info("Flags: %d critical, %d warnings", summary.flag_count_critical, summary.flag_count_warning)

    # ── Step 7: Register + write outputs ──────────────────────────────────────
    log.info("Step 7: Registering run and writing outputs")

    # Register deal
    try:
        register_run(parsed_inputs, summary, output_dir, cost_usd=0.0)
        log.info("Deal registry updated: %s", output_dir / "deals_registry_04.json")
    except Exception as e:
        log.warning("Registry update failed: %s", e)

    # Write outputs
    outputs: dict[str, str] = {}
    try:
        md_path, json_path = generate_financial_report(
            inputs=parsed_inputs,
            all_metrics=all_metrics,
            cash_flows=cash_flows,
            sensitivity=sensitivity_rows,
            flags=flags,
            summary=summary,
            output_dir=output_dir,
        )
        outputs["financial_analysis_md"] = str(md_path)
        log.info("Report written: %s", md_path)
    except Exception as e:
        log.error("Report generation failed: %s", e, exc_info=True)

    # Build result
    result = AgentResult(
        status="success",
        deal_id=parsed_inputs.deal_id,
        deal_name=parsed_inputs.deal_name,
        outputs=outputs,
        summary=summary,
        all_metrics=all_metrics,
        cash_flows=cash_flows,
        sensitivity=sensitivity_rows,
        flags=flags,
        run_timestamp=run_timestamp,
        cost_usd=0.0,
    )

    # Write JSON result
    try:
        json_path = write_json_result(result, output_dir, parsed_inputs.deal_id)
        outputs["financial_analysis_json"] = str(json_path)
        result.outputs = outputs
    except Exception as e:
        log.warning("JSON write failed: %s", e)

    log.info(
        "Agent 04 complete: NPV10=%s | IRR=%s | LOE=%s | Flags: %d critical",
        f"${(summary.npv_10_usd or 0)/1e6:.1f}M",
        f"{summary.irr_pct:.1f}%" if summary.irr_pct else "N/A",
        f"${summary.loe_per_boe:.1f}/boe" if summary.loe_per_boe else "N/A",
        summary.flag_count_critical,
    )
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_inputs(inputs: FinancialInputs | dict | str | Path) -> FinancialInputs:
    """Parse inputs from any supported format into FinancialInputs."""
    if isinstance(inputs, FinancialInputs):
        return inputs
    if isinstance(inputs, dict):
        return FinancialInputs.model_validate(inputs)
    # String or Path → read JSON file
    path = Path(inputs)
    if not path.exists():
        raise FileNotFoundError(f"Inputs file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return FinancialInputs.model_validate(data)


def _build_summary(all_metrics: dict[str, CalcResult]) -> FinancialAnalysisSummary:
    """Extract headline metrics from computed CalcResult dict."""
    def _get(name: str) -> float | None:
        result = all_metrics.get(name)
        if result and result.metric_result is not None:
            return result.metric_result
        return None

    vc_result = all_metrics.get("Value Creation (PV10 − Acquisition Cost)")
    vc_inputs = vc_result.inputs_used if vc_result else {}

    return FinancialAnalysisSummary(
        npv_10_usd=_get("PV10") or _get("NPV @ 10%"),
        acquisition_cost_usd=vc_inputs.get("acquisition_cost_usd"),
        value_creation_usd=_get("Value Creation (PV10 − Acquisition Cost)"),
        irr_pct=_get("IRR"),
        payback_years=_get("Payback Period"),
        moic=_get("MOIC"),
        loe_per_boe=_get("Lifting Cost (LOE/boe)"),
        netback_usd_bbl=_get("Netback"),
        cash_breakeven_usd_bbl=_get("Cash Breakeven Oil Price"),
        full_cycle_breakeven_usd_bbl=_get("Full-Cycle Breakeven Oil Price"),
        ev_2p_usd_boe=_get("EV/2P"),
        ev_1p_usd_boe=_get("EV/1P"),
        ev_production_usd_boepd=_get("EV/Production"),
        government_take_pct=_get("Government Take"),
        borrowing_base_usd=_get("RBL Borrowing Base Estimate"),
        eur_mmboe=(_get("EUR") or 0.0) / 1_000_000 if _get("EUR") else None,
    )


def compute_single_metric(
    metric_key: str,
    inputs: FinancialInputs | dict | str | Path,
    output_dir: str | Path = ".",
) -> CalcResult:
    """
    Compute a single named metric without producing a full report.
    Used by other agents to get one specific result quickly.

    Args:
        metric_key: Key from METRIC_REGISTRY (e.g. "npv_10", "lifting_cost", "irr")
        inputs: FinancialInputs or JSON path
        output_dir: Not used in single-metric mode (no file I/O)

    Returns:
        CalcResult for the requested metric
    """
    parsed = _parse_inputs(inputs)

    if metric_key not in METRIC_REGISTRY:
        return CalcResult(
            metric_name=metric_key,
            metric_result=None,
            unit="",
            formula="",
            workings=[],
            caveats=[f"Unknown metric key '{metric_key}'. Use --list-metrics to see available metrics."],
            confidence=Confidence.LOW,
            error=f"Unknown metric: {metric_key}",
        )

    # Build cash flows (needed for most metrics)
    cash_flows = build_cash_flow_schedule(parsed)
    acq_cost = parsed.capex.acquisition_cost_usd

    # Route to the right function
    if metric_key in ("npv", "npv_10", "pv10"):
        r = calculate_pv10(cash_flows)  # asset-level, no acquisition cost
    elif metric_key == "irr":
        r = calculate_irr(cash_flows, acq_cost)
    elif metric_key == "payback":
        r = calculate_payback(cash_flows, acq_cost)
    elif metric_key == "lifting_cost":
        yr1_boe = cash_flows[0].production_boe if cash_flows else 1.0
        yr1_loe = cash_flows[0].loe_usd if cash_flows else 0.0
        r = calculate_lifting_cost(yr1_loe, yr1_boe)
    elif metric_key == "netback":
        r = calculate_netback(
            parsed.price.oil_price_usd_bbl, parsed.fiscal.royalty_rate_pct,
            parsed.fiscal.severance_tax_pct, parsed.costs.loe_per_boe,
            parsed.costs.transport_per_boe, parsed.price.apply_differential_usd_bbl,
        )
    elif metric_key == "cash_breakeven":
        r = calculate_cash_breakeven(
            parsed.fiscal.royalty_rate_pct, parsed.fiscal.severance_tax_pct,
            parsed.costs.loe_per_boe, parsed.costs.transport_per_boe,
            parsed.price.apply_differential_usd_bbl,
        )
    elif metric_key == "eur":
        prod = parsed.production
        r = calculate_eur(
            prod.initial_rate_boepd * (prod.uptime_pct / 100.0),
            prod.decline_rate_annual_pct / 100.0,
            prod.b_factor, prod.economic_limit_bopd, prod.decline_type,
        )
    elif metric_key == "ev_2p" and parsed.reserves and parsed.reserves.p2_mmboe:
        r = calculate_ev_2p(acq_cost, parsed.reserves.p2_mmboe)
    elif metric_key == "ev_production":
        r = calculate_ev_production(acq_cost, parsed.production.initial_rate_boepd)
    elif metric_key == "borrowing_base":
        pv10 = calculate_pv10(cash_flows)  # asset-level PV10
        r = calculate_borrowing_base(pv10.metric_result or 0.0)
    else:
        # Fallback: run full agent and extract the metric
        full_result = finance_calculator_agent(parsed, output_dir=output_dir,
                                                run_sensitivity_analysis=False)
        # Find best match in all_metrics
        for name, cr in full_result.all_metrics.items():
            if metric_key.lower().replace("_", " ") in name.lower():
                return cr
        return CalcResult(
            metric_name=metric_key, metric_result=None, unit="",
            formula="", workings=[], caveats=[f"Metric '{metric_key}' not found in computed results"],
            confidence=Confidence.LOW, error="Metric not found",
        )

    return r
