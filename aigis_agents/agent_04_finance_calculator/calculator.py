"""
Pure financial calculation functions for Agent 04 — Upstream Finance Calculator.

All functions are:
  - Pure: no LLM calls, no file I/O, no side effects
  - Transparent: every CalcResult includes inputs_used, formula, workings
  - Importable directly by other agents (zero overhead)

Usage from another agent:
    from aigis_agents.agent_04_finance_calculator.calculator import (
        calculate_lifting_cost, calculate_npv, build_cash_flow_schedule
    )
"""

from __future__ import annotations

import math
from typing import Any

from aigis_agents.agent_04_finance_calculator.models import (
    CalcResult,
    Confidence,
    DeclineType,
    FinancialInputs,
    YearlyCashFlow,
)


# ── Unit Conversion Table ─────────────────────────────────────────────────────

CONVERSION_TABLE: dict[tuple[str, str], float] = {
    # Volume
    ("bbl", "m3"): 0.158987,
    ("m3", "bbl"): 6.28981,
    ("bbl", "litres"): 158.987,
    ("litres", "bbl"): 0.0062898,
    ("mcf", "m3"): 28.3168,
    ("m3", "mcf"): 0.035315,
    ("mmcf", "bcf"): 0.001,
    ("bcf", "mmcf"): 1000.0,
    # Energy / BOE conversions
    ("mcf", "boe"): 0.17810,       # 1 mcf = 1/5.615 boe (using 5.615 Mcf/boe)
    ("boe", "mcf"): 5.615,
    ("mmbtu", "boe"): 0.17241,    # rough: 1 mmbtu ≈ 0.17 boe
    ("boe", "mmbtu"): 5.8,
    # Mass
    ("tonnes", "bbl"): 7.33,       # rough, API ~35
    ("bbl", "tonnes"): 0.1364,
    # Area
    ("acres", "hectares"): 0.404686,
    ("hectares", "acres"): 2.47105,
    # Currency (indicative — use live rates in production)
    ("GBP", "USD"): 1.27,
    ("USD", "GBP"): 0.787,
    ("NOK", "USD"): 0.094,
    ("USD", "NOK"): 10.64,
    ("AUD", "USD"): 0.65,
    ("USD", "AUD"): 1.54,
}


def convert_units(value: float, from_unit: str, to_unit: str) -> tuple[float, str]:
    """
    Convert a value between units.

    Returns (converted_value, conversion_note).
    Returns original value with a warning note if conversion not found.
    """
    if from_unit == to_unit:
        return value, ""
    key = (from_unit, to_unit)
    if key in CONVERSION_TABLE:
        result = value * CONVERSION_TABLE[key]
        return result, f"{value} {from_unit} → {result:.4g} {to_unit}"
    return value, f"Warning: no conversion factor found for {from_unit} → {to_unit}"


# ── Decline Curves ────────────────────────────────────────────────────────────

def decline_exponential(q_i: float, D_nominal: float, t: float) -> float:
    """
    Exponential decline: q(t) = q_i × e^(-D×t)

    Args:
        q_i: Initial rate (any consistent unit)
        D_nominal: Nominal annual decline rate (fraction, e.g. 0.15 for 15%)
        t: Time (years)
    """
    return q_i * math.exp(-D_nominal * t)


def decline_hyperbolic(q_i: float, D_i: float, b: float, t: float) -> float:
    """
    Hyperbolic decline: q(t) = q_i × (1 + b×D_i×t)^(-1/b)

    Args:
        q_i: Initial rate
        D_i: Initial nominal decline rate (fraction)
        b: Arps b-factor (0 < b ≤ 2; 1 = harmonic, 0 → exponential)
        t: Time (years)
    """
    if b <= 0 or b > 2:
        return decline_exponential(q_i, D_i, t)
    return q_i * (1.0 + b * D_i * t) ** (-1.0 / b)


def decline_harmonic(q_i: float, D_i: float, t: float) -> float:
    """
    Harmonic decline (special case of hyperbolic with b=1):
    q(t) = q_i / (1 + D_i×t)
    """
    return q_i / (1.0 + D_i * t)


def _rate_at_year(inputs: FinancialInputs, t: float) -> float:
    """Rate at fractional year t, applying uptime and decline."""
    D = inputs.production.decline_rate_annual_pct / 100.0
    q_i = inputs.production.initial_rate_boepd * (inputs.production.uptime_pct / 100.0)
    dt = inputs.production.decline_type
    b = inputs.production.b_factor

    if dt == DeclineType.exponential:
        return decline_exponential(q_i, D, t)
    elif dt == DeclineType.hyperbolic:
        return decline_hyperbolic(q_i, D, b, t)
    else:
        return decline_harmonic(q_i, D, t)


# ── Cash Flow Schedule (Core Engine) ─────────────────────────────────────────

def build_cash_flow_schedule(inputs: FinancialInputs) -> list[YearlyCashFlow]:
    """
    Build annual cash flow schedule for the evaluation period.

    Steps:
    1. Production profile via decline curve (with uptime)
    2. Revenue by product (oil, gas, NGL) using price assumptions
    3. Royalty deduction
    4. OPEX (LOE, G&A, workovers, transport)
    5. CAPEX (acquisition in year 0 only as negative CF; development + ARO by year)
    6. Income tax on (net_revenue - opex - capex)
    7. Discounted CF at discount_rate_pct

    Note: Acquisition cost is NOT included in yearly CF rows (it forms the initial outflow
    that makes NPV = -acquisition + PV of future flows). Development capex and ARO are included.
    """
    D = inputs.production.decline_rate_annual_pct / 100.0
    r = inputs.discount_rate_pct / 100.0
    p = inputs.price
    prod = inputs.production
    fiscal = inputs.fiscal
    costs = inputs.costs
    capex_sched = inputs.capex

    q_i_uptime = prod.initial_rate_boepd * (prod.uptime_pct / 100.0)
    econ_limit = prod.economic_limit_bopd

    # Oil effective price after differential
    oil_price = p.oil_price_usd_bbl + p.apply_differential_usd_bbl
    gas_price = p.gas_price_usd_mmbtu
    ngl_price = oil_price * (p.ngl_price_pct_wti / 100.0)

    # NRI (Net Revenue Interest) = WI × (1 - royalty_pct/100 - ORRI/100)
    nri = (fiscal.wi_pct / 100.0) * (1.0 - fiscal.royalty_rate_pct / 100.0 - fiscal.orri_pct / 100.0)
    royalty_rate = fiscal.royalty_rate_pct / 100.0

    rows: list[YearlyCashFlow] = []
    cumulative_revenue = 0.0
    cumulative_opex = 0.0

    for yr in range(1, inputs.evaluation_years + 1):
        # Mid-year production rate (average of start and end of year)
        t_start = yr - 1
        t_end = yr
        if prod.decline_type == DeclineType.exponential:
            q_start = decline_exponential(q_i_uptime, D, t_start)
            q_end = decline_exponential(q_i_uptime, D, t_end)
        elif prod.decline_type == DeclineType.hyperbolic:
            q_start = decline_hyperbolic(q_i_uptime, D, prod.b_factor, t_start)
            q_end = decline_hyperbolic(q_i_uptime, D, prod.b_factor, t_end)
        else:
            q_start = decline_harmonic(q_i_uptime, D, t_start)
            q_end = decline_harmonic(q_i_uptime, D, t_end)

        q_avg = (q_start + q_end) / 2.0

        # Check economic limit (oil rate only)
        q_oil_avg = q_avg * prod.oil_fraction
        if q_oil_avg < econ_limit and yr > 1:
            break  # Below economic limit

        # Annual production volumes
        days_in_year = 365.25
        boe_total = q_avg * days_in_year
        boe_oil = boe_total * prod.oil_fraction
        boe_gas = boe_total * prod.gas_fraction    # boe equivalent
        boe_ngl = boe_total * prod.ngl_fraction

        # Convert gas boe to mcf for revenue (1 boe = 5.615 mcf)
        mcf_gas = boe_gas * 5.615

        # Gross revenue
        rev_oil = boe_oil * oil_price
        rev_gas = mcf_gas * gas_price / 1000.0    # MMBtu ≈ Mcf; /1000 to convert gas price base
        # More precisely: gas revenue = volume_mmcf × price_per_mmbtu × 1000
        # boe_gas already in boe; mcf_gas = boe_gas * 5.615; mmcf = mcf_gas/1000
        rev_gas = (mcf_gas / 1000.0) * gas_price * 1000.0   # = mcf_gas * gas_price ($/mcf ≈ $/mmbtu)
        rev_ngl = boe_ngl * ngl_price
        gross_revenue = rev_oil + rev_gas + rev_ngl

        # Royalty
        royalty = gross_revenue * royalty_rate

        # Net revenue
        net_revenue = gross_revenue * (1.0 - royalty_rate)

        # OPEX
        loe = boe_total * costs.loe_per_boe
        g_and_a = boe_total * costs.g_and_a_per_boe
        workovers = costs.workovers_annual_usd
        transport = boe_total * costs.transport_per_boe
        total_opex = loe + g_and_a + workovers + transport

        # EBITDA
        ebitda = net_revenue - total_opex

        # Development CAPEX (year 1 = index 0)
        dev_capex_list = capex_sched.development_capex_by_year_usd
        dev_capex = dev_capex_list[yr - 1] if (yr - 1) < len(dev_capex_list) else 0.0

        # ARO: scheduled year or at economic limit (last year)
        aro_cost = 0.0
        if capex_sched.abandonment_year is not None and yr == capex_sched.abandonment_year:
            aro_cost = capex_sched.abandonment_cost_p50_usd
        capex_total = dev_capex + aro_cost

        # Taxable income = net_revenue - opex - capex (simplified; capex expensed)
        taxable_income = max(0.0, net_revenue - total_opex - capex_total)
        income_tax = taxable_income * (fiscal.income_tax_rate_pct / 100.0)

        # Net cash flow
        net_cf = net_revenue - total_opex - capex_total - income_tax

        # Discounted CF (end-of-year convention)
        dcf = net_cf / ((1.0 + r) ** yr)

        cumulative_revenue += gross_revenue
        cumulative_opex += total_opex

        rows.append(YearlyCashFlow(
            year=yr,
            production_boepd=round(q_avg, 2),
            production_boe=round(boe_total, 0),
            gross_revenue_usd=round(gross_revenue, 0),
            royalty_usd=round(royalty, 0),
            net_revenue_usd=round(net_revenue, 0),
            loe_usd=round(loe, 0),
            workovers_usd=round(workovers, 0),
            transport_usd=round(transport, 0),
            g_and_a_usd=round(g_and_a, 0),
            total_opex_usd=round(total_opex, 0),
            ebitda_usd=round(ebitda, 0),
            capex_usd=round(capex_total, 0),
            taxable_income_usd=round(taxable_income, 0),
            income_tax_usd=round(income_tax, 0),
            net_cash_flow_usd=round(net_cf, 0),
            discounted_cash_flow_usd=round(dcf, 0),
        ))

    # Append ARO in final year if not already scheduled
    if capex_sched.abandonment_cost_p50_usd > 0 and capex_sched.abandonment_year is None and rows:
        last_row = rows[-1]
        aro = capex_sched.abandonment_cost_p50_usd
        rows[-1] = YearlyCashFlow(
            **{**last_row.model_dump(),
               "capex_usd": last_row.capex_usd + aro,
               "net_cash_flow_usd": last_row.net_cash_flow_usd - aro,
               "discounted_cash_flow_usd": (last_row.net_cash_flow_usd - aro) / ((1.0 + r) ** last_row.year),
            }
        )

    return rows


# ── Valuation Metrics ─────────────────────────────────────────────────────────

def calculate_npv(
    cash_flows: list[YearlyCashFlow],
    discount_rate_pct: float,
) -> CalcResult:
    """
    Asset-level Net Present Value at a given discount rate.

    NPV = Σ(CF_t / (1+r)^t)

    This is the intrinsic value of the asset's future cash flows.
    Acquisition cost is EXCLUDED — it is compared separately against this value
    to assess whether the bid price is commercially attractive.

    Investment NPV = Asset NPV − Acquisition Cost (computed separately).
    """
    r = discount_rate_pct / 100.0
    pv_sum = sum(cf.net_cash_flow_usd / ((1.0 + r) ** cf.year) for cf in cash_flows)

    return CalcResult(
        metric_name=f"NPV @ {discount_rate_pct:.0f}%",
        metric_result=round(pv_sum, 0),
        unit="USD",
        inputs_used={
            "discount_rate_pct": discount_rate_pct,
            "evaluation_years": len(cash_flows),
        },
        formula="Asset NPV = Σ(CF_t / (1+r)^t)  [acquisition cost excluded — compare separately]",
        workings=[
            f"Asset PV of future cash flows at {discount_rate_pct}%: ${pv_sum:,.0f}",
            "Acquisition cost is NOT deducted — compare separately to assess deal attractiveness",
        ],
        caveats=[
            "Asset-level metric: excludes acquisition cost. To assess return, compare to bid price.",
            "Uses end-of-year discounting convention",
            "Simplified tax treatment: capex expensed in year incurred",
            "Flat real price deck — no inflation or escalation applied",
        ],
        confidence=Confidence.HIGH,
    )


def calculate_pv10(
    cash_flows: list[YearlyCashFlow],
) -> CalcResult:
    """
    PV10 = Asset NPV at exactly 10% discount rate (SEC / SPE standard).

    Represents the intrinsic value of the asset's future cash flows.
    Compare PV10 to acquisition cost to assess deal attractiveness:
      Value Creation = PV10 − Acquisition Cost
    """
    result = calculate_npv(cash_flows, 10.0)
    result.metric_name = "PV10"
    result.workings.insert(0, "PV10 uses 10.0% discount rate per SEC standard")
    return result


def calculate_irr(
    cash_flows: list[YearlyCashFlow],
    acquisition_cost_usd: float = 0.0,
    max_iterations: int = 1000,
    tolerance: float = 1e-6,
) -> CalcResult:
    """
    Internal Rate of Return using Newton-Raphson iteration.
    IRR is the rate r where NPV = 0.
    """
    def npv_at(r: float) -> float:
        total = -acquisition_cost_usd
        for cf in cash_flows:
            total += cf.net_cash_flow_usd / ((1.0 + r) ** cf.year)
        return total

    def npv_derivative(r: float) -> float:
        total = 0.0
        for cf in cash_flows:
            total -= cf.year * cf.net_cash_flow_usd / ((1.0 + r) ** (cf.year + 1))
        return total

    # Check if positive CFs exist after initial outlay
    positive_cfs = [cf.net_cash_flow_usd for cf in cash_flows if cf.net_cash_flow_usd > 0]
    if not positive_cfs:
        return CalcResult(
            metric_name="IRR",
            metric_result=None,
            unit="%",
            inputs_used={"acquisition_cost_usd": acquisition_cost_usd},
            formula="IRR: rate where NPV = 0",
            workings=["No positive cash flows found — IRR undefined"],
            caveats=["IRR cannot be computed without positive cash flows"],
            confidence=Confidence.LOW,
            error="No positive cash flows",
        )

    # Newton-Raphson starting from 20%
    r = 0.20
    for i in range(max_iterations):
        npv_val = npv_at(r)
        deriv = npv_derivative(r)
        if abs(deriv) < 1e-12:
            break
        r_new = r - npv_val / deriv
        if abs(r_new - r) < tolerance:
            r = r_new
            break
        r = r_new
        # Clamp to reasonable range
        r = max(-0.99, min(r, 10.0))

    irr_pct = r * 100.0

    # Verify convergence
    final_npv = npv_at(r)
    converged = abs(final_npv) < max(1.0, abs(acquisition_cost_usd) * 0.001)

    return CalcResult(
        metric_name="IRR",
        metric_result=round(irr_pct, 2) if converged else None,
        unit="%",
        inputs_used={
            "acquisition_cost_usd": acquisition_cost_usd,
            "evaluation_years": len(cash_flows),
        },
        formula="IRR: discount rate r where NPV(r) = 0",
        workings=[
            f"Newton-Raphson converged in <{max_iterations} iterations",
            f"IRR = {irr_pct:.2f}%",
            f"Verification NPV at IRR: ${final_npv:,.0f} (should be ≈ 0)",
        ],
        caveats=[
            "Multiple IRR solutions possible if cash flows change sign more than once",
            "IRR assumes reinvestment at IRR rate — use NPV for absolute value decisions",
        ] + (["Newton-Raphson did not fully converge — treat with caution"] if not converged else []),
        confidence=Confidence.HIGH if converged else Confidence.LOW,
    )


def calculate_payback(
    cash_flows: list[YearlyCashFlow],
    acquisition_cost_usd: float = 0.0,
) -> CalcResult:
    """
    Simple payback period: year when cumulative undiscounted cash flow turns positive.
    """
    cumulative = -acquisition_cost_usd
    payback_year: float | None = None

    for cf in cash_flows:
        prev = cumulative
        cumulative += cf.net_cash_flow_usd
        if prev < 0 and cumulative >= 0 and payback_year is None:
            # Interpolate within the year
            fraction = (-prev) / cf.net_cash_flow_usd if cf.net_cash_flow_usd > 0 else 0
            payback_year = cf.year - 1 + fraction

    return CalcResult(
        metric_name="Payback Period",
        metric_result=round(payback_year, 2) if payback_year is not None else None,
        unit="years",
        inputs_used={
            "acquisition_cost_usd": acquisition_cost_usd,
            "evaluation_years": len(cash_flows),
        },
        formula="Payback = year where cumulative undiscounted CF > 0",
        workings=[
            f"Initial outlay: ${acquisition_cost_usd:,.0f}",
            f"Cumulative CF at end of evaluation: ${cumulative:,.0f}",
            f"Payback: {payback_year:.2f} years" if payback_year else "Not recovered within evaluation period",
        ],
        caveats=["Undiscounted payback; use NPV for time-value-adjusted analysis"],
        confidence=Confidence.HIGH if payback_year is not None else Confidence.LOW,
        error=None if payback_year is not None else "Investment not recovered within evaluation period",
    )


def calculate_moic(
    cash_flows: list[YearlyCashFlow],
    equity_invested_usd: float,
) -> CalcResult:
    """
    Multiple on Invested Capital: MOIC = Total CF / Equity invested.
    """
    total_cf = sum(cf.net_cash_flow_usd for cf in cash_flows)
    moic = total_cf / equity_invested_usd if equity_invested_usd > 0 else None

    return CalcResult(
        metric_name="MOIC",
        metric_result=round(moic, 2) if moic is not None else None,
        unit="×",
        inputs_used={"equity_invested_usd": equity_invested_usd, "total_cf_usd": round(total_cf, 0)},
        formula="MOIC = Total undiscounted CF / Equity invested",
        workings=[
            f"Total undiscounted CF: ${total_cf:,.0f}",
            f"Equity invested: ${equity_invested_usd:,.0f}",
            f"MOIC: {moic:.2f}×" if moic else "Cannot compute",
        ],
        caveats=["Undiscounted; does not account for time value of money"],
        confidence=Confidence.HIGH if moic is not None else Confidence.LOW,
    )


def calculate_ev_2p(ev_usd: float, p2_mmboe: float) -> CalcResult:
    """EV/2P = Enterprise Value / 2P reserves ($/boe)."""
    result = ev_usd / (p2_mmboe * 1_000_000) if p2_mmboe > 0 else None
    return CalcResult(
        metric_name="EV/2P",
        metric_result=round(result, 2) if result else None,
        unit="$/boe",
        inputs_used={"ev_usd": ev_usd, "p2_mmboe": p2_mmboe},
        formula="EV/2P = EV / (2P reserves in boe)",
        workings=[f"EV: ${ev_usd/1e6:.1f}M / 2P: {p2_mmboe:.2f} mmboe = ${result:.2f}/boe" if result else ""],
        caveats=["GoM producing asset typical range: $5–$25/boe (2P)"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_ev_1p(ev_usd: float, p1_mmboe: float) -> CalcResult:
    """EV/1P = Enterprise Value / 1P (Proved) reserves ($/boe)."""
    result = ev_usd / (p1_mmboe * 1_000_000) if p1_mmboe > 0 else None
    return CalcResult(
        metric_name="EV/1P",
        metric_result=round(result, 2) if result else None,
        unit="$/boe",
        inputs_used={"ev_usd": ev_usd, "p1_mmboe": p1_mmboe},
        formula="EV/1P = EV / (1P proved reserves in boe)",
        workings=[f"${ev_usd/1e6:.1f}M / {p1_mmboe:.2f} mmboe = ${result:.2f}/boe" if result else ""],
        caveats=["1P proved reserves only; more conservative than 2P multiple"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_ev_production(ev_usd: float, production_boepd: float) -> CalcResult:
    """EV per boepd of current production."""
    result = ev_usd / production_boepd if production_boepd > 0 else None
    return CalcResult(
        metric_name="EV/Production",
        metric_result=round(result, 0) if result else None,
        unit="$/boepd",
        inputs_used={"ev_usd": ev_usd, "production_boepd": production_boepd},
        formula="EV/boepd = EV / current production rate",
        workings=[f"${ev_usd/1e6:.1f}M / {production_boepd:.0f} boepd = ${result:,.0f}/boepd" if result else ""],
        caveats=["GoM mature producing asset typical range: $15,000–$50,000/boepd"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_ev_ebitda(ev_usd: float, ebitda_usd: float) -> CalcResult:
    """EV/EBITDA multiple."""
    result = ev_usd / ebitda_usd if ebitda_usd > 0 else None
    return CalcResult(
        metric_name="EV/EBITDA",
        metric_result=round(result, 2) if result else None,
        unit="×",
        inputs_used={"ev_usd": ev_usd, "ebitda_usd": ebitda_usd},
        formula="EV/EBITDA = Enterprise Value / EBITDA",
        workings=[f"${ev_usd/1e6:.1f}M / ${ebitda_usd/1e6:.1f}M = {result:.2f}×" if result else ""],
        caveats=["E&P sector typical range: 3–6×; higher for high-growth assets"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


# ── Cost and Efficiency Metrics ───────────────────────────────────────────────

def calculate_lifting_cost(loe_annual_usd: float, production_boe: float) -> CalcResult:
    """
    Lifting cost (LOE per boe) = Annual LOE / Annual production (boe).
    """
    result = loe_annual_usd / production_boe if production_boe > 0 else None
    return CalcResult(
        metric_name="Lifting Cost (LOE/boe)",
        metric_result=round(result, 2) if result else None,
        unit="USD/boe",
        inputs_used={"loe_annual_usd": loe_annual_usd, "production_boe": production_boe},
        formula="LOE/boe = Annual LOE ($) / Annual production (boe)",
        workings=[f"${loe_annual_usd:,.0f} / {production_boe:,.0f} boe = ${result:.2f}/boe" if result else ""],
        caveats=["GoM shallow water benchmark: $8–$35/boe; deepwater: $25–$80/boe"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_netback(
    oil_price_usd_bbl: float,
    royalty_rate_pct: float,
    severance_tax_pct: float,
    loe_per_boe: float,
    transport_per_boe: float = 0.0,
    differential_usd_bbl: float = 0.0,
) -> CalcResult:
    """
    Netback per barrel:
    Netback = (Price + differential) × (1 - royalty) × (1 - prod_tax) - LOE - transport
    """
    effective_price = oil_price_usd_bbl + differential_usd_bbl
    after_royalty = effective_price * (1.0 - royalty_rate_pct / 100.0)
    after_prod_tax = after_royalty * (1.0 - severance_tax_pct / 100.0)
    netback = after_prod_tax - loe_per_boe - transport_per_boe

    return CalcResult(
        metric_name="Netback",
        metric_result=round(netback, 2),
        unit="USD/bbl",
        inputs_used={
            "oil_price_usd_bbl": oil_price_usd_bbl,
            "differential_usd_bbl": differential_usd_bbl,
            "royalty_rate_pct": royalty_rate_pct,
            "severance_tax_pct": severance_tax_pct,
            "loe_per_boe": loe_per_boe,
            "transport_per_boe": transport_per_boe,
        },
        formula="Netback = (Price + diff) × (1-royalty) × (1-prod_tax) - LOE - transport",
        workings=[
            f"Effective price: ${effective_price:.2f}/bbl",
            f"After royalty ({royalty_rate_pct}%): ${after_royalty:.2f}/bbl",
            f"After production tax ({severance_tax_pct}%): ${after_prod_tax:.2f}/bbl",
            f"Less LOE: -${loe_per_boe:.2f}/boe",
            f"Less transport: -${transport_per_boe:.2f}/boe",
            f"Netback: ${netback:.2f}/bbl",
        ],
        caveats=["Income tax not included (applies at corporate level); negative netback = sub-economic"],
        confidence=Confidence.HIGH,
    )


def calculate_cash_breakeven(
    royalty_rate_pct: float,
    severance_tax_pct: float,
    loe_per_boe: float,
    transport_per_boe: float = 0.0,
    differential_usd_bbl: float = 0.0,
) -> CalcResult:
    """
    Cash breakeven oil price: price at which netback = 0.
    P_breakeven = (LOE + transport) / ((1 - royalty) × (1 - prod_tax)) - differential
    """
    denominator = (1.0 - royalty_rate_pct / 100.0) * (1.0 - severance_tax_pct / 100.0)
    if denominator <= 0:
        return CalcResult(
            metric_name="Cash Breakeven", metric_result=None, unit="USD/bbl",
            inputs_used={}, formula="", workings=[], caveats=["Invalid fiscal terms"], confidence=Confidence.LOW,
        )
    breakeven = (loe_per_boe + transport_per_boe) / denominator - differential_usd_bbl

    return CalcResult(
        metric_name="Cash Breakeven Oil Price",
        metric_result=round(breakeven, 2),
        unit="USD/bbl",
        inputs_used={
            "royalty_rate_pct": royalty_rate_pct,
            "severance_tax_pct": severance_tax_pct,
            "loe_per_boe": loe_per_boe,
            "transport_per_boe": transport_per_boe,
            "differential_usd_bbl": differential_usd_bbl,
        },
        formula="Breakeven = (LOE + transport) / ((1-royalty)(1-prod_tax)) - differential",
        workings=[
            f"(${loe_per_boe:.2f} + ${transport_per_boe:.2f}) / {denominator:.4f} - ${differential_usd_bbl:.2f}",
            f"Cash breakeven: ${breakeven:.2f}/bbl",
        ],
        caveats=["Cash breakeven only; does not include G&A, income tax, or capex recovery"],
        confidence=Confidence.HIGH,
    )


def calculate_full_cycle_breakeven(
    cash_flows: list[YearlyCashFlow],
    acquisition_cost_usd: float,
    inputs: FinancialInputs,
    iterations: int = 50,
) -> CalcResult:
    """
    Full-cycle breakeven: oil price at which Asset PV10 = Acquisition Cost.

    Equivalently: the oil price at which the investment NPV (asset PV10 minus
    acquisition cost) = 0 at a 10% hurdle rate.
    Solved iteratively by bisection.
    """

    def investment_npv_at_price(price: float) -> float:
        """Investment NPV = Asset PV10 - Acquisition Cost."""
        new_price_obj = inputs.price.model_copy(update={"oil_price_usd_bbl": price})
        new_inputs = inputs.model_copy(update={"price": new_price_obj})
        cfs = build_cash_flow_schedule(new_inputs)
        asset_pv10 = sum(cf.net_cash_flow_usd / (1.1 ** cf.year) for cf in cfs)
        return asset_pv10 - acquisition_cost_usd

    # Bisection search: find price where investment NPV = 0 (asset PV10 = acquisition cost)
    low, high = 5.0, 200.0
    breakeven = None
    for _ in range(iterations):
        mid = (low + high) / 2.0
        npv_mid = investment_npv_at_price(mid)
        if abs(npv_mid) < 1000:
            breakeven = mid
            break
        if npv_mid < 0:
            low = mid
        else:
            high = mid
    if breakeven is None:
        breakeven = (low + high) / 2.0

    return CalcResult(
        metric_name="Full-Cycle Breakeven Oil Price",
        metric_result=round(breakeven, 2),
        unit="USD/bbl",
        inputs_used={
            "acquisition_cost_usd": acquisition_cost_usd,
            "discount_rate_pct": 10.0,
        },
        formula="Price where Asset PV10 = Acquisition Cost (i.e., investment NPV10 = 0)",
        workings=[
            f"Full-cycle breakeven: ${breakeven:.2f}/bbl (at 10% hurdle rate)",
            f"At this price, Asset PV10 exactly equals acquisition cost of ${acquisition_cost_usd/1e6:.1f}M",
        ],
        caveats=[
            "Includes all operating costs, development capex, ARO, and income taxes in the asset CFs",
            "Acquisition cost compared against asset PV10 — breakeven = price where deal is NPV-neutral",
        ],
        confidence=Confidence.MEDIUM,
    )


def calculate_fnd_cost(capex_usd: float, reserve_additions_mmboe: float) -> CalcResult:
    """Finding & Development cost per boe."""
    result = capex_usd / (reserve_additions_mmboe * 1_000_000) if reserve_additions_mmboe > 0 else None
    return CalcResult(
        metric_name="F&D Cost",
        metric_result=round(result, 2) if result else None,
        unit="USD/boe",
        inputs_used={"capex_usd": capex_usd, "reserve_additions_mmboe": reserve_additions_mmboe},
        formula="F&D = Development CAPEX / Reserve additions (boe)",
        workings=[f"${capex_usd/1e6:.1f}M / {reserve_additions_mmboe:.2f} mmboe = ${result:.2f}/boe" if result else ""],
        caveats=["Acquisition cost typically excluded from F&D (use for drill-bit F&D)"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_recycle_ratio(netback_usd_bbl: float, fnd_cost_usd_boe: float) -> CalcResult:
    """Recycle ratio = Netback / F&D cost (>1.5× indicates profitable exploration)."""
    result = netback_usd_bbl / fnd_cost_usd_boe if fnd_cost_usd_boe > 0 else None
    return CalcResult(
        metric_name="Recycle Ratio",
        metric_result=round(result, 2) if result else None,
        unit="×",
        inputs_used={"netback_usd_bbl": netback_usd_bbl, "fnd_cost_usd_boe": fnd_cost_usd_boe},
        formula="Recycle ratio = Netback ($/bbl) / F&D cost ($/boe)",
        workings=[f"${netback_usd_bbl:.2f} / ${fnd_cost_usd_boe:.2f} = {result:.2f}×" if result else ""],
        caveats=[">1.5× = healthy; <1.0× = destroying value"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_opex_per_boe(opex_annual_usd: float, production_boe: float) -> CalcResult:
    """Total OPEX per boe (LOE + G&A + transport + workovers)."""
    result = opex_annual_usd / production_boe if production_boe > 0 else None
    return CalcResult(
        metric_name="Total OPEX/boe",
        metric_result=round(result, 2) if result else None,
        unit="USD/boe",
        inputs_used={"opex_annual_usd": opex_annual_usd, "production_boe": production_boe},
        formula="OPEX/boe = Total annual OPEX / Annual production",
        workings=[f"${opex_annual_usd:,.0f} / {production_boe:,.0f} boe = ${result:.2f}/boe" if result else ""],
        caveats=["Includes LOE, G&A, transport, workovers — excludes capex and taxes"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


# ── Production Metrics ────────────────────────────────────────────────────────

def calculate_eur(
    q_i: float,
    D_nominal: float,
    b: float,
    q_econ: float,
    decline_type: DeclineType = DeclineType.exponential,
) -> CalcResult:
    """
    Estimated Ultimate Recovery — closed-form integral of q(t) from t=0 to t_econ.

    Exponential: EUR = (q_i - q_econ) / D  [boe/yr × yr → boe if rate in boe/day × 365]
    Hyperbolic:  EUR = (q_i^b / ((1-b) × D_i)) × (q_i^(1-b) - q_econ^(1-b))
    Harmonic:    EUR = (q_i / D_i) × ln(q_i / q_econ)
    """
    if q_econ >= q_i:
        return CalcResult(
            metric_name="EUR", metric_result=0.0, unit="boe",
            inputs_used={}, formula="", workings=["Economic limit >= initial rate"],
            caveats=[], confidence=Confidence.LOW,
        )

    days_per_year = 365.25

    if decline_type == DeclineType.exponential:
        # Annual rate units; convert to daily: q_i_daily = q_i (boepd)
        # EUR (boe) = (q_i_daily × 365.25) integral...
        # Actually using boepd rates: EUR = sum over years
        # Closed form: EUR = (q_i - q_econ) / D × 365.25  [boepd / (1/yr) = boe]
        eur = (q_i - q_econ) / D_nominal * days_per_year
        formula = "EUR = (q_i - q_econ) / D_nominal × 365.25"
        workings = [
            f"q_i={q_i:.1f} boepd, q_econ={q_econ:.1f} boepd, D={D_nominal:.4f}/yr",
            f"EUR = ({q_i:.1f} - {q_econ:.1f}) / {D_nominal:.4f} × 365.25 = {eur:,.0f} boe",
        ]
    elif decline_type == DeclineType.hyperbolic and b != 1.0:
        if b < 1.0:
            eur = (q_i**b / ((1.0 - b) * D_nominal)) * (q_i**(1.0 - b) - q_econ**(1.0 - b)) * days_per_year
        else:
            # b > 1 (rare): use numerical approximation via time steps
            t_econ = ((q_i / q_econ)**b - 1.0) / (b * D_nominal)
            steps = int(t_econ * 12) + 1
            dt = t_econ / steps
            eur = sum(decline_hyperbolic(q_i, D_nominal, b, i * dt) * dt * days_per_year for i in range(steps))
        formula = "EUR = (q_i^b / ((1-b)×D)) × (q_i^(1-b) - q_econ^(1-b)) × 365.25"
        workings = [f"Hyperbolic EUR (b={b}): {eur:,.0f} boe"]
    else:  # harmonic
        eur = (q_i / D_nominal) * math.log(q_i / q_econ) * days_per_year
        formula = "EUR = (q_i / D_i) × ln(q_i / q_econ) × 365.25"
        workings = [f"Harmonic EUR: {eur:,.0f} boe"]

    return CalcResult(
        metric_name="EUR",
        metric_result=round(eur, 0),
        unit="boe",
        inputs_used={"q_i_boepd": q_i, "D_nominal": D_nominal, "b": b, "q_econ_boepd": q_econ,
                     "decline_type": decline_type.value},
        formula=formula,
        workings=workings,
        caveats=["Closed-form integral; assumes single decline segment"],
        confidence=Confidence.HIGH,
    )


def calculate_decline_rate(q1: float, q2: float, period_years: float) -> CalcResult:
    """
    Back-calculate nominal annual exponential decline rate from two production points.
    D = -ln(q2/q1) / t
    """
    if q1 <= 0 or q2 <= 0 or period_years <= 0:
        return CalcResult(
            metric_name="Decline Rate", metric_result=None, unit="%/yr",
            inputs_used={}, formula="", workings=["Invalid inputs"],
            caveats=[], confidence=Confidence.LOW,
        )
    D = -math.log(q2 / q1) / period_years
    return CalcResult(
        metric_name="Nominal Decline Rate",
        metric_result=round(D * 100.0, 2),
        unit="%/yr",
        inputs_used={"q1": q1, "q2": q2, "period_years": period_years},
        formula="D = -ln(q2/q1) / t  [exponential assumption]",
        workings=[f"-ln({q2:.1f}/{q1:.1f}) / {period_years:.1f} = {D*100:.2f}%/yr"],
        caveats=["Assumes exponential decline; actual decline type may differ"],
        confidence=Confidence.MEDIUM,
    )


def calculate_gor(gas_rate_mcfd: float, oil_rate_bopd: float) -> CalcResult:
    """Gas-to-Oil Ratio (GOR) in scf/bbl."""
    result = (gas_rate_mcfd * 1000.0) / oil_rate_bopd if oil_rate_bopd > 0 else None
    return CalcResult(
        metric_name="GOR",
        metric_result=round(result, 0) if result else None,
        unit="scf/bbl",
        inputs_used={"gas_rate_mcfd": gas_rate_mcfd, "oil_rate_bopd": oil_rate_bopd},
        formula="GOR (scf/bbl) = Gas rate (Mcfd) × 1000 / Oil rate (bopd)",
        workings=[f"{gas_rate_mcfd:.1f} Mcfd × 1000 / {oil_rate_bopd:.1f} bopd = {result:,.0f} scf/bbl" if result else ""],
        caveats=["Rising GOR = reservoir depressurisation or gas cap breakthrough; >1,500 scf/bbl warrants investigation"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_water_cut(water_rate_bwpd: float, total_liquid_rate_blpd: float) -> CalcResult:
    """Water cut as % of total liquid production."""
    result = (water_rate_bwpd / total_liquid_rate_blpd * 100.0) if total_liquid_rate_blpd > 0 else None
    return CalcResult(
        metric_name="Water Cut",
        metric_result=round(result, 1) if result else None,
        unit="%",
        inputs_used={"water_rate_bwpd": water_rate_bwpd, "total_liquid_rate_blpd": total_liquid_rate_blpd},
        formula="Water Cut = Water rate / Total liquid rate × 100%",
        workings=[f"{water_rate_bwpd:.0f} bwpd / {total_liquid_rate_blpd:.0f} blpd = {result:.1f}%" if result else ""],
        caveats=["Rising water cut = natural water influx or injection breakthrough; >70% warrants investigation"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_reserve_replacement(reserve_additions_mmboe: float, production_mmboe: float) -> CalcResult:
    """Reserve Replacement Ratio (RRR) = additions / production × 100%."""
    result = (reserve_additions_mmboe / production_mmboe * 100.0) if production_mmboe > 0 else None
    return CalcResult(
        metric_name="Reserve Replacement Ratio",
        metric_result=round(result, 1) if result else None,
        unit="%",
        inputs_used={"reserve_additions_mmboe": reserve_additions_mmboe, "production_mmboe": production_mmboe},
        formula="RRR = Reserve additions / Production × 100%",
        workings=[f"{reserve_additions_mmboe:.2f} / {production_mmboe:.2f} × 100 = {result:.1f}%" if result else ""],
        caveats=["<100% = declining reserve base; only relevant for operator-drilled assets"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_wi_net_production(
    gross_rate_boepd: float,
    wi_pct: float,
    nri_pct: float,
) -> CalcResult:
    """
    Working Interest and Net Revenue Interest production.
    WI net (for cost sharing) = gross × WI%
    NRI net (for revenue) = gross × NRI%
    """
    wi_net = gross_rate_boepd * (wi_pct / 100.0)
    nri_net = gross_rate_boepd * (nri_pct / 100.0)
    return CalcResult(
        metric_name="WI/NRI Net Production",
        metric_result=nri_net,
        unit="boepd (NRI net)",
        inputs_used={"gross_rate_boepd": gross_rate_boepd, "wi_pct": wi_pct, "nri_pct": nri_pct},
        formula="WI net = gross × WI%; NRI net = gross × NRI%",
        workings=[
            f"WI net (cost burden): {gross_rate_boepd:.0f} × {wi_pct:.1f}% = {wi_net:.1f} boepd",
            f"NRI net (revenue entitlement): {gross_rate_boepd:.0f} × {nri_pct:.1f}% = {nri_net:.1f} boepd",
        ],
        caveats=["NRI = WI × (1 - royalty - ORRI); verify against lease agreements"],
        confidence=Confidence.HIGH,
    )


# ── Leverage / RBL Metrics ────────────────────────────────────────────────────

def calculate_borrowing_base(pv10_producing_usd: float) -> CalcResult:
    """
    Estimate RBL borrowing base ≈ 50–65% of PDP PV10.
    Returns conservative / base / optimistic range.
    """
    conservative = pv10_producing_usd * 0.50
    base_case = pv10_producing_usd * 0.55
    optimistic = pv10_producing_usd * 0.65

    return CalcResult(
        metric_name="RBL Borrowing Base Estimate",
        metric_result=round(base_case, 0),
        unit="USD",
        inputs_used={"pdp_pv10_usd": pv10_producing_usd},
        formula="Borrowing base ≈ 50–65% of PDP PV10 (lender rule of thumb)",
        workings=[
            f"PDP PV10: ${pv10_producing_usd/1e6:.1f}M",
            f"Conservative (50%): ${conservative/1e6:.1f}M",
            f"Base case (55%):    ${base_case/1e6:.1f}M",
            f"Optimistic (65%):   ${optimistic/1e6:.1f}M",
        ],
        caveats=[
            "Indicative only — actual borrowing base set by bank engineer reserve report",
            "Advance rate varies by lender, jurisdiction, commodity mix",
            "Bank price decks typically more conservative than spot",
        ],
        confidence=Confidence.MEDIUM,
    )


def calculate_llcr(
    pv_debt_service_usd: float,
    debt_outstanding_usd: float,
) -> CalcResult:
    """Loan Life Coverage Ratio = PV of future debt service / outstanding debt."""
    result = pv_debt_service_usd / debt_outstanding_usd if debt_outstanding_usd > 0 else None
    return CalcResult(
        metric_name="LLCR",
        metric_result=round(result, 2) if result else None,
        unit="×",
        inputs_used={"pv_debt_service_usd": pv_debt_service_usd, "debt_outstanding_usd": debt_outstanding_usd},
        formula="LLCR = PV of future debt service / Outstanding debt",
        workings=[f"${pv_debt_service_usd/1e6:.1f}M / ${debt_outstanding_usd/1e6:.1f}M = {result:.2f}×" if result else ""],
        caveats=["Covenant threshold typically ≥1.2×; below 1.0× = potential covenant breach"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_dscr(
    operating_cf_annual_usd: float,
    debt_service_annual_usd: float,
) -> CalcResult:
    """Debt Service Coverage Ratio = Annual operating CF / Annual debt service."""
    result = operating_cf_annual_usd / debt_service_annual_usd if debt_service_annual_usd > 0 else None
    return CalcResult(
        metric_name="DSCR",
        metric_result=round(result, 2) if result else None,
        unit="×",
        inputs_used={"operating_cf_annual_usd": operating_cf_annual_usd,
                     "debt_service_annual_usd": debt_service_annual_usd},
        formula="DSCR = Annual operating CF / Annual debt service (principal + interest)",
        workings=[f"${operating_cf_annual_usd/1e6:.1f}M / ${debt_service_annual_usd/1e6:.1f}M = {result:.2f}×" if result else ""],
        caveats=["Covenant threshold typically ≥1.2×; <1.0× = cannot service debt from operations"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


def calculate_net_debt_ebitda(net_debt_usd: float, ebitda_usd: float) -> CalcResult:
    """Net Debt / EBITDA leverage ratio."""
    result = net_debt_usd / ebitda_usd if ebitda_usd > 0 else None
    return CalcResult(
        metric_name="Net Debt/EBITDA",
        metric_result=round(result, 2) if result else None,
        unit="×",
        inputs_used={"net_debt_usd": net_debt_usd, "ebitda_usd": ebitda_usd},
        formula="Net Debt/EBITDA = Net debt / LTM EBITDA",
        workings=[f"${net_debt_usd/1e6:.1f}M / ${ebitda_usd/1e6:.1f}M = {result:.2f}×" if result else ""],
        caveats=["E&P sector RBL covenant typically ≤3.5×; >4× = high leverage"],
        confidence=Confidence.HIGH if result else Confidence.LOW,
    )


# ── Metric Registry ───────────────────────────────────────────────────────────

METRIC_REGISTRY: dict[str, str] = {
    "npv": "NPV at specified discount rate",
    "npv_10": "NPV at 10% discount rate (= PV10)",
    "pv10": "PV10 — SEC/SPE standard",
    "irr": "Internal Rate of Return (%)",
    "payback": "Simple payback period (years)",
    "moic": "Multiple on Invested Capital (×)",
    "ev_2p": "EV/2P reserves ($/boe)",
    "ev_1p": "EV/1P proved reserves ($/boe)",
    "ev_production": "EV per current boepd ($/boepd)",
    "ev_ebitda": "EV/EBITDA multiple (×)",
    "lifting_cost": "Lifting cost / LOE per boe ($/boe)",
    "netback": "Netback per barrel ($/bbl)",
    "cash_breakeven": "Cash breakeven oil price ($/bbl)",
    "full_cycle_breakeven": "Full-cycle breakeven oil price at NPV10=0 ($/bbl)",
    "fnd_cost": "Finding & Development cost ($/boe)",
    "recycle_ratio": "Recycle ratio — netback / F&D (×)",
    "opex_per_boe": "Total OPEX per boe ($/boe)",
    "eur": "Estimated Ultimate Recovery (boe)",
    "decline_rate": "Nominal annual decline rate (%/yr)",
    "gor": "Gas-to-Oil Ratio (scf/bbl)",
    "water_cut": "Water cut (%)",
    "reserve_replacement": "Reserve Replacement Ratio (%)",
    "wi_net_production": "WI/NRI net production (boepd)",
    "borrowing_base": "RBL Borrowing Base estimate (USD)",
    "llcr": "Loan Life Coverage Ratio (×)",
    "dscr": "Debt Service Coverage Ratio (×)",
    "net_debt_ebitda": "Net Debt/EBITDA leverage (×)",
}
