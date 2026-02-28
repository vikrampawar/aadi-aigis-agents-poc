"""
Fiscal regime calculations for Agent 04 — Finance Calculator.

Implements regime-specific fiscal logic driven by fiscal_terms_playbook.md.
Covers: GoM (US concessionary), UKCS, Norway, PSC (generic), Service Contracts.
"""

from __future__ import annotations

from aigis_agents.agent_04_finance_calculator.models import (
    CalcResult,
    Confidence,
    DealType,
    FiscalRegime,
    FiscalTerms,
    Jurisdiction,
)


# ── Concessionary / Royalty-Tax Regime ───────────────────────────────────────

def calculate_royalty_payment(
    gross_revenue_usd: float,
    royalty_rate_pct: float,
) -> CalcResult:
    """
    Royalty payment = gross revenue × royalty rate.
    Applied before any other deductions.
    """
    royalty = gross_revenue_usd * (royalty_rate_pct / 100.0)
    return CalcResult(
        metric_name="Royalty Payment",
        metric_result=round(royalty, 0),
        unit="USD",
        inputs_used={"gross_revenue_usd": gross_revenue_usd, "royalty_rate_pct": royalty_rate_pct},
        formula="Royalty = Gross revenue × Royalty rate",
        workings=[f"${gross_revenue_usd:,.0f} × {royalty_rate_pct}% = ${royalty:,.0f}"],
        caveats=["Federal royalty rates GoM: 12.5% (pre-2007 leases), 16.67% or 18.75% (post-2007)"],
        confidence=Confidence.HIGH,
    )


def calculate_severance_tax(
    gross_revenue_usd: float,
    severance_rate_pct: float,
) -> CalcResult:
    """
    State/production severance tax on gross revenue.
    Federal leases (GoM offshore) are typically 0% severance tax.
    """
    tax = gross_revenue_usd * (severance_rate_pct / 100.0)
    return CalcResult(
        metric_name="Severance Tax",
        metric_result=round(tax, 0),
        unit="USD",
        inputs_used={"gross_revenue_usd": gross_revenue_usd, "severance_rate_pct": severance_rate_pct},
        formula="Severance tax = Gross revenue × Severance rate",
        workings=[f"${gross_revenue_usd:,.0f} × {severance_rate_pct}% = ${tax:,.0f}"],
        caveats=[
            "GoM federal offshore: 0% severance (royalty replaces severance)",
            "Texas onshore: 4.6% oil, 7.5% gas; Louisiana: 12.5% oil, 1.3¢/mcf gas",
        ],
        confidence=Confidence.HIGH,
    )


def calculate_net_revenue_interest(
    wi_pct: float,
    royalty_pct: float,
    orri_pct: float = 0.0,
) -> CalcResult:
    """
    NRI = WI × (1 - royalty% - ORRI%)
    NRI determines the operator's share of revenue after burdens.
    """
    nri = (wi_pct / 100.0) * (1.0 - royalty_pct / 100.0 - orri_pct / 100.0) * 100.0
    return CalcResult(
        metric_name="Net Revenue Interest (NRI)",
        metric_result=round(nri, 4),
        unit="%",
        inputs_used={"wi_pct": wi_pct, "royalty_pct": royalty_pct, "orri_pct": orri_pct},
        formula="NRI = WI × (1 - royalty% - ORRI%)",
        workings=[
            f"WI: {wi_pct}%",
            f"Burdens: royalty {royalty_pct}% + ORRI {orri_pct}%",
            f"NRI = {wi_pct}% × (1 - {royalty_pct + orri_pct}%) = {nri:.4f}%",
        ],
        caveats=["NRI applies to revenue; WI applies to cost obligations"],
        confidence=Confidence.HIGH,
    )


def calculate_government_take(
    gross_revenue_usd: float,
    royalty_usd: float,
    production_taxes_usd: float,
    income_tax_usd: float,
    regime: FiscalRegime = FiscalRegime.concessionary_royalty_tax,
) -> CalcResult:
    """
    Government take as % of gross revenue.
    Includes all fiscal payments to government: royalty + prod taxes + income tax.
    """
    total_govt = royalty_usd + production_taxes_usd + income_tax_usd
    govt_take_pct = (total_govt / gross_revenue_usd * 100.0) if gross_revenue_usd > 0 else 0.0

    return CalcResult(
        metric_name="Government Take",
        metric_result=round(govt_take_pct, 2),
        unit="%",
        inputs_used={
            "gross_revenue_usd": gross_revenue_usd,
            "royalty_usd": royalty_usd,
            "production_taxes_usd": production_taxes_usd,
            "income_tax_usd": income_tax_usd,
        },
        formula="Govt take % = (Royalty + Prod taxes + Income tax) / Gross revenue × 100",
        workings=[
            f"Royalty: ${royalty_usd:,.0f}",
            f"Production taxes: ${production_taxes_usd:,.0f}",
            f"Income tax: ${income_tax_usd:,.0f}",
            f"Total govt payments: ${total_govt:,.0f}",
            f"Govt take: {govt_take_pct:.1f}%",
        ],
        caveats=[
            "Reference ranges: GoM ~60–65%, UKCS ~60–75% (post-EPL), Norway ~78%",
            ">80% government take is typically a red flag for project economics",
        ],
        confidence=Confidence.HIGH,
    )


# ── PSC (Production Sharing Contract) ────────────────────────────────────────

def calculate_psc_cashflow(
    gross_revenue_usd: float,
    opex_usd: float,
    capex_usd: float,
    cost_oil_limit_pct: float,
    govt_profit_oil_pct: float,
) -> CalcResult:
    """
    PSC cash flow mechanics:

    1. Cost oil = min(OPEX + CAPEX, cost_oil_limit × gross_revenue)
    2. Profit oil = gross_revenue - royalty (if any) - cost_oil
    3. Contractor share = profit_oil × (1 - govt_profit_oil_pct/100)
    4. Contractor net CF = cost_oil_recovered + contractor_profit_oil

    Note: PSC structure varies significantly by jurisdiction.
    This implements the generic/standard form.
    """
    cost_oil_ceiling = gross_revenue_usd * (cost_oil_limit_pct / 100.0)
    total_recoverable_costs = opex_usd + capex_usd
    cost_oil_recovered = min(total_recoverable_costs, cost_oil_ceiling)
    unrecovered = max(0.0, total_recoverable_costs - cost_oil_recovered)

    profit_oil = gross_revenue_usd - cost_oil_recovered
    govt_profit_oil = profit_oil * (govt_profit_oil_pct / 100.0)
    contractor_profit_oil = profit_oil - govt_profit_oil

    # Contractor net = cost oil recovered + contractor profit oil - actual costs
    contractor_net_cf = cost_oil_recovered + contractor_profit_oil - total_recoverable_costs

    return CalcResult(
        metric_name="PSC Contractor Net Cash Flow",
        metric_result=round(contractor_net_cf, 0),
        unit="USD",
        inputs_used={
            "gross_revenue_usd": gross_revenue_usd,
            "opex_usd": opex_usd,
            "capex_usd": capex_usd,
            "cost_oil_limit_pct": cost_oil_limit_pct,
            "govt_profit_oil_pct": govt_profit_oil_pct,
        },
        formula=(
            "Cost oil = min(OPEX+CAPEX, limit×revenue); "
            "Profit oil = revenue - cost_oil; "
            "Contractor = cost_oil + (1-govt_share)×profit_oil - actual costs"
        ),
        workings=[
            f"Gross revenue: ${gross_revenue_usd:,.0f}",
            f"Total costs: ${total_recoverable_costs:,.0f}",
            f"Cost oil ceiling ({cost_oil_limit_pct}%): ${cost_oil_ceiling:,.0f}",
            f"Cost oil recovered: ${cost_oil_recovered:,.0f}",
            f"Unrecovered costs (carry forward): ${unrecovered:,.0f}",
            f"Profit oil: ${profit_oil:,.0f}",
            f"Govt profit oil ({govt_profit_oil_pct}%): ${govt_profit_oil:,.0f}",
            f"Contractor profit oil: ${contractor_profit_oil:,.0f}",
            f"Contractor net CF: ${contractor_net_cf:,.0f}",
        ],
        caveats=[
            "Simplified PSC model; actual terms vary by country and contract vintage",
            "Unrecovered costs carry forward — modelled annually",
            "Income tax (if applicable to PSC) not included here",
        ],
        confidence=Confidence.MEDIUM,
    )


def calculate_r_factor(cumulative_revenue_usd: float, cumulative_cost_usd: float) -> float:
    """
    R-Factor = cumulative revenue / cumulative cost (running ratio).
    Used in PSC contracts to determine government take step-ups.
    """
    if cumulative_cost_usd <= 0:
        return 0.0
    return cumulative_revenue_usd / cumulative_cost_usd


def calculate_r_factor_govt_share(
    r_factor: float,
    thresholds: list[dict[str, float]],
) -> CalcResult:
    """
    Determine government profit oil share based on R-Factor thresholds.

    Thresholds format: [{"r_from": 0.0, "r_to": 1.0, "govt_share_pct": 40.0}, ...]
    Uses stair-step (discrete) interpolation.
    """
    govt_share = 0.0
    matched_band = None

    for band in sorted(thresholds, key=lambda x: x["r_from"]):
        r_from = band.get("r_from", 0.0)
        r_to = band.get("r_to", float("inf"))
        if r_from <= r_factor < r_to:
            govt_share = band["govt_share_pct"]
            matched_band = band
            break

    return CalcResult(
        metric_name="R-Factor Government Profit Oil Share",
        metric_result=round(govt_share, 2),
        unit="%",
        inputs_used={"r_factor": round(r_factor, 4), "threshold_bands": len(thresholds)},
        formula="Stair-step interpolation of govt share by R-Factor band",
        workings=[
            f"R-Factor = {r_factor:.3f}",
            f"Matched band: {matched_band}" if matched_band else "No band matched",
            f"Government profit oil share: {govt_share}%",
        ],
        caveats=["R-Factor based regimes are dynamic; share adjusts as cumulative revenues accrue"],
        confidence=Confidence.HIGH if matched_band else Confidence.LOW,
    )


# ── Special Regimes ───────────────────────────────────────────────────────────

def calculate_prrt(net_income_usd: float, augmented_bond_rate_pct: float = 7.0) -> CalcResult:
    """
    Australian Petroleum Resource Rent Tax (PRRT).
    PRRT = 40% of "PRRT profits" (net income above uplift threshold).

    Simplified: PRRT = 40% × max(0, net_income - uplift_allowance)
    Uplift rate for project expenditure: LTBR + 5% (exploration), LTBR + 5% (development)
    """
    prrt_rate = 0.40
    # Simplified: assume net_income already above uplift threshold
    prrt = net_income_usd * prrt_rate

    return CalcResult(
        metric_name="PRRT (Australian)",
        metric_result=round(prrt, 0),
        unit="USD",
        inputs_used={"net_income_usd": net_income_usd, "augmented_bond_rate_pct": augmented_bond_rate_pct},
        formula="PRRT = 40% × PRRT profits (net income after uplift)",
        workings=[
            f"Net income: ${net_income_usd:,.0f}",
            f"PRRT (simplified, 40%): ${prrt:,.0f}",
            f"Note: uplift allowance (bond rate + 5%) not modelled here",
        ],
        caveats=[
            "PRRT calculation is highly complex — this is a simplified estimate",
            "Uplift credits, transferred losses, and exploration deductions not modelled",
            "Use specialist tax adviser for binding PRRT calculations",
        ],
        confidence=Confidence.LOW,
    )


# ── Fiscal Profiles (Default Parameters) ─────────────────────────────────────

_FISCAL_PROFILES: dict[str, dict] = {
    "GoM_producing_asset": {
        "regime": "concessionary_royalty_tax",
        "royalty_rate_pct": 18.75,       # Post-2007 deepwater default; 12.5% for older leases
        "royalty_note": "Federal: 12.5% (pre-2007), 16.67% or 18.75% (post-2007). Verify per lease.",
        "severance_tax_pct": 0.0,        # Federal offshore: no state severance
        "income_tax_rate_pct": 21.0,     # US federal CT (as of 2024)
        "govt_take_range": "60–65%",
        "regime_description": "US federal royalty + corporate income tax; no state severance on OCS",
    },
    "UKCS_producing_asset": {
        "regime": "concessionary_royalty_tax",
        "royalty_rate_pct": 0.0,         # PRT abolished for post-1993 fields; legacy fields may apply
        "royalty_note": "PRT abolished; legacy pre-1993 fields may still have PRT liability",
        "severance_tax_pct": 0.0,
        "income_tax_rate_pct": 40.0,     # Ring Fence CT 30% + SC 10% = 40% (EPL adds 35% on excess profits)
        "income_tax_note": "Ring Fence CT 30% + Supplementary Charge 10% = 40%; EPL 35% on excess profits 2022+",
        "abcr_pct": 29.0,               # ABCR relief reduces effective rate
        "govt_take_range": "60–75% (EPL era)",
        "regime_description": "Ring Fence CT 30% + SC 10%; EPL 35% on profits above allowance; ABCR investment relief",
    },
    "Norway_producing_asset": {
        "regime": "concessionary_royalty_tax",
        "royalty_rate_pct": 0.0,
        "severance_tax_pct": 0.0,
        "income_tax_rate_pct": 22.0,     # Ordinary CT
        "petroleum_special_tax_pct": 71.8,  # Special petroleum tax; includes uplift
        "uplift_pct": 17.69,            # Uplift on investments (6-year)
        "govt_take_range": "~78%",
        "regime_description": "Ordinary CT 22% + Special Petroleum Tax 71.8% (with uplift); SDFI takes direct stake",
    },
    "International_psc": {
        "regime": "psc",
        "cost_oil_limit_pct": 50.0,
        "profit_oil_govt_share_pct": 60.0,  # Indicative; varies widely
        "royalty_rate_pct": 0.0,
        "income_tax_rate_pct": 30.0,
        "govt_take_range": "65–85%",
        "regime_description": "Generic PSC; cost oil + profit oil split; actual terms vary by country/vintage",
    },
}


def get_fiscal_profile(jurisdiction: Jurisdiction, deal_type: DealType) -> dict:
    """
    Return default fiscal parameters for a given jurisdiction and deal type.
    Used to pre-populate FiscalTerms when user hasn't specified all parameters.
    """
    key = f"{jurisdiction.value}_{deal_type.value}"
    if key in _FISCAL_PROFILES:
        return _FISCAL_PROFILES[key]
    # Try jurisdiction-only match
    for k, v in _FISCAL_PROFILES.items():
        if k.startswith(jurisdiction.value):
            return v
    return {
        "regime": "concessionary_royalty_tax",
        "royalty_rate_pct": 12.5,
        "severance_tax_pct": 0.0,
        "income_tax_rate_pct": 25.0,
        "govt_take_range": "Unknown",
        "regime_description": f"Default profile for {jurisdiction.value}; verify actual fiscal terms",
    }
