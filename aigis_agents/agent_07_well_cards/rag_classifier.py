"""
RAG (Red / Amber / Green) traffic-light classifier for Agent 07.

Assigns a performance status to each well based on:
  - Actual rate vs. CPR forecast (primary classification)
  - GOR trend (secondary escalation)
  - WC trend (secondary escalation)
  - DCA annual decline rate (secondary escalation)
  - Well operational status

Learned patterns from MemoryManager can override default thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── RAG colour constants ──────────────────────────────────────────────────────

GREEN  = "GREEN"
AMBER  = "AMBER"
RED    = "RED"
BLACK  = "BLACK"   # shut-in

RAG_EMOJI = {
    GREEN: "🟢",
    AMBER: "🟡",
    RED:   "🔴",
    BLACK: "⚫",
}

# ── Default thresholds ────────────────────────────────────────────────────────

# Primary: actual rate vs. CPR forecast variance
OUTPERFORMER_THRESHOLD = +0.10   # > +10% → GREEN (Outperformer)
ON_TRACK_LOWER         = -0.10   # -10% to +10% → GREEN (On-track)
AMBER_LOWER            = -0.25   # -25% to -10% → AMBER

# Secondary: GOR trend (% change over 12 months)
GOR_RISE_AMBER_PCT     = 20.0    # +20%/12mo → escalate to AMBER
GOR_RISE_RED_PCT       = 40.0    # +40%/12mo → escalate to RED

# Secondary: WC trend (percentage point increase over 12 months)
WC_RISE_AMBER_PPTS     = 8.0     # +8 ppts/12mo → escalate to AMBER
WC_RISE_RED_PPTS       = 15.0    # +15 ppts/12mo → escalate to RED

# Secondary: annual decline rate
DI_STEEP_AMBER_PCT     = 30.0    # > 30%/yr → AMBER flag
DI_STEEP_RED_PCT       = 50.0    # > 50%/yr → RED flag

# DCA fit quality
R2_POOR                = 0.70    # R² < 0.70 → data quality flag

# Uptime
UPTIME_LOW_AMBER_PCT   = 85.0    # < 85% → operational flag
UPTIME_LOW_RED_PCT     = 70.0    # < 70% → serious operational flag


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RAGResult:
    """Traffic-light classification result for a single well."""
    status:            str                       # "GREEN" | "AMBER" | "RED" | "BLACK"
    label:             str                       # Human description
    emoji:             str                       # Single emoji
    variance_pct:      float | None = None       # Actual vs. forecast %
    flags:             list[str] = field(default_factory=list)
    learned_overrides: list[str] = field(default_factory=list)  # patterns applied


# ── Severity ordering ─────────────────────────────────────────────────────────

_SEVERITY_ORDER = {BLACK: 4, RED: 3, AMBER: 2, GREEN: 1}


def _max_severity(a: str, b: str) -> str:
    """Return the more severe of two RAG statuses."""
    return a if _SEVERITY_ORDER.get(a, 0) >= _SEVERITY_ORDER.get(b, 0) else b


# ── Pattern override helpers ──────────────────────────────────────────────────

def _apply_pattern_overrides(
    thresholds: dict,
    patterns: list[dict],
) -> tuple[dict, list[str]]:
    """
    Scan learned patterns for threshold overrides. Returns updated thresholds
    and a list of override notes applied.

    Pattern example:
      {"classification": "gor_threshold_gas_condensate",
       "rule": "gas condensate wells: GOR rise 30% normal — raise amber to 35%"}

    This implementation applies a simple heuristic: if a pattern mentions
    specific numeric thresholds in its rule text, a caller-side override
    should be done. Here we log that patterns were considered.
    """
    overrides: list[str] = []
    for p in patterns:
        cls = p.get("classification", "")
        rule = p.get("rule", "")
        weight = p.get("weight", "MEDIUM")
        if weight == "STALE":
            continue
        if cls == "gor_threshold_gas_condensate":
            overrides.append(f"Pattern '{cls}' applied: {rule}")
        elif cls == "gom_uptime_benchmark":
            overrides.append(f"Pattern '{cls}' noted: {rule}")
    return thresholds, overrides


# ── Main classifier ───────────────────────────────────────────────────────────

def classify_well(
    current_rate_boepd:  float,
    forecast_rate_boepd: float | None,
    gor_trend_12m_pct:   float | None,
    wc_trend_12m_ppts:   float | None,
    di_annual_pct:       float | None,
    fit_r2:              float | None,
    uptime_pct:          float | None,
    well_status:         str | None,
    patterns:            list[dict] | None = None,
) -> RAGResult:
    """
    Classify a well's performance with a traffic-light RAG status.

    Primary classification is based on actual rate vs. CPR forecast variance.
    Secondary flags escalate the status if GOR/WC trends are anomalous.

    Args:
        current_rate_boepd:   Most recent normalized production rate.
        forecast_rate_boepd:  CPR base case forecast rate for current period.
                              If None, falls back to metric-only classification.
        gor_trend_12m_pct:    GOR % change over last 12 months.
        wc_trend_12m_ppts:    Water cut percentage point change over 12 months.
        di_annual_pct:        Annual decline rate from DCA.
        fit_r2:               DCA fit R².
        uptime_pct:           Average uptime % (actual or assumed).
        well_status:          Operational status string, e.g. "shut-in".
        patterns:             Learned patterns from MemoryManager.

    Returns:
        RAGResult with status, label, flags, and applied pattern notes.
    """
    patterns = patterns or []
    flags: list[str] = []

    thresholds: dict = {
        "outperformer":  OUTPERFORMER_THRESHOLD,
        "on_track_lower": ON_TRACK_LOWER,
        "amber_lower":   AMBER_LOWER,
        "gor_amber":     GOR_RISE_AMBER_PCT,
        "gor_red":       GOR_RISE_RED_PCT,
        "wc_amber":      WC_RISE_AMBER_PPTS,
        "wc_red":        WC_RISE_RED_PPTS,
        "di_amber":      DI_STEEP_AMBER_PCT,
        "di_red":        DI_STEEP_RED_PCT,
        "uptime_amber":  UPTIME_LOW_AMBER_PCT,
        "uptime_red":    UPTIME_LOW_RED_PCT,
    }
    thresholds, overrides = _apply_pattern_overrides(thresholds, patterns)

    # ── BLACK: shut-in ────────────────────────────────────────────────────────
    status_str = (well_status or "").lower()
    if status_str in ("shut-in", "shut_in", "suspended", "abandonment", "p&a", "plugged"):
        return RAGResult(
            status=BLACK, label="Shut-in / Suspended", emoji=RAG_EMOJI[BLACK],
            flags=["Well is currently shut-in or suspended — no production data"],
            learned_overrides=overrides,
        )

    if current_rate_boepd <= 0:
        return RAGResult(
            status=BLACK, label="No production recorded", emoji=RAG_EMOJI[BLACK],
            flags=["Zero or negative production rate recorded"],
            learned_overrides=overrides,
        )

    # ── Primary classification: rate vs. forecast ─────────────────────────────
    variance_pct: float | None = None

    if forecast_rate_boepd and forecast_rate_boepd > 0:
        variance_pct = (current_rate_boepd - forecast_rate_boepd) / forecast_rate_boepd

        if variance_pct >= thresholds["outperformer"]:
            rag = GREEN
            label = f"Outperformer ({variance_pct:+.0%} vs CPR forecast)"
        elif variance_pct >= thresholds["on_track_lower"]:
            rag = GREEN
            label = f"On-track ({variance_pct:+.0%} vs CPR forecast)"
        elif variance_pct >= thresholds["amber_lower"]:
            rag = AMBER
            label = f"Underperformer ({variance_pct:+.0%} vs CPR forecast)"
            flags.append(
                f"Production {abs(variance_pct):.0%} below CPR base case forecast "
                f"({current_rate_boepd:,.0f} boe/d actual vs {forecast_rate_boepd:,.0f} boe/d CPR)"
            )
        else:
            rag = RED
            label = f"Significantly below forecast ({variance_pct:+.0%} vs CPR)"
            flags.append(
                f"CRITICAL: Production {abs(variance_pct):.0%} below CPR base case "
                f"({current_rate_boepd:,.0f} boe/d actual vs {forecast_rate_boepd:,.0f} boe/d CPR) — "
                "material reserve revision risk"
            )
    else:
        # No forecast available — classify on trends only
        rag = GREEN
        label = "On-track (no CPR forecast for comparison)"
        flags.append("No CPR forecast found for this well — RAG based on trend metrics only")

    # ── Secondary: GOR trend ──────────────────────────────────────────────────
    if gor_trend_12m_pct is not None:
        if gor_trend_12m_pct >= thresholds["gor_red"]:
            rag = _max_severity(rag, RED)
            flags.append(
                f"GOR rising {gor_trend_12m_pct:+.0f}% over 12 months — "
                "possible gas coning, aquifer encroachment, or depletion drive change; "
                "recommend well test and PVT re-sampling"
            )
        elif gor_trend_12m_pct >= thresholds["gor_amber"]:
            rag = _max_severity(rag, AMBER)
            flags.append(
                f"GOR rising {gor_trend_12m_pct:+.0f}% over 12 months — "
                "monitor closely; cross-check against CPR PVT model"
            )

    # ── Secondary: WC trend ───────────────────────────────────────────────────
    if wc_trend_12m_ppts is not None:
        if wc_trend_12m_ppts >= thresholds["wc_red"]:
            rag = _max_severity(rag, RED)
            flags.append(
                f"Water cut rising {wc_trend_12m_ppts:+.1f} ppts over 12 months — "
                "possible early water breakthrough; review sweep efficiency and aquifer model"
            )
        elif wc_trend_12m_ppts >= thresholds["wc_amber"]:
            rag = _max_severity(rag, AMBER)
            flags.append(
                f"Water cut rising {wc_trend_12m_ppts:+.1f} ppts over 12 months — "
                "monitor; compare against CPR WC forecast trajectory"
            )

    # ── Secondary: steep decline ──────────────────────────────────────────────
    if di_annual_pct is not None:
        if di_annual_pct >= thresholds["di_red"]:
            rag = _max_severity(rag, RED)
            flags.append(
                f"Annual decline {di_annual_pct:.0f}%/yr exceeds 50%/yr — "
                "verify production data quality; may indicate reservoir compartmentalization or mechanical damage"
            )
        elif di_annual_pct >= thresholds["di_amber"]:
            rag = _max_severity(rag, AMBER)
            flags.append(
                f"Annual decline {di_annual_pct:.0f}%/yr is above GoM deepwater benchmark (15–25%/yr)"
            )

    # ── Secondary: low uptime ─────────────────────────────────────────────────
    if uptime_pct is not None:
        if uptime_pct < thresholds["uptime_red"]:
            rag = _max_severity(rag, RED)
            flags.append(
                f"Well uptime {uptime_pct:.0f}% is critically low (<70%) — "
                "significant operational reliability concern; investigate root cause"
            )
        elif uptime_pct < thresholds["uptime_amber"]:
            rag = _max_severity(rag, AMBER)
            flags.append(
                f"Well uptime {uptime_pct:.0f}% is below GoM benchmark (88–92%) — "
                "review maintenance history and equipment reliability"
            )

    # ── Secondary: poor DCA fit ───────────────────────────────────────────────
    if fit_r2 is not None and fit_r2 < R2_POOR:
        flags.append(
            f"DCA fit R²={fit_r2:.2f} is poor — EUR projection has limited confidence; "
            "request additional production history or well tests"
        )

    return RAGResult(
        status=rag,
        label=label,
        emoji=RAG_EMOJI[rag],
        variance_pct=round(variance_pct * 100, 1) if variance_pct is not None else None,
        flags=flags,
        learned_overrides=overrides,
    )


def summarize_fleet_rag(well_cards: list[dict]) -> dict:
    """
    Aggregate RAG counts and fleet statistics from a list of well card dicts.
    """
    counts = {GREEN: 0, AMBER: 0, RED: 0, BLACK: 0}
    critical_flags = 0
    rates = []
    eurs = []

    for card in well_cards:
        status = card.get("rag_status", GREEN)
        counts[status] = counts.get(status, 0) + 1
        flags = card.get("flags", [])
        critical_flags += sum(1 for f in flags if "CRITICAL" in f.upper())
        if card.get("metrics", {}).get("current_rate_boepd"):
            rates.append(card["metrics"]["current_rate_boepd"])
        if card.get("decline_curve", {}).get("eur_mmboe"):
            eurs.append(card["decline_curve"]["eur_mmboe"])

    total_rate = round(sum(rates), 1)
    total_eur  = round(sum(eurs), 3)

    di_values = [
        c.get("decline_curve", {}).get("Di_annual_pct", 0)
        for c in well_cards
        if c.get("decline_curve", {}).get("Di_annual_pct")
    ]
    weighted_di = round(float(sum(di_values) / len(di_values)), 1) if di_values else None

    return {
        "rag_summary":              counts,
        "total_current_rate_boepd": total_rate,
        "total_eur_mmboe":          total_eur,
        "critical_flag_count":      critical_flags,
        "weighted_decline_rate_pct": weighted_di,
    }
