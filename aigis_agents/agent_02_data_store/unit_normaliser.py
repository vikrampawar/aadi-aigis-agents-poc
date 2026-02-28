"""
Unit normalisation for Agent 02 — VDR Financial & Operational Data Store.

Converts domain-specific oil & gas units to standardised bases:
  - Volume: all production → boe/boed
  - Currency: all USD variants → USD (base, not thousands/millions)
  - Rate: per-unit cost metrics normalised to USD/boe

For complex domain calculations (decline curves, BTU-based gas conversion),
delegates to Agent 04 via the mesh.
"""

from __future__ import annotations

from typing import Any


# ── Conversion tables ─────────────────────────────────────────────────────────

# Gas conversion: mcf → boe at 6:1 ratio (standard SPE/SEC convention)
_MCF_PER_BOE = 6.0

# Production rate conversions → boe/d
_TO_BOEPD: dict[str, float] = {
    # Oil
    "bopd":  1.0,
    "bbl/d": 1.0,
    "bbl":   1.0,
    "stb/d": 1.0,
    # Gas (at 6:1 MCF:BOE)
    "mcfd":  1.0 / _MCF_PER_BOE,
    "mcf/d": 1.0 / _MCF_PER_BOE,
    "mmcfd": 1000.0 / _MCF_PER_BOE,
    "mmcf/d":1000.0 / _MCF_PER_BOE,
    "mscfd": 1.0 / _MCF_PER_BOE,
    "boed":  1.0,
    "boepd": 1.0,
    "boe/d": 1.0,
    # NGL
    "ngld":  1.0,
    "ngl/d": 1.0,
}

# Cumulative volume conversions → boe
_TO_BOE: dict[str, float] = {
    "bbl":    1.0,
    "boe":    1.0,
    "mmboe":  1_000_000.0,
    "mboe":   1_000.0,
    "mbbl":   1_000.0,
    "mmbbl":  1_000_000.0,
    "bcf":    1_000_000.0 / _MCF_PER_BOE,  # bcf → mcf → boe
    "tcf":    1_000_000_000.0 / _MCF_PER_BOE,
    "mmcf":   1_000.0 / _MCF_PER_BOE,
    "mcf":    1.0 / _MCF_PER_BOE,
    "bcfe":   1_000_000.0 / _MCF_PER_BOE,
}

# Currency scalar conversions → USD
_TO_USD: dict[str, float] = {
    "usd":    1.0,
    "$":      1.0,
    "kusd":   1_000.0,
    "musd":   1_000_000.0,
    "mmusd":  1_000_000.0,
    "mm$":    1_000_000.0,
    "m$":     1_000.0,
    "k$":     1_000.0,
    "usd000": 1_000.0,
    "usdm":   1_000_000.0,
    "gbp":    1.27,   # approximate — Agent 04 should be called for FX-sensitive work
    "cad":    0.74,
    "aud":    0.63,
}

# Per-unit cost conversions → USD/boe
_RATE_TO_USD_PER_BOE: dict[str, float] = {
    "usd/boe":   1.0,
    "$/boe":     1.0,
    "usd/bbl":   1.0,
    "$/bbl":     1.0,
    "$/mcf":     _MCF_PER_BOE,     # $/mcf * 6 = $/boe
    "usd/mcf":   _MCF_PER_BOE,
    "usd/mscf":  _MCF_PER_BOE,
    "$/mscf":    _MCF_PER_BOE,
}

# Units that are already percentages
_PERCENTAGE_UNITS = {"%", "pct", "percent", "fraction"}


# ── Public API ─────────────────────────────────────────────────────────────────

def normalise_value(
    value: float,
    unit: str,
    category: str = "other",
    agent04_fn: Any | None = None,
) -> tuple[float | None, str | None]:
    """
    Normalise a value + unit pair.

    Returns (normalised_value, normalised_unit) or (None, None) if no conversion needed.

    Args:
        value:      Raw extracted value.
        unit:       Unit string as extracted.
        category:   Data category (production | financial | cost | fiscal | other).
        agent04_fn: Optional callable to Agent 04 for complex conversions.

    Returns:
        (normalised_value, normalised_unit) — None if no conversion applies.
    """
    unit_lower = unit.lower().strip()

    # Production rate → boepd
    if unit_lower in _TO_BOEPD:
        factor = _TO_BOEPD[unit_lower]
        if factor == 1.0:
            return None, None  # already in boepd/bopd
        return value * factor, "boepd"

    # Cumulative volume → boe
    if unit_lower in _TO_BOE:
        factor = _TO_BOE[unit_lower]
        if factor == 1.0:
            return None, None  # already in boe/bbl
        return value * factor, "boe"

    # Currency → USD
    if unit_lower in _TO_USD:
        factor = _TO_USD[unit_lower]
        if factor == 1.0:
            return None, None  # already in USD
        return value * factor, "USD"

    # Per-unit cost → USD/boe
    if unit_lower in _RATE_TO_USD_PER_BOE:
        factor = _RATE_TO_USD_PER_BOE[unit_lower]
        if factor == 1.0:
            return None, None
        return value * factor, "USD/boe"

    # Percentage: no-op
    if unit_lower in _PERCENTAGE_UNITS:
        return None, None

    # Delegate complex conversions to Agent 04
    if agent04_fn:
        return _delegate_to_agent04(value, unit, category, agent04_fn)

    return None, None


def normalise_unit_string(unit: str) -> str:
    """
    Return a canonical unit string.

    e.g. "Bbl/d" → "bopd", "MUSD" → "kUSD", "MCF/D" → "mcfd"
    """
    unit_lower = unit.lower().strip()
    if unit_lower in _TO_BOEPD:
        return _canonical_production_unit(unit_lower)
    if unit_lower in _TO_BOE:
        return _canonical_volume_unit(unit_lower)
    if unit_lower in _TO_USD:
        return _canonical_currency_unit(unit_lower)
    if unit_lower in _RATE_TO_USD_PER_BOE:
        return "USD/boe"
    if unit_lower in _PERCENTAGE_UNITS:
        return "%"
    return unit  # pass through if unknown


def batch_normalise(
    rows: list[dict],
    value_key: str = "value",
    unit_key: str = "unit",
    category_key: str = "category",
    agent04_fn: Any | None = None,
) -> list[dict]:
    """
    Normalise a list of data point dicts in-place (adds value_normalised + unit_normalised).

    Returns the same list with normalised fields added.
    """
    for row in rows:
        val = row.get(value_key)
        unit = row.get(unit_key, "")
        cat  = row.get(category_key, "other")
        if val is not None and unit:
            norm_val, norm_unit = normalise_value(float(val), unit, cat, agent04_fn)
            if norm_val is not None:
                row["value_normalised"] = norm_val
                row["unit_normalised"]  = norm_unit
    return rows


# ── Agent 04 delegation ───────────────────────────────────────────────────────

def _delegate_to_agent04(
    value: float,
    unit: str,
    category: str,
    agent04_fn: Any,
) -> tuple[float | None, str | None]:
    """
    Call Agent 04 for domain-specific unit conversions not covered by static tables.

    agent04_fn is expected to accept a conversion request dict and return
    {"normalised_value": float, "normalised_unit": str} or None.
    """
    try:
        result = agent04_fn({
            "operation": "unit_convert",
            "value": value,
            "from_unit": unit,
            "category": category,
        })
        if result and "normalised_value" in result:
            return result["normalised_value"], result.get("normalised_unit")
    except Exception:
        pass
    return None, None


# ── Canonical unit helpers ────────────────────────────────────────────────────

def _canonical_production_unit(unit_lower: str) -> str:
    if unit_lower in ("bopd", "bbl/d", "stb/d"):
        return "bopd"
    if unit_lower in ("mcfd", "mcf/d", "mscfd"):
        return "mcfd"
    if unit_lower in ("mmcfd", "mmcf/d"):
        return "mmcfd"
    if unit_lower in ("boed", "boepd", "boe/d"):
        return "boepd"
    return unit_lower


def _canonical_volume_unit(unit_lower: str) -> str:
    if unit_lower in ("bbl", "boe"):
        return "boe"
    if unit_lower in ("mboe", "mbbl"):
        return "mboe"
    if unit_lower in ("mmboe", "mmbbl"):
        return "mmboe"
    if unit_lower in ("mmcf",):
        return "mmcf"
    return unit_lower


def _canonical_currency_unit(unit_lower: str) -> str:
    if unit_lower in ("usd", "$"):
        return "USD"
    if unit_lower in ("kusd", "k$", "m$", "usd000"):
        return "kUSD"
    if unit_lower in ("musd", "mmusd", "mm$", "usdm"):
        return "MMUSD"
    return unit_lower
