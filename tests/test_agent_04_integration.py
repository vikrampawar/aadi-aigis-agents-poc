"""
Integration tests for Agent 04 — full pipeline execution.

These tests run the complete finance_calculator_agent() pipeline end-to-end
using the bundled example JSON inputs. No LLM calls are made (Agent 04 is
pure math in Sprint 1).

Tests verify:
- Pipeline completes without error
- Output artefacts are written to disk
- Headline metrics are plausible (sanity, not exact values)
- Deal registry is updated
"""

import json
from pathlib import Path

import pytest

from aigis_agents.agent_04_finance_calculator.agent import finance_calculator_agent
from aigis_agents.agent_04_finance_calculator.deal_registry import (
    REGISTRY_FILENAME,
    load_registry,
)

INPUTS_DIR = Path(__file__).parent.parent / "aigis_agents" / "agent_04_finance_calculator" / "inputs"
CORSAIR_JSON = INPUTS_DIR / "example_producing_asset_gom.json"
COULOMB_JSON = INPUTS_DIR / "project_coulomb_gom.json"


@pytest.fixture(scope="module")
def corsair_result(tmp_path_factory):
    """Run the full Agent 04 pipeline on Project Corsair once per test module."""
    out_dir = tmp_path_factory.mktemp("outputs")
    return finance_calculator_agent(
        inputs=CORSAIR_JSON,
        output_dir=out_dir,
        run_sensitivity_analysis=False,  # skip tornado for speed
    ), out_dir


@pytest.fixture(scope="module")
def coulomb_result(tmp_path_factory):
    """Run the full Agent 04 pipeline on Project Coulomb once per test module."""
    out_dir = tmp_path_factory.mktemp("outputs")
    return finance_calculator_agent(
        inputs=COULOMB_JSON,
        output_dir=out_dir,
        run_sensitivity_analysis=False,
    ), out_dir


class TestCorsairPipeline:
    def test_status_is_success(self, corsair_result):
        result, _ = corsair_result
        assert result.status == "success", f"Agent failed: {result}"

    def test_deal_id_matches_input(self, corsair_result):
        result, _ = corsair_result
        assert result.deal_id == "00000000-0000-0000-0000-c005a1000002"

    def test_cashflow_rows_exist(self, corsair_result):
        result, _ = corsair_result
        assert len(result.cash_flows) > 0
        assert len(result.cash_flows) <= 20

    def test_cashflow_years_are_sequential(self, corsair_result):
        result, _ = corsair_result
        years = [cf.year for cf in result.cash_flows]
        assert years == list(range(1, len(years) + 1))

    def test_summary_headline_metrics_present(self, corsair_result):
        result, _ = corsair_result
        s = result.summary
        assert s.npv_10_usd is not None
        assert s.irr_pct is not None
        assert s.loe_per_boe is not None
        assert s.cash_breakeven_usd_bbl is not None
        assert s.netback_usd_bbl is not None

    def test_irr_is_plausible(self, corsair_result):
        result, _ = corsair_result
        # Corsair: $32M acquisition, GoM producing asset — should have positive IRR
        assert result.summary.irr_pct is not None
        assert result.summary.irr_pct > 0

    def test_loe_is_in_gom_range(self, corsair_result):
        result, _ = corsair_result
        # Corsair LOE $18/boe — should fall in typical GoM range $8–$80
        assert 5 < result.summary.loe_per_boe < 100

    def test_pv10_is_positive(self, corsair_result):
        result, _ = corsair_result
        # Asset PV10 (intrinsic value) should be positive
        assert result.summary.npv_10_usd > 0

    def test_output_files_written(self, corsair_result):
        result, out_dir = corsair_result
        deal_id = result.deal_id
        md_path = out_dir / deal_id / "04_finance_calculator" / "04_financial_analysis.md"
        json_path = out_dir / deal_id / "04_finance_calculator" / "04_financial_analysis.json"
        assert md_path.exists(), f"Markdown report not found: {md_path}"
        assert json_path.exists(), f"JSON output not found: {json_path}"

    def test_json_output_is_valid(self, corsair_result):
        result, out_dir = corsair_result
        json_path = out_dir / result.deal_id / "04_finance_calculator" / "04_financial_analysis.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["status"] == "success"
        assert "summary" in data
        assert "cash_flows" in data

    def test_markdown_report_contains_key_sections(self, corsair_result):
        result, out_dir = corsair_result
        md_path = out_dir / result.deal_id / "04_finance_calculator" / "04_financial_analysis.md"
        content = md_path.read_text(encoding="utf-8")
        assert "Financial Analysis Report" in content
        assert "Executive Summary" in content
        assert "Production Profile & Cash Flows" in content

    def test_deal_registry_updated(self, corsair_result):
        result, out_dir = corsair_result
        registry = load_registry(out_dir)
        assert registry.agent_stats.total_deals >= 1
        deal_ids = [d.deal_id for d in registry.deals]
        assert result.deal_id in deal_ids

    def test_flags_list_is_present(self, corsair_result):
        result, _ = corsair_result
        # flags may be empty (healthy deal) but must be a list
        assert isinstance(result.flags, list)


class TestCoulombPipeline:
    def test_status_is_success(self, coulomb_result):
        result, _ = coulomb_result
        assert result.status == "success"

    def test_coulomb_irr_is_low_vs_corsair(self, corsair_result, coulomb_result):
        """Coulomb ($700M bid vs $583M PV10) should have lower IRR than Corsair ($32M vs higher PV10)."""
        corsair_irr = corsair_result[0].summary.irr_pct
        coulomb_irr = coulomb_result[0].summary.irr_pct
        assert coulomb_irr is not None
        assert corsair_irr is not None
        assert coulomb_irr < corsair_irr

    def test_coulomb_has_critical_flags(self, coulomb_result):
        """Coulomb IRR ~5% should trigger at least one CRITICAL flag."""
        result, _ = coulomb_result
        assert result.summary.flag_count_critical >= 1

    def test_coulomb_pv10_below_acquisition_cost(self, coulomb_result):
        """Coulomb at flat $65/bbl: Asset PV10 should be below the $700M bid (value destruction)."""
        result, _ = coulomb_result
        assert result.summary.npv_10_usd is not None
        assert result.summary.acquisition_cost_usd is not None
        assert result.summary.npv_10_usd < result.summary.acquisition_cost_usd


class TestRegistryAccumulation:
    def test_two_runs_accumulate_in_registry(self, tmp_path):
        """Running the same deal twice should add two run records."""
        result1 = finance_calculator_agent(
            inputs=CORSAIR_JSON,
            output_dir=tmp_path,
            run_sensitivity_analysis=False,
        )
        result2 = finance_calculator_agent(
            inputs=CORSAIR_JSON,
            output_dir=tmp_path,
            run_sensitivity_analysis=False,
        )
        assert result1.status == "success"
        assert result2.status == "success"

        registry = load_registry(tmp_path)
        deal = next(d for d in registry.deals if d.deal_id == result1.deal_id)
        assert deal.run_count == 2
        assert registry.agent_stats.total_runs == 2
