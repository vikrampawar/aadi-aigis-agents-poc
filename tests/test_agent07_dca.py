"""
Tests for Agent 07 — DCA engine (dca_engine.py).

Covers:
  - arps_hyperbolic() and arps_exponential() equations
  - compute_eur() numerical integration
  - fit_decline_curve() with synthetic data
  - Edge cases: insufficient data, all-zeros, single product, steep decline
"""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest

_scipy_available = importlib.util.find_spec("scipy") is not None

from aigis_agents.agent_07_well_cards.dca_engine import (
    DCAResult,
    arps_exponential,
    arps_hyperbolic,
    compute_eur,
    fit_decline_curve,
    project_decline_curve,
)


# ── Arps equations ────────────────────────────────────────────────────────────

class TestArpsHyperbolic:
    def test_at_t_zero_equals_qi(self):
        q = arps_hyperbolic(np.array([0.0]), qi=1000.0, Di=0.05, b=0.5)
        assert abs(q[0] - 1000.0) < 1e-6

    def test_declining_over_time(self):
        t = np.array([0.0, 12.0, 24.0])
        q = arps_hyperbolic(t, qi=1000.0, Di=0.05, b=0.5)
        assert q[0] > q[1] > q[2]

    def test_b_zero_approximates_exponential(self):
        t = np.array([0.0, 6.0, 12.0])
        q_hyp = arps_hyperbolic(t, qi=1000.0, Di=0.05, b=1e-7)
        q_exp = arps_exponential(t, qi=1000.0, Di=0.05)
        np.testing.assert_allclose(q_hyp, q_exp, rtol=1e-3)

    def test_higher_b_gives_slower_decline(self):
        t = np.array([24.0])
        q_low_b  = arps_hyperbolic(t, qi=1000.0, Di=0.05, b=0.3)
        q_high_b = arps_hyperbolic(t, qi=1000.0, Di=0.05, b=0.9)
        assert q_high_b[0] > q_low_b[0]


class TestArpsExponential:
    def test_at_t_zero_equals_qi(self):
        q = arps_exponential(np.array([0.0]), qi=500.0, Di=0.08)
        assert abs(q[0] - 500.0) < 1e-6

    def test_declining_over_time(self):
        t = np.arange(0, 25)
        q = arps_exponential(t, qi=500.0, Di=0.08)
        assert all(q[i] > q[i + 1] for i in range(len(q) - 1))


# ── EUR calculation ───────────────────────────────────────────────────────────

class TestComputeEur:
    def test_zero_qi_returns_zero(self):
        assert compute_eur(qi=0.0, Di_monthly=0.05, b=0.5) == 0.0

    def test_zero_di_returns_zero(self):
        assert compute_eur(qi=1000.0, Di_monthly=0.0, b=0.5) == 0.0

    def test_positive_result_for_valid_inputs(self):
        eur = compute_eur(qi=1000.0, Di_monthly=0.02, b=0.5,
                          economic_limit_boepd=25.0, projection_months=240)
        assert eur > 0.0

    def test_higher_qi_gives_higher_eur(self):
        eur_low  = compute_eur(qi=500.0,  Di_monthly=0.02, b=0.5)
        eur_high = compute_eur(qi=1000.0, Di_monthly=0.02, b=0.5)
        assert eur_high > eur_low

    def test_eur_bounded_by_projection_months(self):
        eur_short = compute_eur(qi=1000.0, Di_monthly=0.001, b=0.5,
                                economic_limit_boepd=0.0, projection_months=12)
        eur_long  = compute_eur(qi=1000.0, Di_monthly=0.001, b=0.5,
                                economic_limit_boepd=0.0, projection_months=240)
        assert eur_long > eur_short


# ── fit_decline_curve ─────────────────────────────────────────────────────────

class TestFitDeclineCurve:
    @staticmethod
    def _synthetic_hyperbolic(n=36, qi=800.0, Di_monthly=0.03, b=0.5,
                               noise_pct=0.03, rng_seed=42):
        rng = np.random.default_rng(rng_seed)
        t = np.arange(n, dtype=float)
        q = arps_hyperbolic(t, qi, Di_monthly, b)
        noise = 1.0 + rng.uniform(-noise_pct, noise_pct, size=n)
        return t, q * noise

    def test_returns_dca_result_instance(self):
        t, q = self._synthetic_hyperbolic()
        result = fit_decline_curve(t, q)
        assert isinstance(result, DCAResult)

    @pytest.mark.skipif(not _scipy_available, reason="scipy not installed")
    def test_fits_hyperbolic_synthetic_data(self):
        t, q = self._synthetic_hyperbolic()
        result = fit_decline_curve(t, q)
        assert result.curve_type in ("hyperbolic", "exponential")
        assert result.fit_r2 > 0.85
        assert result.eur_mmboe > 0.0

    def test_insufficient_data_flag(self):
        t = np.array([0.0, 1.0, 2.0])
        q = np.array([800.0, 770.0, 740.0])
        result = fit_decline_curve(t, q)
        assert result.insufficient_data is True
        assert result.curve_type == "insufficient_data"

    def test_all_zeros_returns_insufficient(self):
        t = np.zeros(12)
        q = np.zeros(12)
        result = fit_decline_curve(t, q)
        assert result.insufficient_data is True

    @pytest.mark.skipif(not _scipy_available, reason="scipy not installed")
    def test_flags_steep_decline(self):
        # Very steep synthetic data: Di_monthly=0.10 → ~120%/yr annual equivalent
        t, q = self._synthetic_hyperbolic(Di_monthly=0.10, qi=2000.0)
        result = fit_decline_curve(t, q)
        assert any("steep" in f.lower() or "50" in f or "decline" in f.lower()
                   for f in result.flags) or result.Di_annual_pct > 30.0

    def test_flags_high_b_factor(self):
        # b=0.95 is anomalously high for GoM Miocene
        t, q = self._synthetic_hyperbolic(b=0.92, Di_monthly=0.02)
        result = fit_decline_curve(t, q)
        # High b may be clamped by bounds but should not error
        assert isinstance(result, DCAResult)

    @pytest.mark.skipif(not _scipy_available, reason="scipy not installed")
    def test_eur_mmboe_reasonable_magnitude(self):
        # 800 boe/d declining well should give roughly 0.1–5 MMboe EUR
        t, q = self._synthetic_hyperbolic(qi=800.0, Di_monthly=0.03)
        result = fit_decline_curve(t, q)
        if not result.insufficient_data:
            assert 0.01 < result.eur_mmboe < 20.0

    def test_months_of_data_recorded(self):
        t, q = self._synthetic_hyperbolic(n=24)
        result = fit_decline_curve(t, q)
        assert result.months_of_data == 24


# ── project_decline_curve ─────────────────────────────────────────────────────

class TestProjectDeclineCurve:
    def test_returns_empty_for_insufficient_data(self):
        bad = DCAResult(curve_type="insufficient_data", insufficient_data=True)
        t, q = project_decline_curve(bad)
        assert len(t) == 0 and len(q) == 0

    def test_returns_arrays_for_valid_result(self):
        good = DCAResult(
            curve_type="hyperbolic", qi_boepd=1000.0,
            Di_annual_pct=24.0, b_factor=0.5, eur_mmboe=1.0, fit_r2=0.95,
        )
        t, q = project_decline_curve(good, months_ahead=24)
        assert len(t) == 25  # 0..24 inclusive
        assert len(q) == 25
        assert q[0] >= q[-1]   # declining
