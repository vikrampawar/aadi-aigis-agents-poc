"""
Tests for Agent 07 — chart_generator.py.

Uses matplotlib Agg backend (no display required).
Tests that output files are created and have non-zero size.
No pixel-perfect assertions.
"""

from __future__ import annotations

import os
import importlib

import pytest


# ── Skip entire module if matplotlib/plotly unavailable ───────────────────────

matplotlib_available = importlib.util.find_spec("matplotlib") is not None
plotly_available     = importlib.util.find_spec("plotly") is not None

pytestmark = pytest.mark.skipif(
    not matplotlib_available,
    reason="matplotlib not installed",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_periods(n: int = 24) -> list[dict]:
    """Synthetic normalized production periods."""
    periods = []
    for i in range(n):
        oil  = 800.0 * (0.98 ** i)
        gas  = oil * 3.75 / 1000.0   # 3750 scf/stb GOR → gas in MMcfd equivalent
        wat  = 100.0 * (1.02 ** i)
        boe  = oil + gas * 1e3 / 6.0 + wat / 6.28
        periods.append({
            "period":        f"2023-{(i % 12) + 1:02d}",
            "month_idx":     float(i),
            "oil_norm":      oil,
            "gas_norm":      gas * 1e3 / 6.0,
            "water_norm":    wat / 6.28,
            "boe_norm":      boe,
            "oil_bopd":      oil,
            "gor_scf_stb":   3750.0,
            "wc_pct":        wat / (oil + wat) * 100.0,
        })
    return periods


def _make_dca_result():
    from aigis_agents.agent_07_well_cards.dca_engine import DCAResult
    return DCAResult(
        curve_type   = "hyperbolic",
        qi_boepd     = 1000.0,
        Di_annual_pct = 22.0,
        b_factor      = 0.5,
        eur_mmboe     = 1.8,
        fit_r2        = 0.94,
        months_of_data = 24,
    )


def _make_well_cards(n: int = 3) -> list[dict]:
    from aigis_agents.agent_07_well_cards.rag_classifier import GREEN, AMBER, RED
    statuses = [GREEN, AMBER, RED]
    cards = []
    for i in range(n):
        cards.append({
            "well_name":   f"WELL-{i+1:03d}",
            "rag_status":  statuses[i % len(statuses)],
            "metrics":     {"current_rate_boepd": 1000.0 - i * 200.0},
            "decline_curve": {"eur_mmboe": 1.5 - i * 0.3},
            "flags":       [],
            "_production_history": _make_periods(12),
            "_reserve_estimates":  {"2P": 1.2},
        })
    return cards


# ── Per-well chart ────────────────────────────────────────────────────────────

class TestGenerateWellChart:
    def test_creates_png_file(self, tmp_path):
        from aigis_agents.agent_07_well_cards.chart_generator import generate_well_chart
        out = str(tmp_path / "WELL-001_production.png")
        result = generate_well_chart(
            well_name    = "WELL-001",
            periods      = _make_periods(),
            dca_result   = _make_dca_result(),
            forecast_data = {},
            rag_status   = "GREEN",
            output_path  = out,
        )
        assert result is not None
        assert os.path.exists(out)
        assert os.path.getsize(out) > 5_000   # at least 5 KB

    def test_returns_none_for_empty_periods(self, tmp_path):
        from aigis_agents.agent_07_well_cards.chart_generator import generate_well_chart
        out = str(tmp_path / "empty.png")
        result = generate_well_chart(
            well_name    = "EMPTY",
            periods      = [],
            dca_result   = None,
            forecast_data = {},
            rag_status   = "BLACK",
            output_path  = out,
        )
        assert result is None

    def test_creates_parent_dirs(self, tmp_path):
        from aigis_agents.agent_07_well_cards.chart_generator import generate_well_chart
        nested = str(tmp_path / "deep" / "dir" / "chart.png")
        generate_well_chart(
            well_name   = "W",
            periods     = _make_periods(12),
            dca_result  = None,
            forecast_data = {},
            rag_status  = "AMBER",
            output_path = nested,
        )
        assert os.path.exists(nested)

    @pytest.mark.parametrize("rag", ["GREEN", "AMBER", "RED", "BLACK"])
    def test_all_rag_statuses_render(self, tmp_path, rag):
        from aigis_agents.agent_07_well_cards.chart_generator import generate_well_chart
        out = str(tmp_path / f"chart_{rag}.png")
        generate_well_chart(
            well_name    = f"TEST-{rag}",
            periods      = _make_periods(18),
            dca_result   = _make_dca_result(),
            forecast_data = {},
            rag_status   = rag,
            output_path  = out,
        )
        assert os.path.exists(out)


# ── Fleet summary chart ───────────────────────────────────────────────────────

class TestGenerateFleetSummaryChart:
    def test_creates_fleet_png(self, tmp_path):
        from aigis_agents.agent_07_well_cards.chart_generator import generate_fleet_summary_chart
        out = str(tmp_path / "fleet_summary.png")
        result = generate_fleet_summary_chart(_make_well_cards(4), out)
        assert result is not None
        assert os.path.exists(out)
        assert os.path.getsize(out) > 5_000

    def test_empty_cards_returns_none(self, tmp_path):
        from aigis_agents.agent_07_well_cards.chart_generator import generate_fleet_summary_chart
        result = generate_fleet_summary_chart([], str(tmp_path / "x.png"))
        assert result is None


# ── Plotly fleet dashboard ────────────────────────────────────────────────────

@pytest.mark.skipif(not plotly_available, reason="plotly not installed")
class TestGenerateFleetDashboard:
    def test_creates_html_file(self, tmp_path):
        from aigis_agents.agent_07_well_cards.chart_generator import generate_fleet_dashboard
        out = str(tmp_path / "fleet_dashboard.html")
        result = generate_fleet_dashboard(_make_well_cards(3), out, deal_name="Test Deal")
        assert result is not None
        assert os.path.exists(out)
        assert os.path.getsize(out) > 10_000   # HTML + embedded Plotly CDN call

    def test_html_contains_plotly_ref(self, tmp_path):
        from aigis_agents.agent_07_well_cards.chart_generator import generate_fleet_dashboard
        out = str(tmp_path / "dash.html")
        generate_fleet_dashboard(_make_well_cards(2), out)
        with open(out, encoding="utf-8") as fh:
            content = fh.read()
        assert "plotly" in content.lower()

    def test_empty_cards_returns_none(self, tmp_path):
        from aigis_agents.agent_07_well_cards.chart_generator import generate_fleet_dashboard
        result = generate_fleet_dashboard([], str(tmp_path / "x.html"))
        assert result is None
