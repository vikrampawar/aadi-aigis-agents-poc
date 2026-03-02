"""
Tests for Agent 07 — production_processor.py.

Covers:
  - pivot_production()
  - normalize_production() with/without uptime data
  - compute_secondary_metrics() — GOR, WC, 12-month trends
  - compute_summary_stats()
  - extract_cpr_eur()
  - Flag messages for assumption scenarios
"""

from __future__ import annotations

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_records(case="actual", product_rates: dict | None = None,
                  n_months: int = 24) -> list[dict]:
    """
    Build minimal production_series records for n_months months.
    Product names match pivot_production's expected values: "oil", "gas", "water".
    Uses year-aware periods so months 13-24 don't collide with months 1-12.
    """
    if product_rates is None:
        # 800 bopd oil; gas in boe/d (3 MMcfd / 6 mcf:boe × 1000 = 500 boe/d); 100 bwpd water
        product_rates = {"oil": 800.0, "gas": 500.0, "water": 100.0}

    records = []
    for month in range(n_months):
        year = 2022 + month // 12
        mo   = (month % 12) + 1
        period = f"{year}-{mo:02d}-01"
        for product, base_rate in product_rates.items():
            rate = base_rate * (0.98 ** month)
            records.append({
                "period_start": period,
                "product":      product,
                "value_normalised": rate,
                "case_name":    case,
            })
    return records


def _make_reserve_records(p1=0.8, p2=1.2, p3=2.0) -> list[dict]:
    return [
        {"reserve_class": "1P", "product": "boe", "value_normalised": p1,
         "effective_date": "2024-01-01", "reserve_engineer": "Ryder Scott"},
        {"reserve_class": "2P", "product": "boe", "value_normalised": p2,
         "effective_date": "2024-01-01", "reserve_engineer": "Ryder Scott"},
        {"reserve_class": "3P", "product": "boe", "value_normalised": p3,
         "effective_date": "2024-01-01", "reserve_engineer": "Ryder Scott"},
    ]


# ── pivot_production ──────────────────────────────────────────────────────────

class TestPivotProduction:
    def test_returns_dict_keyed_by_period(self):
        from aigis_agents.agent_07_well_cards.production_processor import pivot_production
        records = _make_records()
        result = pivot_production(records)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_period_keys_present(self):
        from aigis_agents.agent_07_well_cards.production_processor import pivot_production
        records = _make_records()
        result = pivot_production(records)
        # Each dict should have both period and period_start keys matching the outer key
        for period, data in result.items():
            assert data.get("period_start") == period
            assert data.get("period") == period

    def test_oil_values_present(self):
        from aigis_agents.agent_07_well_cards.production_processor import pivot_production
        records = _make_records()
        result = pivot_production(records)
        first = next(iter(result.values()))
        assert "oil_bopd" in first
        assert first["oil_bopd"] > 0

    def test_empty_records_returns_empty_dict(self):
        from aigis_agents.agent_07_well_cards.production_processor import pivot_production
        assert pivot_production([]) == {}

    def test_filters_by_case_name(self):
        from aigis_agents.agent_07_well_cards.production_processor import pivot_production
        actual_records = _make_records(case="actual")
        cpr_records    = _make_records(case="cpr_base_case",
                                       product_rates={"oil": 1200.0})
        all_records    = actual_records + cpr_records
        result = pivot_production(all_records, case_name="actual")
        for data in result.values():
            assert data["oil_bopd"] < 1000.0   # actual ~800 not CPR ~1200


# ── normalize_production ──────────────────────────────────────────────────────

class TestNormalizeProduction:
    def test_no_uptime_data_applies_default(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            normalize_production, pivot_production,
        )
        records = _make_records()
        periods_dict = pivot_production(records)
        normalized, flags = normalize_production(periods_dict, default_uptime=90.0)
        # Should have assumption flag
        assert any("assumed" in f.lower() or "default" in f.lower() or "90" in f for f in flags)

    def test_normalized_rate_higher_than_raw(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            normalize_production, pivot_production,
        )
        records = _make_records()
        periods_dict = pivot_production(records)
        normalized, _ = normalize_production(periods_dict, default_uptime=90.0)
        for p in normalized:
            if p.get("oil_bopd", 0) > 0:
                # normalized = actual / 0.90 → should be higher
                assert p.get("oil_norm", 0) >= p.get("oil_bopd", 0)
                break

    def test_100pct_uptime_gives_same_rate(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            normalize_production, pivot_production,
        )
        records = _make_records()
        periods_dict = pivot_production(records)
        normalized, _ = normalize_production(periods_dict, default_uptime=100.0)
        for p in normalized:
            raw_oil  = p.get("oil_bopd", 0) or 0
            norm_oil = p.get("oil_norm", 0) or 0
            # Allow rounding tolerance from round() in normalize_production
            assert abs(raw_oil - norm_oil) < 1.0

    def test_with_actual_uptime_data(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            normalize_production, pivot_production,
        )
        records = _make_records()
        periods_dict = pivot_production(records)
        uptime_data = {p: 85.0 for p in periods_dict}
        normalized, flags = normalize_production(periods_dict, uptime_data=uptime_data)
        # With actual data, assumption flags should be absent or minimal
        assert isinstance(normalized, list)
        assert isinstance(flags, list)

    def test_returns_list_and_flags(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            normalize_production, pivot_production,
        )
        records = _make_records()
        periods_dict = pivot_production(records)
        result, flags = normalize_production(periods_dict)
        assert isinstance(result, list)
        assert isinstance(flags, list)


# ── compute_secondary_metrics ─────────────────────────────────────────────────

class TestComputeSecondaryMetrics:
    def test_computes_gor(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            compute_secondary_metrics, normalize_production, pivot_production,
        )
        records = _make_records()
        periods_dict = pivot_production(records)
        normalized, _ = normalize_production(periods_dict)
        enriched = compute_secondary_metrics(normalized)
        # Some periods should have GOR (where oil > 0 and gas > 0)
        gor_vals = [p.get("gor_scf_stb") for p in enriched if p.get("gor_scf_stb") is not None]
        assert len(gor_vals) > 0
        assert all(v > 0 for v in gor_vals)

    def test_computes_wc(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            compute_secondary_metrics, normalize_production, pivot_production,
        )
        records = _make_records()
        periods_dict = pivot_production(records)
        normalized, _ = normalize_production(periods_dict)
        enriched = compute_secondary_metrics(normalized)
        wc_vals = [p.get("wc_pct") for p in enriched if p.get("wc_pct") is not None]
        assert len(wc_vals) > 0
        assert all(0.0 <= v <= 100.0 for v in wc_vals)

    def test_no_division_by_zero_all_oil(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            compute_secondary_metrics, normalize_production, pivot_production,
        )
        # Oil-only production — no water
        records = _make_records(product_rates={"oil": 800.0})
        periods_dict = pivot_production(records)
        normalized, _ = normalize_production(periods_dict)
        enriched = compute_secondary_metrics(normalized)  # Must not raise
        assert isinstance(enriched, list)

    def test_12mo_trend_requires_12_months(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            compute_secondary_metrics, normalize_production, pivot_production,
        )
        # Only 6 months of data — trend should be None for all periods
        records = _make_records()[:6 * 3]   # 6 months × 3 products
        periods_dict = pivot_production(records)
        normalized, _ = normalize_production(periods_dict)
        enriched = compute_secondary_metrics(normalized)
        gor_trends = [p.get("gor_12m_trend_pct") for p in enriched]
        assert all(v is None for v in gor_trends)


# ── compute_summary_stats ─────────────────────────────────────────────────────

class TestComputeSummaryStats:
    def _enriched(self):
        from aigis_agents.agent_07_well_cards.production_processor import (
            compute_secondary_metrics, normalize_production, pivot_production,
        )
        records = _make_records()
        periods_dict = pivot_production(records)
        normalized, _ = normalize_production(periods_dict)
        return compute_secondary_metrics(normalized)

    def test_current_rate_positive(self):
        from aigis_agents.agent_07_well_cards.production_processor import compute_summary_stats
        stats = compute_summary_stats(self._enriched())
        assert stats.get("current_rate_boepd", 0) > 0

    def test_peak_rate_geq_current(self):
        from aigis_agents.agent_07_well_cards.production_processor import compute_summary_stats
        stats = compute_summary_stats(self._enriched())
        assert stats.get("peak_rate_boepd", 0) >= stats.get("current_rate_boepd", 0)

    def test_cumulative_positive(self):
        from aigis_agents.agent_07_well_cards.production_processor import compute_summary_stats
        stats = compute_summary_stats(self._enriched())
        assert stats.get("cumulative_mmboe", 0) > 0

    def test_empty_periods_returns_defaults(self):
        from aigis_agents.agent_07_well_cards.production_processor import compute_summary_stats
        stats = compute_summary_stats([])
        assert stats.get("current_rate_boepd") is None or stats.get("current_rate_boepd") == 0


# ── extract_cpr_eur ───────────────────────────────────────────────────────────

class TestExtractCprEur:
    def test_extracts_1p_2p_3p(self):
        from aigis_agents.agent_07_well_cards.production_processor import extract_cpr_eur
        records = _make_reserve_records(p1=0.8, p2=1.2, p3=2.0)
        result = extract_cpr_eur(records)
        assert result["1P"] == pytest.approx(0.8, rel=0.01)
        assert result["2P"] == pytest.approx(1.2, rel=0.01)
        assert result["3P"] == pytest.approx(2.0, rel=0.01)

    def test_empty_records(self):
        from aigis_agents.agent_07_well_cards.production_processor import extract_cpr_eur
        result = extract_cpr_eur([])
        assert result.get("1P") is None
        assert result.get("2P") is None

    def test_missing_3p_ok(self):
        from aigis_agents.agent_07_well_cards.production_processor import extract_cpr_eur
        records = [
            {"reserve_class": "1P", "product": "boe", "value_normalised": 0.5,
             "effective_date": "2024-01-01", "reserve_engineer": "RS"},
            {"reserve_class": "2P", "product": "boe", "value_normalised": 1.0,
             "effective_date": "2024-01-01", "reserve_engineer": "RS"},
        ]
        result = extract_cpr_eur(records)
        assert result["2P"] == pytest.approx(1.0)
        assert result.get("3P") is None or result["3P"] is None
