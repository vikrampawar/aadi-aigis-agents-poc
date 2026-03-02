"""
Production data processor for Agent 07.

Queries Agent 02's SQLite database for well-level production history,
reserve estimates, and scalar metrics. Applies downtime normalization
and computes secondary metrics (GOR, WC, trend deltas).
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

# Default GoM uptime assumption when no VDR data is available
DEFAULT_UPTIME_PCT = 90.0


def _db_path(deal_id: str, output_dir: str | Path) -> Path:
    """Resolve path to Agent 02's SQLite data store for a deal."""
    return Path(output_dir) / deal_id / "02_data_store.db"


def _connect(deal_id: str, output_dir: str | Path) -> sqlite3.Connection:
    db = _db_path(deal_id, output_dir)
    if not db.exists():
        raise FileNotFoundError(
            f"Agent 02 data store not found at {db}. "
            "Run Agent 02 (ingest_vdr or ingest_file) for this deal before Agent 07."
        )
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    return conn


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ── Well discovery ────────────────────────────────────────────────────────────

def load_well_names(deal_id: str, output_dir: str | Path) -> list[str]:
    """Return distinct entity_names from production_series for this deal."""
    conn = _connect(deal_id, output_dir)
    try:
        rows = conn.execute(
            "SELECT DISTINCT entity_name FROM production_series "
            "WHERE deal_id=? AND entity_name IS NOT NULL AND entity_name != '' "
            "ORDER BY entity_name",
            (deal_id,),
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


# ── Production series ─────────────────────────────────────────────────────────

def load_production_series(
    deal_id: str,
    well_name: str,
    output_dir: str | Path,
) -> list[dict]:
    """
    Load all production records for a well, all cases, ordered by period_start.

    Returns list of dicts with keys:
      period_start, product, value_normalised, case_name, unit_normalised,
      period_end, confidence, source_page, extraction_note
    """
    conn = _connect(deal_id, output_dir)
    try:
        rows = conn.execute(
            """
            SELECT period_start, period_end, product, value_normalised,
                   unit_normalised, case_name, confidence,
                   source_page, extraction_note
            FROM production_series
            WHERE deal_id=? AND entity_name=?
            ORDER BY period_start ASC, product ASC
            """,
            (deal_id, well_name),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def load_reserve_estimates(
    deal_id: str,
    well_name: str,
    output_dir: str | Path,
) -> list[dict]:
    """
    Load reserve estimate records for a well.

    Returns list of dicts with: reserve_class, product, value_normalised,
    effective_date, report_date, reserve_engineer, source_page.
    """
    conn = _connect(deal_id, output_dir)
    try:
        rows = conn.execute(
            """
            SELECT reserve_class, product, value_normalised, unit_normalised,
                   effective_date, report_date, reserve_engineer,
                   source_section, source_page, confidence
            FROM reserve_estimates
            WHERE deal_id=? AND entity_name=?
            ORDER BY reserve_class ASC
            """,
            (deal_id, well_name),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def load_scalar_metrics(
    deal_id: str,
    well_name: str,
    output_dir: str | Path,
) -> dict[str, float]:
    """
    Load one-off scalar metrics for a well from scalar_datapoints.

    Looks for metric_names/keys containing the well_name or standard well metric names.
    Returns dict of {metric_name: value}.
    """
    conn = _connect(deal_id, output_dir)
    try:
        rows = conn.execute(
            """
            SELECT metric_name, metric_key, value, unit, as_of_date
            FROM scalar_datapoints
            WHERE deal_id=?
              AND (
                LOWER(metric_key) LIKE ?
                OR LOWER(context) LIKE ?
                OR LOWER(extraction_note) LIKE ?
              )
            """,
            (deal_id, f"%{well_name.lower()}%", f"%{well_name.lower()}%", f"%{well_name.lower()}%"),
        ).fetchall()
        result: dict[str, float] = {}
        for r in rows:
            try:
                result[r["metric_name"]] = float(r["value"])
            except (TypeError, ValueError):
                pass
        return result
    finally:
        conn.close()


# ── Production pivot ──────────────────────────────────────────────────────────

def pivot_production(
    records: list[dict],
    case_name: str | None = None,
) -> dict[str, dict]:
    """
    Pivot production records into a per-period dict keyed by period_start.

    Each entry: {oil_bopd, gas_mmcfd, water_bwpd, boe_boepd, case_name}

    If case_name is provided, filters to that case. If None, uses the first
    case that looks like actual production (no 'forecast', 'cpr', 'case' in name).
    """
    # Identify actual-production case: prefer entries without a case name
    # or with case_name containing 'actual' — fall back to first available case
    if case_name is None:
        available_cases = sorted({r["case_name"] for r in records if r.get("case_name")})
        # Prefer case names that suggest actuals
        actual_hints = ("actual", "hist", "reported", "measured")
        actuals = [c for c in available_cases if any(h in (c or "").lower() for h in actual_hints)]
        if actuals:
            case_name = actuals[0]
        elif available_cases:
            # Use first non-forecast case
            non_forecast = [c for c in available_cases
                            if not any(h in (c or "").lower()
                                       for h in ("cpr", "forecast", "management", "case", "projection"))]
            case_name = non_forecast[0] if non_forecast else available_cases[0]

    filtered = [r for r in records if r.get("case_name") == case_name]

    # Group by period
    periods: dict[str, dict] = {}
    for r in filtered:
        p = r["period_start"]
        if p not in periods:
            periods[p] = {
                "period":      p,           # convenience alias = period_start
                "period_start": p,
                "period_end": r.get("period_end", p),
                "case_name": case_name,
                "oil_bopd": 0.0,
                "gas_mmcfd": 0.0,
                "water_bwpd": 0.0,
                "boe_boepd": 0.0,
            }
        product = (r.get("product") or "").lower()
        val = float(r.get("value_normalised") or 0.0)
        if product in ("oil", "condensate"):
            periods[p]["oil_bopd"] += val
        elif product in ("gas", "gas_mcfd"):
            # value_normalised in boe already (Agent 02 normalises to boe)
            # But we also want raw gas in mmcfd for GOR — approximate from boe
            periods[p]["gas_mmcfd"] += val / 6000.0  # 6 mcf:1 boe → mmcfd
            periods[p]["boe_boepd"] += val
        elif product in ("water", "ngl"):
            periods[p]["water_bwpd"] += val
        elif product in ("boe", "boepd"):
            periods[p]["boe_boepd"] += val

    # Fill boe where not explicit
    for p in periods:
        if periods[p]["boe_boepd"] == 0.0:
            periods[p]["boe_boepd"] = (
                periods[p]["oil_bopd"]
                + periods[p]["gas_mmcfd"] * 6000.0
            )

    return dict(sorted(periods.items()))


def pivot_forecast(
    records: list[dict],
    forecast_case: str = "cpr_base_case",
) -> dict[str, dict]:
    """
    Pivot CPR forecast production by period.

    Similar to pivot_production but targets the forecast_case.
    """
    return pivot_production(records, case_name=forecast_case)


# ── Downtime normalization ────────────────────────────────────────────────────

def normalize_production(
    periods: dict[str, dict],
    uptime_data: dict[str, float] | None = None,
    default_uptime: float = DEFAULT_UPTIME_PCT,
) -> tuple[list[dict], list[str]]:
    """
    Apply uptime normalization: rate_normalized = rate_actual / uptime_factor.

    Args:
        periods:      dict from pivot_production() — keyed by period_start.
        uptime_data:  Optional {period_start: uptime_pct} from VDR data.
        default_uptime: GoM benchmark uptime % to assume if no VDR data.

    Returns:
        (normalized_periods, assumption_flags)
        normalized_periods is a list[dict] sorted by period, each dict includes:
          period, oil_norm, gas_norm, water_norm, boe_norm, uptime_factor, uptime_source.
    """
    flags: list[str] = []
    uptime_frac = default_uptime / 100.0
    normalized_list: list[dict] = []
    assumed_count = 0

    for period in sorted(periods.keys()):
        data = periods[period]
        entry = dict(data)
        entry["period"] = period  # ensure accessible as .get("period")

        if uptime_data and period in uptime_data:
            factor = uptime_data[period] / 100.0
            source = "actual"
        else:
            factor = uptime_frac
            source = "assumed"
            assumed_count += 1

        factor = max(factor, 0.01)  # avoid division by zero
        entry["uptime_factor"] = round(factor, 4)
        entry["uptime_source"] = source
        entry["boe_norm"]   = round(entry["boe_boepd"]   / factor, 1)
        entry["oil_norm"]   = round(entry["oil_bopd"]    / factor, 1)
        entry["gas_norm"]   = round(entry["gas_mmcfd"]   / factor, 4)
        entry["water_norm"] = round(entry["water_bwpd"]  / factor, 1)
        normalized_list.append(entry)

    if assumed_count > 0 and uptime_data is None:
        flags.append(
            f"No uptime data found in VDR — {default_uptime:.0f}% uptime assumed for all "
            f"{assumed_count} periods (GoM subsea tie-back benchmark; actual 88–92%)"
        )
    elif assumed_count > 0:
        flags.append(
            f"Uptime data absent for {assumed_count} periods — {default_uptime:.0f}% assumed"
        )

    return normalized_list, flags


# ── Secondary metrics ─────────────────────────────────────────────────────────

def compute_secondary_metrics(periods: list[dict] | dict) -> list[dict]:
    """
    Add GOR and WC columns to normalized periods.
    Add 12-month trend for GOR and WC (delta vs. 12 months prior).

    Accepts either a list[dict] (from normalize_production) or a legacy dict[str,dict].
    Returns list[dict] sorted by period, each entry with "period" key.

    GOR (scf/stb) = gas_norm_mmcfd * 1_000_000 / oil_norm_bopd
    WC% = water_norm / (water_norm + oil_norm) * 100
    """
    # Normalise input to list[dict]
    if isinstance(periods, dict):
        period_list = [dict(v, period=k) for k, v in sorted(periods.items())]
    else:
        period_list = sorted(periods, key=lambda p: p.get("period", p.get("period_start", "")))

    result: list[dict] = []

    for i, raw in enumerate(period_list):
        entry = dict(raw)
        # Ensure period key present
        if "period" not in entry:
            entry["period"] = entry.get("period_start", str(i))

        oil   = entry.get("oil_norm",   entry.get("oil_bopd",   0.0)) or 0.0
        gas   = entry.get("gas_norm",   entry.get("gas_mmcfd",  0.0)) or 0.0
        water = entry.get("water_norm", entry.get("water_bwpd", 0.0)) or 0.0

        # GOR in scf/stb
        entry["gor_scf_stb"] = round(gas * 1_000_000 / oil, 0) if oil > 0 else None

        # Water cut %
        total_liquids = oil + water
        entry["wc_pct"] = round(water / total_liquids * 100, 2) if total_liquids > 0 else 0.0

        # 12-month trends
        entry["gor_12m_trend_pct"]  = None
        entry["wc_12m_trend_ppts"]  = None
        if i >= 12:
            prior = result[i - 12]
            if prior.get("gor_scf_stb") and entry.get("gor_scf_stb"):
                entry["gor_12m_trend_pct"] = round(
                    (entry["gor_scf_stb"] - prior["gor_scf_stb"]) / prior["gor_scf_stb"] * 100, 1
                )
            if prior.get("wc_pct") is not None and entry.get("wc_pct") is not None:
                entry["wc_12m_trend_ppts"] = round(entry["wc_pct"] - prior["wc_pct"], 2)

        result.append(entry)

    return result


# ── Summary statistics ────────────────────────────────────────────────────────

def compute_summary_stats(periods: list[dict] | dict) -> dict:
    """
    Compute well-level summary statistics from normalized period data.

    Accepts list[dict] (from compute_secondary_metrics) or legacy dict[str,dict].
    Returns dict with: current_rate_boepd, peak_rate_boepd, cumulative_mmboe,
    ip30_boepd, ip90_boepd, ip180_boepd, trend_12m_pct, gor_scf_stb (latest),
    gor_trend_12m_pct, water_cut_pct, wc_trend_12m_ppts,
    months_of_data, completeness_pct.
    """
    if not periods:
        return {"months_of_data": 0, "completeness_pct": 0.0,
                "current_rate_boepd": None, "peak_rate_boepd": None, "cumulative_mmboe": 0.0}

    # Normalise to list
    if isinstance(periods, dict):
        period_list = [dict(v) for _, v in sorted(periods.items())]
    else:
        period_list = list(periods)

    boe_rates = [p.get("boe_norm", p.get("boe_boepd", 0.0)) or 0.0 for p in period_list]
    boe_arr = np.array(boe_rates, dtype=float)

    current_rate = float(boe_arr[-1]) if len(boe_arr) else 0.0
    peak_rate    = float(np.max(boe_arr)) if len(boe_arr) else 0.0

    # Cumulative production (sum of monthly averages × 30.44 days/month)
    cumulative_boe = float(np.sum(boe_arr) * 30.44)

    # IP metrics (average rate over first N calendar months, using only producing periods)
    def _ip(n: int) -> float | None:
        if len(boe_arr) < n:
            return None
        window = boe_arr[:n]
        nonzero = window[window > 0]
        return round(float(np.mean(nonzero)), 1) if len(nonzero) else None

    ip30  = _ip(1)   # 1 month ≈ IP30
    ip90  = _ip(3)   # 3 months ≈ IP90
    ip180 = _ip(6)   # 6 months ≈ IP180

    # 12-month rate trend
    trend_12m_pct = None
    if len(boe_arr) >= 13:
        rate_12m_ago = float(boe_arr[-13]) if boe_arr[-13] > 0 else None
        if rate_12m_ago and rate_12m_ago > 0:
            trend_12m_pct = round((current_rate - rate_12m_ago) / rate_12m_ago * 100, 1)

    # Latest GOR, WC and their 12m trends
    latest = period_list[-1]

    # Completeness
    total_possible = len(period_list)
    non_zero = sum(1 for p in period_list
                   if (p.get("boe_norm") or p.get("boe_boepd") or 0) > 0)
    completeness = round(non_zero / total_possible * 100, 1) if total_possible else 0.0

    # Average uptime
    uptime_factors = [p.get("uptime_factor", 0.9) for p in period_list]
    avg_uptime_pct = round(float(np.mean(uptime_factors)) * 100, 1)
    uptime_sources = [p.get("uptime_source", "assumed") for p in period_list]
    uptime_source = "actual" if all(s == "actual" for s in uptime_sources) else "assumed"

    return {
        "current_rate_boepd":   round(current_rate, 1),
        "peak_rate_boepd":      round(peak_rate, 1),
        "cumulative_mmboe":     round(cumulative_boe / 1e6, 3),
        "ip30_boepd":           ip30,
        "ip90_boepd":           ip90,
        "ip180_boepd":          ip180,
        "trend_12m_pct":        trend_12m_pct,
        "gor_scf_stb":          latest.get("gor_scf_stb"),
        "gor_trend_12m_pct":    latest.get("gor_12m_trend_pct"),
        "water_cut_pct":        latest.get("wc_pct"),
        "wc_trend_12m_ppts":    latest.get("wc_12m_trend_ppts"),
        "uptime_pct":           avg_uptime_pct,
        "uptime_source":        uptime_source,
        "months_of_data":       total_possible,
        "completeness_pct":     completeness,
    }


# ── CPR EUR extraction ────────────────────────────────────────────────────────

def extract_cpr_eur(reserve_records: list[dict]) -> dict:
    """
    Extract CPR EUR from reserve_estimates records.

    Returns dict: {1P: float|None, 2P: float|None, 3P: float|None, source: str|None}
    Prefers most recent report_date; aggregates across oil/gas/NGL into BOE total.
    """
    result: dict = {"1P": None, "2P": None, "3P": None, "source": None, "effective_date": None}
    if not reserve_records:
        return result

    # Group by reserve_class, sum value_normalised.
    # Reserve estimates are stored in their natural unit (MMboe by convention in Agent 02);
    # production data is boe/d but reserve estimates are not converted further.
    for cls in ("2P", "1P", "3P", "PDP", "PNP"):
        recs = [r for r in reserve_records if r.get("reserve_class") == cls]
        if recs:
            total = sum(float(r.get("value_normalised") or 0.0) for r in recs)
            # If unit indicates boe (not MMboe), convert; otherwise keep as-is
            unit = (recs[0].get("unit_normalised") or recs[0].get("unit") or "MMboe").lower()
            if "mmboe" in unit or "mmb" in unit:
                result[cls] = round(total, 3)
            else:
                # Assume boe → convert to MMboe
                result[cls] = round(total / 1e6, 3)
            if result["source"] is None:
                result["source"] = recs[0].get("reserve_engineer") or recs[0].get("source_section")
                result["effective_date"] = recs[0].get("effective_date")

    return result
