"""
Tests for Agent 07 — RAG classifier (rag_classifier.py).

Covers:
  - Primary classification matrix (GREEN / AMBER / RED / BLACK)
  - Secondary flag escalation (GOR, WC, DI, uptime)
  - Pattern overrides (_apply_pattern_overrides)
  - summarize_fleet_rag fleet aggregation
"""

from __future__ import annotations

import pytest

from aigis_agents.agent_07_well_cards.rag_classifier import (
    AMBER,
    BLACK,
    GREEN,
    RED,
    RAGResult,
    classify_well,
    summarize_fleet_rag,
    _apply_pattern_overrides,
)


# ── Shared helper ─────────────────────────────────────────────────────────────

def _classify(
    current=1000.0,
    forecast=1000.0,
    gor_trend=None,
    wc_trend=None,
    di_annual=None,
    fit_r2=None,
    uptime=None,
    well_status="producing",
    patterns=None,
) -> RAGResult:
    return classify_well(
        current_rate_boepd  = current,
        forecast_rate_boepd = forecast,
        gor_trend_12m_pct   = gor_trend,
        wc_trend_12m_ppts   = wc_trend,
        di_annual_pct       = di_annual,
        fit_r2              = fit_r2,
        uptime_pct          = uptime,
        well_status         = well_status,
        patterns            = patterns or [],
    )


# ── BLACK: shut-in ────────────────────────────────────────────────────────────

class TestBlackStatus:
    @pytest.mark.parametrize("status", ["shut-in", "shut_in", "suspended", "p&a", "plugged"])
    def test_shut_in_statuses_return_black(self, status):
        r = _classify(well_status=status)
        assert r.status == BLACK

    def test_zero_rate_returns_black(self):
        r = _classify(current=0.0, forecast=1000.0)
        assert r.status == BLACK

    def test_negative_rate_returns_black(self):
        r = _classify(current=-50.0, forecast=1000.0)
        assert r.status == BLACK

    def test_black_has_emoji(self):
        r = _classify(well_status="shut-in")
        assert r.emoji == "⚫"


# ── Primary classification ────────────────────────────────────────────────────

class TestPrimaryClassification:
    def test_outperformer_green(self):
        # +15% vs forecast → GREEN Outperformer
        r = _classify(current=1150.0, forecast=1000.0)
        assert r.status == GREEN
        assert "Outperformer" in r.label

    def test_on_track_green(self):
        # +5% vs forecast → GREEN On-track
        r = _classify(current=1050.0, forecast=1000.0)
        assert r.status == GREEN
        assert "On-track" in r.label

    def test_slight_miss_green(self):
        # -8% → still GREEN (within ±10%)
        r = _classify(current=920.0, forecast=1000.0)
        assert r.status == GREEN

    def test_amber_lower_bound(self):
        # -11% → AMBER
        r = _classify(current=890.0, forecast=1000.0)
        assert r.status == AMBER

    def test_amber_upper_bound(self):
        # -24% → AMBER
        r = _classify(current=760.0, forecast=1000.0)
        assert r.status == AMBER

    def test_red_below_threshold(self):
        # -30% → RED
        r = _classify(current=700.0, forecast=1000.0)
        assert r.status == RED

    def test_no_forecast_defaults_green(self):
        r = _classify(current=1000.0, forecast=None)
        assert r.status == GREEN
        assert any("no cpr forecast" in f.lower() for f in r.flags)

    def test_variance_pct_stored_correctly(self):
        r = _classify(current=1100.0, forecast=1000.0)
        assert r.variance_pct is not None
        assert abs(r.variance_pct - 10.0) < 0.01


# ── Secondary: GOR escalation ────────────────────────────────────────────────

class TestGorEscalation:
    def test_high_gor_escalates_green_to_red(self):
        r = _classify(current=1000.0, forecast=1000.0, gor_trend=45.0)
        assert r.status == RED

    def test_moderate_gor_escalates_green_to_amber(self):
        r = _classify(current=1000.0, forecast=1000.0, gor_trend=25.0)
        assert r.status == AMBER

    def test_low_gor_does_not_escalate(self):
        r = _classify(current=1000.0, forecast=1000.0, gor_trend=10.0)
        assert r.status == GREEN

    def test_gor_cannot_improve_existing_red(self):
        r_no_gor  = _classify(current=600.0, forecast=1000.0)
        r_with_gor = _classify(current=600.0, forecast=1000.0, gor_trend=5.0)
        assert r_with_gor.status == RED  # already RED; mild GOR doesn't help or hurt


# ── Secondary: WC escalation ─────────────────────────────────────────────────

class TestWcEscalation:
    def test_high_wc_trend_escalates_to_red(self):
        r = _classify(current=1000.0, forecast=1000.0, wc_trend=20.0)
        assert r.status == RED

    def test_moderate_wc_trend_escalates_to_amber(self):
        r = _classify(current=1000.0, forecast=1000.0, wc_trend=10.0)
        assert r.status == AMBER

    def test_low_wc_trend_no_escalation(self):
        r = _classify(current=1000.0, forecast=1000.0, wc_trend=3.0)
        assert r.status == GREEN


# ── Secondary: decline rate escalation ───────────────────────────────────────

class TestDeclineEscalation:
    def test_very_steep_decline_escalates_to_red(self):
        r = _classify(current=1000.0, forecast=1000.0, di_annual=60.0)
        assert r.status == RED

    def test_steep_decline_escalates_to_amber(self):
        r = _classify(current=1000.0, forecast=1000.0, di_annual=35.0)
        assert r.status == AMBER

    def test_normal_decline_no_escalation(self):
        r = _classify(current=1000.0, forecast=1000.0, di_annual=20.0)
        assert r.status == GREEN


# ── Secondary: uptime ─────────────────────────────────────────────────────────

class TestUptimeEscalation:
    def test_critically_low_uptime_red(self):
        r = _classify(current=1000.0, forecast=1000.0, uptime=65.0)
        assert r.status == RED

    def test_low_uptime_amber(self):
        r = _classify(current=1000.0, forecast=1000.0, uptime=80.0)
        assert r.status == AMBER

    def test_good_uptime_no_escalation(self):
        r = _classify(current=1000.0, forecast=1000.0, uptime=92.0)
        assert r.status == GREEN


# ── DCA R² flag (no status change) ───────────────────────────────────────────

class TestR2Flag:
    def test_poor_r2_adds_flag_but_no_escalation(self):
        r = _classify(current=1000.0, forecast=1000.0, fit_r2=0.60)
        # R² alone does not escalate RAG status
        assert r.status == GREEN
        assert any("R²" in f or "r2" in f.lower() or "r²" in f.lower() for f in r.flags)


# ── Pattern overrides ─────────────────────────────────────────────────────────

class TestPatternOverrides:
    def test_stale_pattern_ignored(self):
        patterns = [{"classification": "gor_threshold_gas_condensate",
                     "rule": "GOR 30% normal", "weight": "STALE"}]
        _, overrides = _apply_pattern_overrides({}, patterns)
        assert overrides == []

    def test_valid_pattern_noted(self):
        patterns = [{"classification": "gor_threshold_gas_condensate",
                     "rule": "GOR rising 30%/yr is normal for gas condensate", "weight": "MEDIUM"}]
        _, overrides = _apply_pattern_overrides({}, patterns)
        assert len(overrides) == 1
        assert "gor_threshold_gas_condensate" in overrides[0]

    def test_gom_uptime_benchmark_noted(self):
        patterns = [{"classification": "gom_uptime_benchmark",
                     "rule": "88–92% uptime typical GoM subsea", "weight": "HIGH"}]
        _, overrides = _apply_pattern_overrides({}, patterns)
        assert any("gom_uptime_benchmark" in o for o in overrides)

    def test_classify_well_propagates_overrides(self):
        patterns = [{"classification": "gor_threshold_gas_condensate",
                     "rule": "GOR condensate rule", "weight": "MEDIUM"}]
        r = _classify(patterns=patterns)
        assert any("gor_threshold_gas_condensate" in o for o in r.learned_overrides)


# ── summarize_fleet_rag ───────────────────────────────────────────────────────

class TestSummarizeFleetRag:
    @staticmethod
    def _make_cards(statuses: list[str]) -> list[dict]:
        return [
            {
                "rag_status": s,
                "flags": ["CRITICAL: something bad"] if s == RED else [],
                "metrics": {"current_rate_boepd": 1000.0},
                "decline_curve": {"eur_mmboe": 1.0, "Di_annual_pct": 20.0},
            }
            for s in statuses
        ]

    def test_counts_correct(self):
        cards = self._make_cards([GREEN, GREEN, AMBER, RED, BLACK])
        summary = summarize_fleet_rag(cards)
        assert summary["rag_summary"][GREEN]  == 2
        assert summary["rag_summary"][AMBER]  == 1
        assert summary["rag_summary"][RED]    == 1
        assert summary["rag_summary"][BLACK]  == 1

    def test_total_rate(self):
        cards = self._make_cards([GREEN, GREEN])
        summary = summarize_fleet_rag(cards)
        assert summary["total_current_rate_boepd"] == pytest.approx(2000.0, rel=0.01)

    def test_total_eur(self):
        cards = self._make_cards([GREEN, AMBER, RED])
        summary = summarize_fleet_rag(cards)
        assert summary["total_eur_mmboe"] == pytest.approx(3.0, rel=0.01)

    def test_critical_flag_count(self):
        cards = self._make_cards([GREEN, RED, RED])
        summary = summarize_fleet_rag(cards)
        assert summary["critical_flag_count"] == 2

    def test_empty_fleet(self):
        summary = summarize_fleet_rag([])
        assert summary["total_current_rate_boepd"] == 0.0
        assert summary["rag_summary"][GREEN] == 0
