"""Pydantic data models for Agent 04 — Upstream Finance Calculator."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ── Enumerations ──────────────────────────────────────────────────────────────

class DealType(str, Enum):
    producing_asset = "producing_asset"
    exploration = "exploration"
    development = "development"
    corporate = "corporate"


class Jurisdiction(str, Enum):
    GoM = "GoM"
    UKCS = "UKCS"
    Norway = "Norway"
    International = "International"


class FiscalRegime(str, Enum):
    concessionary_royalty_tax = "concessionary_royalty_tax"
    psc = "psc"
    service_contract = "service_contract"


class DeclineType(str, Enum):
    exponential = "exponential"
    hyperbolic = "hyperbolic"
    harmonic = "harmonic"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Financial Input Models ────────────────────────────────────────────────────

class PriceAssumptions(BaseModel):
    """Commodity price assumptions (real, flat deck unless stated otherwise)."""
    oil_price_usd_bbl: float = Field(..., description="WTI/Brent base price $/bbl")
    gas_price_usd_mmbtu: float = Field(3.0, description="Henry Hub or local gas price $/MMBtu")
    ngl_price_pct_wti: float = Field(35.0, description="NGL realization as % of WTI")
    apply_differential_usd_bbl: float = Field(0.0, description="Basis differential (negative = discount)")


class ProductionAssumptions(BaseModel):
    """Production profile and decline parameters."""
    initial_rate_boepd: float = Field(..., description="Current gross production rate (boepd)")
    oil_fraction: float = Field(..., ge=0.0, le=1.0, description="Oil fraction of total production")
    gas_fraction: float = Field(..., ge=0.0, le=1.0, description="Gas fraction of total production")
    ngl_fraction: float = Field(0.0, ge=0.0, le=1.0, description="NGL fraction of total production")
    decline_rate_annual_pct: float = Field(..., gt=0.0, description="Nominal annual decline rate (%)")
    decline_type: DeclineType = DeclineType.exponential
    b_factor: float = Field(0.0, ge=0.0, le=2.0, description="Arps b-factor (0=exponential, hyperbolic only)")
    economic_limit_bopd: float = Field(5.0, gt=0.0, description="Economic limit rate (bopd) below which well abandoned")
    uptime_pct: float = Field(95.0, gt=0.0, le=100.0, description="Facility/well uptime (%)")

    @model_validator(mode="after")
    def check_fractions(self) -> "ProductionAssumptions":
        total = self.oil_fraction + self.gas_fraction + self.ngl_fraction
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"oil_fraction + gas_fraction + ngl_fraction must sum to 1.0 (got {total:.3f})"
            )
        return self


class FiscalTerms(BaseModel):
    """Fiscal regime and tax parameters."""
    regime: FiscalRegime = FiscalRegime.concessionary_royalty_tax
    royalty_rate_pct: float = Field(..., ge=0.0, le=100.0, description="Royalty rate (%)")
    severance_tax_pct: float = Field(0.0, ge=0.0, le=100.0, description="Severance/production tax (%)")
    income_tax_rate_pct: float = Field(21.0, ge=0.0, le=100.0, description="Corporate income tax rate (%)")
    wi_pct: float = Field(100.0, ge=0.0, le=100.0, description="Working interest (%)")
    orri_pct: float = Field(0.0, ge=0.0, le=100.0, description="Overriding royalty interest (%)")
    # PSC-specific fields (used only when regime=psc)
    cost_oil_limit_pct: float | None = Field(None, description="Cost oil ceiling as % of gross revenue (PSC)")
    profit_oil_govt_share_pct: float | None = Field(None, description="Government profit oil share % (PSC)")
    r_factor_thresholds: list[dict[str, float]] | None = Field(
        None, description="R-Factor stair-step thresholds [{r_from, r_to, govt_share_pct}] (PSC)"
    )


class CostAssumptions(BaseModel):
    """Operating cost parameters."""
    loe_per_boe: float = Field(..., ge=0.0, description="Lease operating expense per boe ($/boe)")
    g_and_a_per_boe: float = Field(0.0, ge=0.0, description="G&A overhead allocated per boe ($/boe)")
    workovers_annual_usd: float = Field(0.0, ge=0.0, description="Annual workover budget (USD)")
    transport_per_boe: float = Field(0.0, ge=0.0, description="Transportation/gathering per boe ($/boe)")


class CapexSchedule(BaseModel):
    """Capital expenditure schedule."""
    acquisition_cost_usd: float = Field(0.0, ge=0.0, description="Acquisition consideration (USD)")
    development_capex_by_year_usd: list[float] = Field(
        default_factory=list,
        description="Development CAPEX by year (year 1 = index 0), USD"
    )
    abandonment_cost_p50_usd: float = Field(0.0, ge=0.0, description="ARO P50 estimate (USD)")
    abandonment_cost_p70_usd: float = Field(0.0, ge=0.0, description="ARO P70 estimate (USD)")
    abandonment_year: int | None = Field(None, description="Year ARO cost incurred (None = at economic limit)")


class ReservesAssumptions(BaseModel):
    """Reserves volumes for EV/reserves multiples."""
    pdp_mmboe: float | None = Field(None, ge=0.0, description="PDP reserves (mmboe)")
    p1_mmboe: float | None = Field(None, ge=0.0, description="1P (Proved) reserves (mmboe)")
    p2_mmboe: float | None = Field(None, ge=0.0, description="2P (Proved + Probable) reserves (mmboe)")
    ev_usd: float | None = Field(None, ge=0.0, description="Enterprise value / acquisition cost for EV multiples (USD)")


class RBLAssumptions(BaseModel):
    """Reserve-based lending parameters (optional)."""
    facility_usd: float | None = Field(None, ge=0.0, description="Total RBL facility size (USD)")
    drawn_usd: float | None = Field(None, ge=0.0, description="Amount currently drawn (USD)")
    margin_pct: float | None = Field(None, ge=0.0, description="Lending margin over SOFR/SONIA (%)")
    debt_service_annual_usd: float | None = Field(None, ge=0.0, description="Annual debt service (principal + interest, USD)")


class FinancialInputs(BaseModel):
    """Top-level input model for Agent 04 Finance Calculator."""
    deal_id: str = Field(..., description="UUID identifying the deal (matches Agent 01 deal_id)")
    deal_name: str = Field(..., description="Human-readable deal name (e.g. 'Project Corsair')")
    deal_type: DealType
    jurisdiction: Jurisdiction
    buyer: str | None = Field(None, description="Acquiring entity name")
    evaluation_years: int = Field(20, ge=1, le=50, description="DCF evaluation horizon (years)")
    discount_rate_pct: float = Field(10.0, gt=0.0, description="Base discount rate for NPV (%)")
    price: PriceAssumptions
    production: ProductionAssumptions
    fiscal: FiscalTerms
    costs: CostAssumptions
    capex: CapexSchedule
    reserves: ReservesAssumptions | None = None
    rbl: RBLAssumptions | None = None


# ── Calculation Result Models ─────────────────────────────────────────────────

class CalcResult(BaseModel):
    """
    Output of a single financial calculation.
    Matches the mesh spec format exactly:
    {metric_result, unit, inputs_used, formula, workings, caveats, confidence, unit_conversions_applied}
    """
    metric_name: str
    metric_result: float | None = None
    unit: str
    inputs_used: dict[str, Any] = Field(default_factory=dict)
    formula: str = ""
    workings: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.HIGH
    unit_conversions_applied: list[str] = Field(default_factory=list)
    error: str | None = None


class YearlyCashFlow(BaseModel):
    """Annual cash flow row in the DCF schedule."""
    year: int
    production_boepd: float          # Average annual production rate
    production_boe: float            # Annual production volume
    gross_revenue_usd: float
    royalty_usd: float
    net_revenue_usd: float           # gross_revenue - royalty
    loe_usd: float
    workovers_usd: float
    transport_usd: float
    g_and_a_usd: float
    total_opex_usd: float
    ebitda_usd: float                # net_revenue - total_opex
    capex_usd: float
    taxable_income_usd: float
    income_tax_usd: float
    net_cash_flow_usd: float         # After all costs, capex, tax
    discounted_cash_flow_usd: float  # Discounted at base discount_rate


class SensitivityRow(BaseModel):
    """One row in the sensitivity / tornado table."""
    variable: str
    variable_label: str
    base_value: float
    base_npv_usd: float
    minus_20_pct_npv: float | None = None
    minus_10_pct_npv: float | None = None
    plus_10_pct_npv: float | None = None
    plus_20_pct_npv: float | None = None
    swing_usd: float = 0.0           # (max NPV - min NPV) across all perturbations


class FinancialQualityFlag(BaseModel):
    """A single benchmark/quality flag on a computed metric."""
    severity: str                    # "🔴 CRITICAL" | "🟡 WARNING" | "🟢 INFO"
    metric: str
    value: float | None
    threshold: str
    message: str


class FinancialAnalysisSummary(BaseModel):
    """Headline metrics — stored in deal registry per run.

    Convention: npv_10_usd is the ASSET-LEVEL PV10 (intrinsic value of future cash flows,
    excluding acquisition cost). Compare against acquisition_cost_usd to assess deal
    attractiveness. value_creation_usd = npv_10_usd − acquisition_cost_usd.
    """
    npv_10_usd: float | None = None           # Asset PV10 — intrinsic value of future CFs
    acquisition_cost_usd: float | None = None  # Bid price (for comparison vs PV10)
    value_creation_usd: float | None = None   # Asset PV10 − Acquisition Cost (investment margin)
    irr_pct: float | None = None
    payback_years: float | None = None
    moic: float | None = None
    loe_per_boe: float | None = None
    netback_usd_bbl: float | None = None
    cash_breakeven_usd_bbl: float | None = None
    full_cycle_breakeven_usd_bbl: float | None = None
    ev_2p_usd_boe: float | None = None
    ev_1p_usd_boe: float | None = None
    ev_production_usd_boepd: float | None = None
    government_take_pct: float | None = None
    borrowing_base_usd: float | None = None
    eur_mmboe: float | None = None
    flag_count_critical: int = 0
    flag_count_warning: int = 0


class AgentResult(BaseModel):
    """Complete output of one Agent 04 run."""
    status: str                      # "success" | "error" | "partial"
    deal_id: str
    deal_name: str
    outputs: dict[str, str] = Field(default_factory=dict)  # artefact name → file path
    summary: FinancialAnalysisSummary = Field(default_factory=FinancialAnalysisSummary)
    all_metrics: dict[str, CalcResult] = Field(default_factory=dict)
    cash_flows: list[YearlyCashFlow] = Field(default_factory=list)
    sensitivity: list[SensitivityRow] = Field(default_factory=list)
    flags: list[FinancialQualityFlag] = Field(default_factory=list)
    run_timestamp: str = ""
    cost_usd: float = 0.0
    error_message: str | None = None


# ── Deal Registry Models ──────────────────────────────────────────────────────

class RunRecord(BaseModel):
    """Snapshot of one Agent 04 run stored in the registry."""
    run_id: str
    timestamp: str                   # ISO UTC
    inputs_hash: str                 # MD5 of serialised FinancialInputs (detect changed assumptions)
    headline_metrics: FinancialAnalysisSummary
    cost_usd: float = 0.0
    flag_count_critical: int = 0


class DealRecord(BaseModel):
    """All runs for a single deal."""
    deal_id: str
    deal_name: str
    deal_type: str
    jurisdiction: str
    buyer: str | None = None
    first_run_timestamp: str
    last_run_timestamp: str
    run_count: int
    runs: list[RunRecord] = Field(default_factory=list)


class AgentRegistryStats(BaseModel):
    total_deals: int = 0
    total_runs: int = 0
    first_run_timestamp: str | None = None
    last_run_timestamp: str | None = None


class AgentRegistry(BaseModel):
    agent_id: str = "agent_04_finance_calculator"
    generated_at: str = ""
    agent_stats: AgentRegistryStats = Field(default_factory=AgentRegistryStats)
    deals: list[DealRecord] = Field(default_factory=list)

    def get_deal(self, deal_id: str) -> DealRecord | None:
        for d in self.deals:
            if d.deal_id == deal_id:
                return d
        return None
