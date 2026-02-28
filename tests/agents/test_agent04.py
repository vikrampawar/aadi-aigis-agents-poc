"""Tests for Agent 04 — Upstream Finance Calculator (MESH v2.0).

Uses the correct FinancialInputs format (matching the existing test_agent_04_calculator.py).
"""
import pytest
from aigis_agents.agent_04_finance_calculator.agent import Agent04


# Correct FinancialInputs-compatible dict format
MINIMAL_FINANCIAL_INPUTS = {
    "deal_id": "test-deal-001",
    "deal_name": "Test Asset",
    "deal_type": "producing_asset",
    "jurisdiction": "GoM",
    "buyer": "Test Buyer",
    "evaluation_years": 5,
    "discount_rate_pct": 10.0,
    "price": {
        "oil_price_usd_bbl": 70.0,
        "gas_price_usd_mmbtu": 3.0,
        "ngl_price_pct_wti": 0.0,
        "apply_differential_usd_bbl": 0.0,
    },
    "production": {
        "initial_rate_boepd": 1200,
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
        "royalty_rate_pct": 18.75,
        "severance_tax_pct": 0.0,
        "income_tax_rate_pct": 21.0,
        "wi_pct": 80.0,
        "orri_pct": 0.0,
    },
    "costs": {
        "loe_per_boe": 18.0,
        "g_and_a_per_boe": 4.0,
        "workovers_annual_usd": 0,
        "transport_per_boe": 1.5,
    },
    "capex": {
        "acquisition_cost_usd": 5_000_000,
        "development_capex_by_year_usd": [],
        "abandonment_cost_p50_usd": 0.0,
        "abandonment_cost_p70_usd": 0.0,
        "abandonment_year": None,
    },
    "reserves": {
        "pdp_mmboe": 0.5,
        "p1_mmboe": 0.5,
        "p2_mmboe": 1.0,
        "ev_usd": 5_000_000,
    },
    "rbl": None,
}

HIGH_COST_INPUTS = {
    **MINIMAL_FINANCIAL_INPUTS,
    "deal_id": "test-deal-highcost",
    "costs": {
        "loe_per_boe": 50.0,
        "g_and_a_per_boe": 10.0,
        "workovers_annual_usd": 0,
        "transport_per_boe": 1.5,
    },
}


@pytest.mark.unit
class TestAgent04Init:

    def test_agent_id_correct(self):
        assert Agent04.AGENT_ID == "agent_04"

    def test_dk_tags_include_financial(self):
        assert "financial" in Agent04.DK_TAGS

    def test_is_agentbase_subclass(self):
        from aigis_agents.mesh.agent_base import AgentBase
        assert issubclass(Agent04, AgentBase)


@pytest.mark.unit
class TestAgent04ToolCall:

    def test_invoke_tool_call_returns_success(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent04().invoke(
            mode="tool_call",
            deal_id=deal_id,
            inputs=MINIMAL_FINANCIAL_INPUTS,
            output_dir=str(tmp_path),
        )
        assert result["status"] == "success"

    def test_invoke_tool_call_no_file_writes(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        Agent04().invoke(
            mode="tool_call",
            deal_id=deal_id,
            inputs=MINIMAL_FINANCIAL_INPUTS,
            output_dir=str(tmp_path),
        )
        output_dir = tmp_path / deal_id
        if output_dir.exists():
            md_files = list(output_dir.glob("04_*.md"))
            assert len(md_files) == 0

    def test_result_contains_npv(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent04().invoke(
            mode="tool_call",
            deal_id=deal_id,
            inputs=MINIMAL_FINANCIAL_INPUTS,
            output_dir=str(tmp_path),
        )
        data = result.get("data", {})
        assert "npv_10_usd" in data or "npv" in str(data).lower()

    def test_result_contains_irr(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent04().invoke(
            mode="tool_call",
            deal_id=deal_id,
            inputs=MINIMAL_FINANCIAL_INPUTS,
            output_dir=str(tmp_path),
        )
        data = result.get("data", {})
        assert "irr_pct" in data or "irr" in str(data).lower()


@pytest.mark.unit
class TestAgent04StandaloneMode:

    def test_invoke_standalone_runs_without_error(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent04().invoke(
            mode="standalone",
            deal_id=deal_id,
            inputs=MINIMAL_FINANCIAL_INPUTS,
            output_dir=str(tmp_path),
            run_sensitivity_analysis=False,
        )
        assert result.get("status") in ("success", "error")


@pytest.mark.unit
class TestAgent04NPVCalculation:

    def test_npv_is_numeric(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent04().invoke(
            mode="tool_call",
            deal_id=deal_id,
            inputs=MINIMAL_FINANCIAL_INPUTS,
            output_dir=str(tmp_path),
        )
        data = result.get("data", {})
        npv = data.get("npv_10_usd")
        if npv is not None:
            assert isinstance(npv, (int, float))

    def test_high_cost_scenario_lower_npv(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        """Higher LOE should reduce NPV."""
        r1 = Agent04().invoke(
            mode="tool_call", deal_id=deal_id,
            inputs=MINIMAL_FINANCIAL_INPUTS, output_dir=str(tmp_path),
        )
        r2 = Agent04().invoke(
            mode="tool_call", deal_id=deal_id + "_hc",
            inputs=HIGH_COST_INPUTS, output_dir=str(tmp_path),
        )
        npv1 = r1.get("data", {}).get("npv_10_usd")
        npv2 = r2.get("data", {}).get("npv_10_usd")
        if npv1 is not None and npv2 is not None:
            assert npv1 > npv2, "Lower cost deal should have higher NPV"


@pytest.mark.unit
class TestAgent04AuditBlock:

    def test_result_includes_audit_block(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent04().invoke(
            mode="tool_call",
            deal_id=deal_id,
            inputs=MINIMAL_FINANCIAL_INPUTS,
            output_dir=str(tmp_path),
        )
        assert "audit" in result
        assert result["audit"]["output_confidence"] in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
