"""
Decline Curve Analysis engine for Agent 07.

Implements Arps hyperbolic and exponential decline curve fitting using scipy,
with multi-segment capability and EUR projection.

GoM deepwater Miocene benchmarks (used for anomaly detection):
  - Initial decline: 15–25 %/yr
  - Terminal decline: 3–6 %/yr
  - b-factor: 0.3–0.7 for partial water-drive sands
  - b > 0.8 is anomalous — flag for LLM cross-check vs. drive mechanism
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger(__name__)

# Minimum data points required to attempt curve fitting
MIN_DATA_POINTS = 6

# GoM parameter bounds for curve_fit (per-month rates)
_BOUNDS_HYPERBOLIC = (
    [0.0,   0.001, 0.05],   # lower: qi, Di/month, b
    [np.inf, 0.5,  1.0],    # upper: qi, Di/month, b
)
_P0_HYPERBOLIC = None       # auto-set to [qi_first, 0.05, 0.5] at runtime

# Annual decline rate thresholds for secondary flags
DI_STEEP_AMBER_PCT  = 30.0   # annual %
DI_STEEP_RED_PCT    = 50.0   # annual %
B_ANOMALY_THRESHOLD = 0.80   # flag if b > this value

# R² threshold below which fit is considered unreliable
R2_POOR_THRESHOLD = 0.70


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class DCAResult:
    """Result of decline curve analysis for a single well."""
    curve_type:         str               # "hyperbolic" | "exponential" | "insufficient_data" | "failed"
    qi_boepd:           float  = 0.0      # Initial rate (boe/d)
    Di_annual_pct:      float  = 0.0      # Annual decline rate (%)
    b_factor:           float  = 0.0      # Arps b-factor
    eur_mmboe:          float  = 0.0      # Estimated Ultimate Recovery (MMboe)
    fit_r2:             float  = 0.0      # Coefficient of determination
    months_of_data:     int    = 0        # Data points used in fit
    flags:              list[str] = field(default_factory=list)  # DCA-specific flags
    insufficient_data:  bool   = False    # True if < MIN_DATA_POINTS


# ── Arps equations ────────────────────────────────────────────────────────────

def arps_hyperbolic(t: np.ndarray, qi: float, Di: float, b: float) -> np.ndarray:
    """
    Arps hyperbolic decline: q(t) = qi / (1 + b·Di·t)^(1/b)

    Args:
        t:  Time array in months from first production.
        qi: Initial rate (boe/d).
        Di: Monthly decline rate (fraction/month).
        b:  Hyperbolic exponent (0 < b < 1; b=0 → exponential).

    Returns:
        Rate array (boe/d) at each time step.
    """
    b_safe = max(b, 1e-6)
    return qi / np.power(1.0 + b_safe * Di * t, 1.0 / b_safe)


def arps_exponential(t: np.ndarray, qi: float, Di: float) -> np.ndarray:
    """
    Arps exponential decline: q(t) = qi · exp(−Di·t)

    Args:
        t:  Time array in months.
        qi: Initial rate (boe/d).
        Di: Monthly decline rate (fraction/month).

    Returns:
        Rate array (boe/d) at each time step.
    """
    return qi * np.exp(-Di * t)


# ── EUR calculation ──────────────────────────────────────────────────────────

def compute_eur(
    qi: float,
    Di_monthly: float,
    b: float,
    economic_limit_boepd: float = 25.0,
    projection_months: int = 240,
    time_step_months: float = 1.0,
) -> float:
    """
    Compute EUR by numerical integration of the decline curve to abandonment.

    Integrates q(t) from t=0 until rate drops below economic_limit OR
    projection_months is reached. Returns EUR in boe (not MMboe — caller converts).

    Uses trapezoid rule with monthly steps.
    """
    if qi <= 0 or Di_monthly <= 0:
        return 0.0

    t_arr = np.arange(0, projection_months + time_step_months, time_step_months)
    if b > 1e-4:
        q_arr = arps_hyperbolic(t_arr, qi, Di_monthly, b)
    else:
        q_arr = arps_exponential(t_arr, qi, Di_monthly)

    # Find abandonment month (first time rate < economic limit)
    below_limit = np.where(q_arr < economic_limit_boepd)[0]
    if len(below_limit):
        cutoff = below_limit[0]
        t_arr = t_arr[:cutoff + 1]
        q_arr = q_arr[:cutoff + 1]

    # Convert rate (boe/d) to volume per month (boe/month = rate * 30.44 days)
    # np.trapezoid is the NumPy 2.0 name (np.trapz was removed in NumPy 2.0)
    _trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz", None)
    eur_boe = float(_trapz(q_arr * 30.44, t_arr))   # boe/d * days/month * months = boe
    return eur_boe


# ── Coefficient of determination ─────────────────────────────────────────────

def _r_squared(y_actual: np.ndarray, y_predicted: np.ndarray) -> float:
    """Calculate R² between actual and model-predicted values."""
    ss_res = float(np.sum((y_actual - y_predicted) ** 2))
    ss_tot = float(np.sum((y_actual - np.mean(y_actual)) ** 2))
    if ss_tot < 1e-12:
        return 1.0
    return max(0.0, 1.0 - ss_res / ss_tot)


# ── Main fitting function ─────────────────────────────────────────────────────

def fit_decline_curve(
    times: np.ndarray,
    rates: np.ndarray,
    economic_limit_boepd: float = 25.0,
    projection_years: int = 20,
) -> DCAResult:
    """
    Fit multi-segment Arps decline to production history.

    Steps:
      1. Try Arps hyperbolic with GoM-bounded parameters.
      2. If hyperbolic fails (RuntimeError / poor fit), fall back to exponential.
      3. Compute EUR by integrating fitted curve to economic limit.
      4. Generate quality flags (steep decline, anomalous b-factor, poor R²).

    Args:
        times:                Month index from first production (0, 1, 2, …).
        rates:                Normalized boe/d for each month.
        economic_limit_boepd: Abandonment rate for EUR calculation.
        projection_years:     Maximum projection horizon.

    Returns:
        DCAResult dataclass.
    """
    n = len(times)
    flags: list[str] = []

    if n < MIN_DATA_POINTS:
        return DCAResult(
            curve_type="insufficient_data",
            months_of_data=n,
            insufficient_data=True,
            flags=[f"Only {n} months of data; minimum {MIN_DATA_POINTS} required for DCA"],
        )

    # Filter out zeros/negatives (shut-in months) for fitting
    mask = rates > 0
    t_fit = times[mask].astype(float)
    r_fit = rates[mask].astype(float)

    if len(t_fit) < MIN_DATA_POINTS:
        return DCAResult(
            curve_type="insufficient_data",
            months_of_data=n,
            insufficient_data=True,
            flags=[f"Fewer than {MIN_DATA_POINTS} non-zero production months after filtering zeros"],
        )

    projection_months = projection_years * 12
    initial_rate_guess = float(r_fit[0]) if r_fit[0] > 0 else 100.0

    # ── Attempt hyperbolic fit ────────────────────────────────────────────────
    try:
        from scipy.optimize import curve_fit  # type: ignore

        popt, _ = curve_fit(
            arps_hyperbolic,
            t_fit,
            r_fit,
            p0=[initial_rate_guess, 0.05, 0.5],
            bounds=_BOUNDS_HYPERBOLIC,
            maxfev=10_000,
            method="trf",
        )
        qi, Di_monthly, b = float(popt[0]), float(popt[1]), float(popt[2])
        y_pred = arps_hyperbolic(t_fit, qi, Di_monthly, b)
        r2 = _r_squared(r_fit, y_pred)

        if r2 < R2_POOR_THRESHOLD:
            flags.append(
                f"Hyperbolic fit R²={r2:.2f} is poor (threshold {R2_POOR_THRESHOLD:.2f}) — "
                "limited confidence in EUR projection; consider requesting additional production history"
            )

        # Anomaly flags
        Di_annual = Di_monthly * 12 * 100  # percent per year
        if Di_annual > DI_STEEP_RED_PCT:
            flags.append(
                f"Annual decline {Di_annual:.0f}%/yr is very steep (>50%/yr) — "
                "verify production data quality; may indicate mechanical issue or choke change"
            )
        elif Di_annual > DI_STEEP_AMBER_PCT:
            flags.append(
                f"Annual decline {Di_annual:.0f}%/yr is above GoM deepwater typical range (15–25%/yr)"
            )

        if b > B_ANOMALY_THRESHOLD:
            flags.append(
                f"b-factor {b:.2f} is anomalously high (>{B_ANOMALY_THRESHOLD}); "
                "cross-check against stated drive mechanism — expected b=0.3–0.7 for GoM Miocene sands"
            )

        eur_boe = compute_eur(qi, Di_monthly, b, economic_limit_boepd, projection_months)

        return DCAResult(
            curve_type="hyperbolic",
            qi_boepd=round(qi, 1),
            Di_annual_pct=round(Di_annual, 1),
            b_factor=round(b, 3),
            eur_mmboe=round(eur_boe / 1e6, 3),
            fit_r2=round(r2, 3),
            months_of_data=n,
            flags=flags,
        )

    except Exception as e:
        log.debug("Hyperbolic fit failed (%s); attempting exponential fallback", e)

    # ── Exponential fallback ──────────────────────────────────────────────────
    try:
        from scipy.optimize import curve_fit  # type: ignore

        popt_exp, _ = curve_fit(
            arps_exponential,
            t_fit,
            r_fit,
            p0=[initial_rate_guess, 0.05],
            bounds=([0.0, 0.0001], [np.inf, 0.5]),
            maxfev=5_000,
        )
        qi_exp, Di_exp = float(popt_exp[0]), float(popt_exp[1])
        y_pred_exp = arps_exponential(t_fit, qi_exp, Di_exp)
        r2_exp = _r_squared(r_fit, y_pred_exp)

        Di_annual_exp = Di_exp * 12 * 100
        eur_boe_exp = compute_eur(qi_exp, Di_exp, 0.0, economic_limit_boepd, projection_months)

        flags.append("Hyperbolic fit failed; using exponential decline (conservative EUR estimate)")
        if r2_exp < R2_POOR_THRESHOLD:
            flags.append(
                f"Exponential fit R²={r2_exp:.2f} is poor — production history may be non-monotonic"
            )

        return DCAResult(
            curve_type="exponential",
            qi_boepd=round(qi_exp, 1),
            Di_annual_pct=round(Di_annual_exp, 1),
            b_factor=0.0,
            eur_mmboe=round(eur_boe_exp / 1e6, 3),
            fit_r2=round(r2_exp, 3),
            months_of_data=n,
            flags=flags,
        )

    except Exception as e:
        log.warning("Both hyperbolic and exponential DCA fits failed: %s", e)
        return DCAResult(
            curve_type="failed",
            months_of_data=n,
            flags=[f"DCA fitting failed: {e}"],
        )


def project_decline_curve(
    dca: DCAResult,
    months_ahead: int = 60,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate projected rate array from DCA result for charting.

    Returns:
        (t_months, q_boepd) arrays starting from t=0.
    """
    if dca.curve_type in ("insufficient_data", "failed") or dca.qi_boepd <= 0:
        return np.array([]), np.array([])

    Di_monthly = dca.Di_annual_pct / 100.0 / 12.0
    t = np.arange(0, months_ahead + 1, dtype=float)

    if dca.curve_type == "hyperbolic" and dca.b_factor > 1e-4:
        q = arps_hyperbolic(t, dca.qi_boepd, Di_monthly, dca.b_factor)
    else:
        q = arps_exponential(t, dca.qi_boepd, Di_monthly)

    return t, q
