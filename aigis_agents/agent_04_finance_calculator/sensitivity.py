"""
Sensitivity analysis engine for Agent 04 — Finance Calculator.

Generates tornado chart data via one-way sensitivity:
  - Varies each input variable independently ±10%, ±20%
  - Re-runs NPV for each perturbation
  - Returns rows sorted by swing (largest NPV impact first)
"""

from __future__ import annotations

import copy

from aigis_agents.agent_04_finance_calculator.calculator import (
    build_cash_flow_schedule,
    calculate_npv,
)
from aigis_agents.agent_04_finance_calculator.models import (
    FinancialInputs,
    SensitivityRow,
)

# Default sensitivity variables and their human-readable labels.
# These variables drive the asset-level NPV (PV10) shown on the tornado chart.
# Acquisition cost is intentionally EXCLUDED: it is a fixed input compared separately
# against asset NPV — varying it does not change the asset's intrinsic value.
DEFAULT_SENSITIVITY_VARIABLES: list[tuple[str, str]] = [
    ("oil_price_usd_bbl", "Oil Price ($/bbl)"),
    ("initial_rate_boepd", "Initial Production Rate (boepd)"),
    ("decline_rate_annual_pct", "Annual Decline Rate (%)"),
    ("loe_per_boe", "Lifting Cost ($/boe)"),
    ("development_capex", "Development CAPEX ($M)"),
    ("discount_rate_pct", "Discount Rate (%)"),
    ("abandonment_cost_p50_usd", "ARO / Abandonment Cost ($M)"),
]


def _perturb_inputs(inputs: FinancialInputs, variable: str, factor: float) -> FinancialInputs:
    """
    Return a copy of FinancialInputs with one variable scaled by (1 + factor).
    Factor of -0.20 = 20% decrease, +0.10 = 10% increase.
    """
    data = inputs.model_dump()

    if variable == "oil_price_usd_bbl":
        data["price"]["oil_price_usd_bbl"] *= (1 + factor)
    elif variable == "initial_rate_boepd":
        data["production"]["initial_rate_boepd"] *= (1 + factor)
    elif variable == "decline_rate_annual_pct":
        # Higher decline = worse; lower decline = better
        data["production"]["decline_rate_annual_pct"] *= (1 + factor)
    elif variable == "loe_per_boe":
        data["costs"]["loe_per_boe"] *= (1 + factor)
    elif variable == "development_capex":
        dev_capex = data["capex"]["development_capex_by_year_usd"]
        data["capex"]["development_capex_by_year_usd"] = [c * (1 + factor) for c in dev_capex]
    elif variable == "discount_rate_pct":
        data["discount_rate_pct"] *= (1 + factor)
        # Clamp discount rate to minimum 1%
        data["discount_rate_pct"] = max(1.0, data["discount_rate_pct"])
    elif variable == "abandonment_cost_p50_usd":
        data["capex"]["abandonment_cost_p50_usd"] *= (1 + factor)
        data["capex"]["abandonment_cost_p70_usd"] *= (1 + factor)
    else:
        # Unknown variable — return unchanged
        return inputs

    return FinancialInputs(**data)


def _compute_npv(inputs: FinancialInputs) -> float:
    """Run cash flow schedule and compute asset-level NPV at inputs.discount_rate_pct.
    Acquisition cost is excluded — NPV here is the intrinsic asset value."""
    cfs = build_cash_flow_schedule(inputs)
    result = calculate_npv(cfs, inputs.discount_rate_pct)
    return result.metric_result or 0.0


def run_sensitivity(
    inputs: FinancialInputs,
    base_npv_usd: float,
    variables: list[tuple[str, str]] | None = None,
    ranges: list[float] | None = None,
) -> list[SensitivityRow]:
    """
    One-way sensitivity analysis.

    For each variable, vary it independently while holding all others at base.
    Returns rows sorted by swing (largest NPV impact first) — ready for tornado chart.

    Args:
        inputs: Base case FinancialInputs
        base_npv_usd: Pre-computed base NPV (avoids redundant computation)
        variables: List of (variable_key, label) pairs; defaults to DEFAULT_SENSITIVITY_VARIABLES
        ranges: List of perturbation fractions; defaults to [-0.20, -0.10, +0.10, +0.20]

    Returns:
        List of SensitivityRow, sorted by swing descending
    """
    if variables is None:
        variables = DEFAULT_SENSITIVITY_VARIABLES
    if ranges is None:
        ranges = [-0.20, -0.10, 0.10, 0.20]

    rows: list[SensitivityRow] = []

    for var_key, var_label in variables:
        npv_results: dict[float, float | None] = {}

        # Get base value for display
        base_value = _get_base_value(inputs, var_key)
        if base_value is None:
            continue

        for factor in ranges:
            try:
                perturbed = _perturb_inputs(inputs, var_key, factor)
                npv = _compute_npv(perturbed)
                npv_results[factor] = npv
            except Exception:
                npv_results[factor] = None

        all_vals = [v for v in npv_results.values() if v is not None]
        swing = (max(all_vals) - min(all_vals)) if len(all_vals) >= 2 else 0.0

        rows.append(SensitivityRow(
            variable=var_key,
            variable_label=var_label,
            base_value=base_value,
            base_npv_usd=base_npv_usd,
            minus_20_pct_npv=npv_results.get(-0.20),
            minus_10_pct_npv=npv_results.get(-0.10),
            plus_10_pct_npv=npv_results.get(0.10),
            plus_20_pct_npv=npv_results.get(0.20),
            swing_usd=round(swing, 0),
        ))

    # Sort by swing descending (largest impact at top of tornado)
    rows.sort(key=lambda r: r.swing_usd, reverse=True)
    return rows


def run_two_way_sensitivity(
    inputs: FinancialInputs,
    var_x: str,
    x_factors: list[float],
    var_y: str,
    y_factors: list[float],
) -> dict:
    """
    Two-way sensitivity: NPV matrix for combinations of var_x and var_y perturbations.

    Returns:
        {
            "var_x": var_x,
            "var_y": var_y,
            "x_labels": [...],
            "y_labels": [...],
            "matrix": [[npv, ...], ...],  # rows=y, cols=x
        }
    """
    x_labels = [f"{f*100:+.0f}%" for f in x_factors]
    y_labels = [f"{f*100:+.0f}%" for f in y_factors]
    matrix: list[list[float | None]] = []

    for y_factor in y_factors:
        row: list[float | None] = []
        for x_factor in x_factors:
            try:
                perturbed = _perturb_inputs(inputs, var_x, x_factor)
                perturbed = _perturb_inputs(perturbed, var_y, y_factor)
                npv = _compute_npv(perturbed)
                row.append(round(npv, 0))
            except Exception:
                row.append(None)
        matrix.append(row)

    return {
        "var_x": var_x,
        "var_y": var_y,
        "x_labels": x_labels,
        "y_labels": y_labels,
        "matrix": matrix,
    }


def _get_base_value(inputs: FinancialInputs, variable: str) -> float | None:
    """Extract the base value of a sensitivity variable from FinancialInputs."""
    if variable == "oil_price_usd_bbl":
        return inputs.price.oil_price_usd_bbl
    elif variable == "initial_rate_boepd":
        return inputs.production.initial_rate_boepd
    elif variable == "decline_rate_annual_pct":
        return inputs.production.decline_rate_annual_pct
    elif variable == "loe_per_boe":
        return inputs.costs.loe_per_boe
    elif variable == "development_capex":
        return sum(inputs.capex.development_capex_by_year_usd)
    elif variable == "discount_rate_pct":
        return inputs.discount_rate_pct
    elif variable == "abandonment_cost_p50_usd":
        return inputs.capex.abandonment_cost_p50_usd
    return None
