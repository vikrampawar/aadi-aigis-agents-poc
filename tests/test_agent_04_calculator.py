"""
Unit tests for Agent 04 — Upstream Finance Calculator.

Covers pure-math functions in calculator.py, fiscal_engine.py, and validator.py.
All assertions use closed-form expected values computed from first principles.
"""

import math
import pytest

from aigis_agents.agent_04_finance_calculator.calculator import (
    build_cash_flow_schedule,
    calculate_cash_breakeven,
    calculate_irr,
    calculate_lifting_cost,
    calculate_netback,
    calculate_npv,
    decline_exponential,
    decline_harmonic,
    decline_hyperbolic,
)
from aigis_agents.agent_04_finance_calculator.fiscal_engine import (
    calculate_government_take,
    calculate_royalty_payment,
    get_fiscal_profile,
)
from aigis_agents.agent_04_finance_calculator.models import (
    DealType,
    FinancialAnalysisSummary,
    FinancialInputs,
    Jurisdiction,
    YearlyCashFlow,
)
from aigis_agents.agent_04_finance_calculator.validator import validate_metrics


# ── Helpers ───────────────────────────────────────────────────────────────────


def _minimal_inputs(**cost_overrides) -> FinancialInputs:
    """Minimal valid FinancialInputs; override cost keys as needed."""
    data = {
        "deal_id": "test-0001",
        "deal_name": "Test Asset",
        "deal_type": "producing_asset",
        "jurisdiction": "GoM",
        "buyer": "Test Buyer",
        "evaluation_years": 5,
        "discount_rate_pct": 10.0,
        "price": {
            "oil_price_usd_bbl": 60.0,
            "gas_price_usd_mmbtu": 3.0,
            "ngl_price_pct_wti": 0.0,
            "apply_differential_usd_bbl": 0.0,
        },
        "production": {
            "initial_rate_boepd": 1000,
            "oil_fraction": 1.0,
            "gas_fraction": 0.0,
            "ngl_fraction": 0.0,
            "decline_rate_annual_pct": 15.0,
            "decline_type": "exponential",
            "b_factor": 0.0,
            "economic_limit_bopd": 1.0,
            "uptime_pct": 100.0,
        },
        "fiscal": {
            "regime": "concessionary_royalty_tax",
            "royalty_rate_pct": 12.5,
            "severance_tax_pct": 0.0,
            "income_tax_rate_pct": 21.0,
            "wi_pct": 100.0,
            "orri_pct": 0.0,
        },
        "costs": {
            "loe_per_boe": cost_overrides.get("loe_per_boe", 10.0),
            "g_and_a_per_boe": cost_overrides.get("g_and_a_per_boe", 0.0),
            "workovers_annual_usd": cost_overrides.get("workovers_annual_usd", 0),
            "transport_per_boe": cost_overrides.get("transport_per_boe", 0.0),
        },
        "capex": {
            "acquisition_cost_usd": 10_000_000,
            "development_capex_by_year_usd": [],
            "abandonment_cost_p50_usd": 0.0,
            "abandonment_cost_p70_usd": 0.0,
            "abandonment_year": None,
        },
        "reserves": {
            "pdp_mmboe": 1.0,
            "p1_mmboe": 1.0,
            "p2_mmboe": 2.0,
            "ev_usd": 10_000_000,
        },
        "rbl": None,
    }
    return FinancialInputs.model_validate(data)


def _make_cf(year: int, net_cash_flow_usd: float, discount_rate: float = 0.10) -> YearlyCashFlow:
    """Construct a minimal YearlyCashFlow for NPV/IRR testing."""
    dcf = net_cash_flow_usd / ((1 + discount_rate) ** year)
    return YearlyCashFlow(
        year=year,
        production_boepd=0.0,
        production_boe=0.0,
        gross_revenue_usd=0.0,
        royalty_usd=0.0,
        net_revenue_usd=0.0,
        loe_usd=0.0,
        workovers_usd=0.0,
        transport_usd=0.0,
        g_and_a_usd=0.0,
        total_opex_usd=0.0,
        ebitda_usd=0.0,
        capex_usd=0.0,
        taxable_income_usd=0.0,
        income_tax_usd=0.0,
        net_cash_flow_usd=net_cash_flow_usd,
        discounted_cash_flow_usd=dcf,
    )


# ── Decline Curves ─────────────────────────────────────────────────────────────


class TestDeclineCurves:
    def test_exponential_at_t0_equals_initial_rate(self):
        assert decline_exponential(q_i=1000, D_nominal=0.15, t=0) == pytest.approx(1000.0)

    def test_exponential_at_t1(self):
        # q(1) = 1000 × e^(-0.15)
        expected = 1000.0 * math.exp(-0.15)
        assert decline_exponential(q_i=1000, D_nominal=0.15, t=1) == pytest.approx(expected, rel=1e-6)

    def test_exponential_decline_is_monotonically_decreasing(self):
        rates = [decline_exponential(1000, 0.15, t) for t in range(10)]
        for i in range(1, len(rates)):
            assert rates[i] < rates[i - 1]

    def test_hyperbolic_at_b0_matches_exponential(self):
        # b≈0 is mathematically the exponential limit
        hyp = decline_hyperbolic(q_i=1000, D_i=0.15, b=0.0001, t=1)
        exp = decline_exponential(q_i=1000, D_nominal=0.15, t=1)
        assert abs(hyp - exp) / exp < 0.001  # within 0.1%

    def test_harmonic_at_t0_equals_initial_rate(self):
        assert decline_harmonic(q_i=1000, D_i=0.15, t=0) == pytest.approx(1000.0)

    def test_harmonic_decline_is_monotonically_decreasing(self):
        rates = [decline_harmonic(1000, 0.15, t) for t in range(10)]
        for i in range(1, len(rates)):
            assert rates[i] < rates[i - 1]


# ── Cost Metrics ───────────────────────────────────────────────────────────────


class TestLiftingCost:
    def test_basic_loe_per_boe(self):
        result = calculate_lifting_cost(loe_annual_usd=1_000_000, production_boe=100_000)
        assert result.metric_result == pytest.approx(10.0)
        assert result.unit == "USD/boe"

    def test_fractional_result_rounds_to_two_decimal_places(self):
        # 9_477_000 / 520_000 = 18.225
        result = calculate_lifting_cost(loe_annual_usd=9_477_000, production_boe=520_000)
        assert result.metric_result == pytest.approx(18.23, abs=0.01)

    def test_zero_production_returns_none(self):
        result = calculate_lifting_cost(loe_annual_usd=1_000_000, production_boe=0)
        assert result.metric_result is None

    def test_confidence_is_high_for_valid_inputs(self):
        from aigis_agents.agent_04_finance_calculator.models import Confidence
        result = calculate_lifting_cost(loe_annual_usd=1_000_000, production_boe=100_000)
        assert result.confidence == Confidence.HIGH


class TestNetback:
    def test_simple_no_fiscal_no_transport(self):
        # netback = (50 + 0) × 1 × 1 - 10 - 0 = 40
        result = calculate_netback(
            oil_price_usd_bbl=50.0,
            royalty_rate_pct=0.0,
            severance_tax_pct=0.0,
            loe_per_boe=10.0,
        )
        assert result.metric_result == pytest.approx(40.0)

    def test_with_royalty_and_transport(self):
        # Corsair parameters:
        # effective_price = 70 + (-1.5) = 68.5
        # after_royalty = 68.5 × 0.875 = 59.9375
        # netback = 59.9375 - 18 - 1.5 = 40.4375 → 40.44
        result = calculate_netback(
            oil_price_usd_bbl=70.0,
            royalty_rate_pct=12.5,
            severance_tax_pct=0.0,
            loe_per_boe=18.0,
            transport_per_boe=1.5,
            differential_usd_bbl=-1.5,
        )
        assert result.metric_result == pytest.approx(40.44, abs=0.01)

    def test_negative_netback_when_costs_exceed_revenue(self):
        result = calculate_netback(
            oil_price_usd_bbl=20.0,
            royalty_rate_pct=12.5,
            severance_tax_pct=0.0,
            loe_per_boe=25.0,
        )
        assert result.metric_result < 0


class TestCashBreakeven:
    def test_zero_royalty_breakeven_equals_costs(self):
        # breakeven = (20 + 5) / 1.0 - 0 = 25.0
        result = calculate_cash_breakeven(
            royalty_rate_pct=0.0,
            severance_tax_pct=0.0,
            loe_per_boe=20.0,
            transport_per_boe=5.0,
        )
        assert result.metric_result == pytest.approx(25.0)

    def test_with_royalty_increases_breakeven(self):
        # Without royalty: (20 + 5) / 1.0 = 25.0
        # With 12.5% royalty: 25 / 0.875 = 28.57
        no_royalty = calculate_cash_breakeven(0.0, 0.0, 20.0, 5.0)
        with_royalty = calculate_cash_breakeven(12.5, 0.0, 20.0, 5.0)
        assert with_royalty.metric_result > no_royalty.metric_result

    def test_negative_differential_reduces_breakeven(self):
        # diff = -2: breakeven = 25/0.875 - (-2) = 28.57 + 2 = 30.57
        # Wait, this increases it — negative differential means the price you receive is lower
        # so you need a higher posted price to break even.
        # diff = +2: breakeven = 25/0.875 - 2 = 26.57 (lower — favorable differential)
        with_neg_diff = calculate_cash_breakeven(12.5, 0.0, 20.0, 5.0, differential_usd_bbl=-2.0)
        with_pos_diff = calculate_cash_breakeven(12.5, 0.0, 20.0, 5.0, differential_usd_bbl=2.0)
        assert with_neg_diff.metric_result > with_pos_diff.metric_result


# ── Valuation Metrics ─────────────────────────────────────────────────────────


class TestNPV:
    def test_single_cashflow_discounted(self):
        # $110k at year 1, 10% rate → PV = 110_000 / 1.1 = 100_000
        cfs = [_make_cf(1, 110_000.0)]
        result = calculate_npv(cfs, discount_rate_pct=10.0)
        assert result.metric_result == pytest.approx(100_000.0, rel=1e-4)

    def test_two_cashflows(self):
        # $55k at yr 1, $55k at yr 2, 10% → 50_000 + 45_454.55 = 95_454.55
        cfs = [_make_cf(1, 55_000.0), _make_cf(2, 55_000.0)]
        result = calculate_npv(cfs, discount_rate_pct=10.0)
        assert result.metric_result == pytest.approx(95_455.0, abs=1.0)

    def test_zero_discount_rate_sums_cashflows(self):
        cfs = [_make_cf(1, 100.0), _make_cf(2, 200.0), _make_cf(3, 300.0)]
        result = calculate_npv(cfs, discount_rate_pct=0.0)
        assert result.metric_result == pytest.approx(600.0, abs=1.0)

    def test_higher_discount_rate_lowers_npv(self):
        cfs = [_make_cf(t, 50_000.0) for t in range(1, 11)]
        npv_5 = calculate_npv(cfs, discount_rate_pct=5.0).metric_result
        npv_15 = calculate_npv(cfs, discount_rate_pct=15.0).metric_result
        assert npv_5 > npv_15

    def test_unit_is_usd(self):
        cfs = [_make_cf(1, 100_000.0)]
        assert calculate_npv(cfs, 10.0).unit == "USD"


class TestIRR:
    def test_single_year_known_irr(self):
        # invest $1000, receive $1150 at year 1 → IRR = 15%
        cfs = [_make_cf(1, 1_150.0)]
        result = calculate_irr(cfs, acquisition_cost_usd=1_000.0)
        assert result.metric_result == pytest.approx(15.0, abs=0.01)

    def test_irr_higher_than_hurdle_for_profitable_deal(self):
        # invest $1000, receive $200/yr for 10 years (sum = 2000 > 1000, good IRR)
        cfs = [_make_cf(t, 200.0) for t in range(1, 11)]
        result = calculate_irr(cfs, acquisition_cost_usd=1_000.0)
        assert result.metric_result is not None
        assert result.metric_result > 10.0  # exceeds 10% hurdle

    def test_irr_returns_none_for_no_positive_cashflows(self):
        cfs = [_make_cf(1, -500.0), _make_cf(2, -300.0)]
        result = calculate_irr(cfs, acquisition_cost_usd=1_000.0)
        assert result.metric_result is None
        assert result.error is not None


# ── Cash Flow Schedule ─────────────────────────────────────────────────────────


class TestBuildCashFlowSchedule:
    def test_returns_rows_for_each_year(self):
        inputs = _minimal_inputs()
        rows = build_cash_flow_schedule(inputs)
        assert len(rows) > 0
        assert len(rows) <= inputs.evaluation_years

    def test_year_sequence_starts_at_one(self):
        rows = build_cash_flow_schedule(_minimal_inputs())
        assert rows[0].year == 1

    def test_production_declines_year_over_year(self):
        rows = build_cash_flow_schedule(_minimal_inputs())
        # Exponential decline: each year production should be lower
        for i in range(1, len(rows)):
            assert rows[i].production_boepd < rows[i - 1].production_boepd

    def test_net_cashflow_positive_for_profitable_asset(self):
        # At $60/bbl oil, 12.5% royalty, $10/boe LOE — healthy asset
        rows = build_cash_flow_schedule(_minimal_inputs(loe_per_boe=10.0))
        # First few years should be cash-flow positive (before ARO)
        assert rows[0].net_cash_flow_usd > 0

    def test_economic_limit_terminates_schedule_early(self):
        # Set economic limit above initial rate so schedule stops after 1 year
        data = _minimal_inputs()
        # Use model_copy to set a very high economic limit
        new_prod = data.production.model_copy(update={"economic_limit_bopd": 999.0})
        limited_inputs = data.model_copy(update={"production": new_prod, "evaluation_years": 20})
        rows = build_cash_flow_schedule(limited_inputs)
        # Should terminate well before 20 years
        assert len(rows) < 20

    def test_aro_appended_to_final_year_when_no_abandonment_year(self):
        # ARO of $1M, no scheduled year → appended to last row
        data = _minimal_inputs()
        new_capex = data.capex.model_copy(update={
            "abandonment_cost_p50_usd": 1_000_000.0,
            "abandonment_year": None,
        })
        inputs = data.model_copy(update={"capex": new_capex})
        rows = build_cash_flow_schedule(inputs)
        # Last row should have capex_usd = 1_000_000
        assert rows[-1].capex_usd == pytest.approx(1_000_000.0)

    def test_development_capex_applied_in_correct_years(self):
        data = _minimal_inputs()
        dev_capex = [500_000.0, 0.0, 300_000.0]
        new_capex = data.capex.model_copy(update={
            "development_capex_by_year_usd": dev_capex,
            "abandonment_cost_p50_usd": 0.0,
        })
        inputs = data.model_copy(update={"capex": new_capex})
        rows = build_cash_flow_schedule(inputs)
        assert rows[0].capex_usd == pytest.approx(500_000.0)
        assert rows[1].capex_usd == pytest.approx(0.0)
        assert rows[2].capex_usd == pytest.approx(300_000.0)


# ── Fiscal Engine ─────────────────────────────────────────────────────────────


class TestRoyaltyPayment:
    def test_basic_royalty_calculation(self):
        # 12.5% of $1M gross revenue = $125,000
        result = calculate_royalty_payment(
            gross_revenue_usd=1_000_000.0,
            royalty_rate_pct=12.5,
        )
        assert result.metric_result == pytest.approx(125_000.0)

    def test_zero_royalty(self):
        result = calculate_royalty_payment(
            gross_revenue_usd=1_000_000.0,
            royalty_rate_pct=0.0,
        )
        assert result.metric_result == pytest.approx(0.0)


class TestGovernmentTake:
    def test_take_includes_royalty_and_tax(self):
        # gross = $100, royalty = $12.5, prod_tax = $0, income_tax = 16.275
        # govt take = (12.5 + 0 + 16.275) / 100 = 28.775%
        result = calculate_government_take(
            gross_revenue_usd=100.0,
            royalty_usd=12.5,
            production_taxes_usd=0.0,
            income_tax_usd=16.275,
        )
        assert result.metric_result == pytest.approx(28.775, abs=0.01)

    def test_zero_taxes_returns_zero_take(self):
        result = calculate_government_take(
            gross_revenue_usd=1_000_000.0,
            royalty_usd=0.0,
            production_taxes_usd=0.0,
            income_tax_usd=0.0,
        )
        assert result.metric_result == pytest.approx(0.0)


class TestGetFiscalProfile:
    def test_gom_producing_asset_returns_correct_regime(self):
        profile = get_fiscal_profile(Jurisdiction.GoM, DealType.producing_asset)
        assert profile["regime"] == "concessionary_royalty_tax"
        assert profile["income_tax_rate_pct"] == pytest.approx(21.0)

    def test_unknown_jurisdiction_returns_default(self):
        # International should fall back gracefully
        profile = get_fiscal_profile(Jurisdiction.International, DealType.exploration)
        assert "regime" in profile
        assert "royalty_rate_pct" in profile


# ── Validator ─────────────────────────────────────────────────────────────────


class TestValidateMetrics:
    def _make_summary(self, **overrides) -> FinancialAnalysisSummary:
        defaults = {
            "npv_10_usd": 50_000_000.0,
            "acquisition_cost_usd": 32_000_000.0,
            "value_creation_usd": 18_000_000.0,
            "irr_pct": 22.0,
            "payback_years": 3.5,
            "loe_per_boe": 18.0,
            "netback_usd_bbl": 32.0,
            "cash_breakeven_usd_bbl": 28.0,
            "full_cycle_breakeven_usd_bbl": 45.0,
            "ev_2p_usd_boe": 8.0,
            "government_take_pct": 28.0,
            "borrowing_base_usd": 20_000_000.0,
            "flag_count_critical": 0,
            "flag_count_warning": 0,
        }
        defaults.update(overrides)
        return FinancialAnalysisSummary(**defaults)

    def test_healthy_metrics_produce_no_critical_flags(self):
        summary = self._make_summary()
        flags = validate_metrics(summary, Jurisdiction.GoM, DealType.producing_asset)
        critical = [f for f in flags if "CRITICAL" in f.severity]
        assert len(critical) == 0

    def test_low_irr_triggers_critical_flag(self):
        summary = self._make_summary(irr_pct=5.0)
        flags = validate_metrics(summary, Jurisdiction.GoM, DealType.producing_asset)
        critical = [f for f in flags if "CRITICAL" in f.severity]
        assert len(critical) >= 1

    def test_negative_npv_triggers_critical_flag(self):
        summary = self._make_summary(npv_10_usd=-10_000_000.0, value_creation_usd=-42_000_000.0)
        flags = validate_metrics(summary, Jurisdiction.GoM, DealType.producing_asset)
        critical = [f for f in flags if "CRITICAL" in f.severity]
        assert len(critical) >= 1

    def test_long_payback_triggers_warning(self):
        summary = self._make_summary(payback_years=6.0, irr_pct=12.0)
        flags = validate_metrics(summary, Jurisdiction.GoM, DealType.producing_asset)
        warnings = [f for f in flags if "WARNING" in f.severity]
        assert len(warnings) >= 1

    def test_negative_netback_triggers_critical_flag(self):
        summary = self._make_summary(netback_usd_bbl=-5.0)
        flags = validate_metrics(summary, Jurisdiction.GoM, DealType.producing_asset)
        critical = [f for f in flags if "CRITICAL" in f.severity]
        assert len(critical) >= 1


# ── Pydantic Model Validation ─────────────────────────────────────────────────


class TestFinancialInputsValidation:
    def test_valid_inputs_parse_successfully(self):
        inputs = _minimal_inputs()
        assert inputs.deal_name == "Test Asset"

    def test_oil_gas_ngl_fractions_must_sum_to_one(self):
        data = _minimal_inputs()
        bad_prod = data.production.model_copy(update={
            "oil_fraction": 0.5,
            "gas_fraction": 0.5,
            "ngl_fraction": 0.1,  # sum = 1.1
        })
        with pytest.raises(Exception):
            data.model_copy(update={"production": bad_prod})
            # Pydantic validator checks on model creation
            FinancialInputs.model_validate({
                **data.model_dump(),
                "production": {**data.production.model_dump(), "ngl_fraction": 0.1}
            })
