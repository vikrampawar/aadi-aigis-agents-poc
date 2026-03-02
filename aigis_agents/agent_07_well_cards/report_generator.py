"""
Markdown report generator for Agent 07 — Well Performance Intelligence Cards.

Assembles the full fleet MD report from a list of well card dicts.
Charts are embedded as relative image paths.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from aigis_agents.agent_07_well_cards.rag_classifier import (
    GREEN, AMBER, RED, BLACK, RAG_EMOJI, summarize_fleet_rag,
)

log = logging.getLogger(__name__)

# RAG ordering for report sections (GREEN first, BLACK last)
_RAG_ORDER = {GREEN: 0, AMBER: 1, RED: 2, BLACK: 3}


# ── Section builders ──────────────────────────────────────────────────────────

def _fleet_overview_table(fleet: dict) -> str:
    rag = fleet.get("rag_summary", {})
    rows = [
        f"| Total wells | **{fleet.get('total_wells', 0)}** |",
        f"| Total current rate | **{fleet.get('total_current_rate_boepd', 0):,.0f} boe/d** |",
        f"| Total DCA EUR | **{fleet.get('total_eur_mmboe', 0):.2f} MMboe** |",
        f"| 🟢 GREEN | {rag.get(GREEN, 0)} wells |",
        f"| 🟡 AMBER | {rag.get(AMBER, 0)} wells |",
        f"| 🔴 RED | {rag.get(RED, 0)} wells |",
        f"| ⚫ BLACK (shut-in) | {rag.get(BLACK, 0)} wells |",
        f"| Critical flags | **{fleet.get('critical_flag_count', 0)}** |",
    ]
    wdi = fleet.get("weighted_decline_rate_pct")
    if wdi is not None:
        rows.append(f"| Weighted avg decline | **{wdi:.1f}%/yr** |")
    return "\n".join(["| Metric | Value |", "|--------|-------|"] + rows)


def _rag_summary_table(well_cards: list[dict]) -> str:
    header = (
        "| Well | Rate (boe/d) | EUR (MMboe) | vs CPR 2P | RAG | Top Flag |\n"
        "|------|-------------|-------------|-----------|-----|----------|\n"
    )
    rows = []
    for card in well_cards:
        m   = card.get("metrics", {})
        dc  = card.get("decline_curve", {})
        rag = card.get("rag_status", GREEN)
        em  = RAG_EMOJI.get(rag, "")
        rate = f"{m.get('current_rate_boepd', 0):,.0f}" if m.get("current_rate_boepd") else "—"
        eur  = f"{dc.get('eur_mmboe', 0):.2f}" if dc.get("eur_mmboe") else "—"
        vs_cpr = dc.get("eur_vs_cpr_2p_pct")
        vs_str = f"{vs_cpr:+.0f}%" if vs_cpr is not None else "N/A"
        flags   = card.get("flags", [])
        top_flag = flags[0][:80] + "…" if flags and len(flags[0]) > 80 else (flags[0] if flags else "")
        rows.append(
            f"| {card.get('well_name', '?')} | {rate} | {eur} | {vs_str} | {em} {rag} | {top_flag} |"
        )
    return header + "\n".join(rows)


def _well_section(card: dict, charts_rel_dir: str | None) -> str:
    well  = card.get("well_name", "Unknown")
    rag   = card.get("rag_status", GREEN)
    em    = RAG_EMOJI.get(rag, "")
    label = card.get("rag_label", "")
    m     = card.get("metrics", {})
    dc    = card.get("decline_curve", {})
    dq    = card.get("data_quality", {})
    res   = card.get("reserve_estimates", {})

    lines: list[str] = [
        f"### {em} {well}",
        f"**RAG:** {rag} — {label}",
        "",
        "#### Key Metrics",
        "| Metric | Value |",
        "|--------|-------|",
    ]

    def _row(label: str, val, fmt: str = ".1f", unit: str = "") -> str:
        if val is None:
            return f"| {label} | N/A |"
        try:
            return f"| {label} | {format(val, fmt)}{' ' + unit if unit else ''} |"
        except (TypeError, ValueError):
            return f"| {label} | {val} |"

    lines += [
        _row("Current rate",   m.get("current_rate_boepd"), ",.0f", "boe/d"),
        _row("Peak rate",      m.get("peak_rate_boepd"),    ",.0f", "boe/d"),
        _row("Cumulative",     m.get("cumulative_mmboe"),   ".3f",  "MMboe"),
        _row("IP30",           m.get("ip30_boepd"),         ",.0f", "boe/d"),
        _row("IP90",           m.get("ip90_boepd"),         ",.0f", "boe/d"),
        _row("IP180",          m.get("ip180_boepd"),        ",.0f", "boe/d"),
        _row("12-mo trend",    m.get("trend_12m_pct"),      "+.1f", "%"),
        _row("GOR (latest)",   m.get("gor_scf_stb"),        ",.0f", "scf/stb"),
        _row("GOR trend 12m",  m.get("gor_trend_12m_pct"),  "+.1f", "%"),
        _row("Water cut",      m.get("water_cut_pct"),      ".1f",  "%"),
        _row("WC trend 12m",   m.get("wc_trend_12m_ppts"),  "+.1f", " ppts"),
        _row("Uptime",         m.get("uptime_pct"),         ".1f",  f"% ({m.get('uptime_source', 'assumed')})"),
    ]

    lines += [
        "",
        "#### Decline Curve Analysis",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Curve type | {dc.get('curve_type', 'N/A')} |",
        _row("qi (initial rate)", dc.get("qi_boepd"),      ",.0f", "boe/d"),
        _row("Di (annual)",       dc.get("Di_annual_pct"), ".1f",  "%/yr"),
        _row("b-factor",          dc.get("b_factor"),      ".3f"),
        _row("DCA EUR",           dc.get("eur_mmboe"),     ".3f",  "MMboe"),
        _row("EUR vs CPR 2P",     dc.get("eur_vs_cpr_2p_pct"), "+.1f", "%"),
        _row("Fit R²",            dc.get("fit_r2"),        ".3f"),
    ]

    if res:
        lines += [
            "",
            "#### CPR Reserve Estimates",
            "| Class | EUR (MMboe) |",
            "|-------|-------------|",
        ]
        for cls in ("1P", "2P", "3P"):
            val = res.get(cls)
            if val is not None:
                lines.append(f"| {cls} | {val:.3f} |")
        if res.get("source"):
            lines.append(f"\n*Source: {res['source']}*")

    # Chart embed
    chart_path = card.get("chart_path")
    if chart_path and charts_rel_dir:
        chart_filename = os.path.basename(chart_path)
        rel_path = os.path.join(charts_rel_dir, chart_filename).replace("\\", "/")
        lines += ["", f"![{well} production chart]({rel_path})", ""]

    # Narrative
    narrative = card.get("narrative", "")
    if narrative:
        lines += ["", "#### Analyst Narrative", "", narrative, ""]

    # Flags
    flags = card.get("flags", [])
    if flags:
        lines += ["", "#### Flags & Red Flags", ""]
        for f in flags:
            lines.append(f"- {f}")

    # Data quality
    lines += [
        "",
        "#### Data Quality",
        f"- Months of data: {dq.get('months_of_data', 0)}",
        f"- Completeness: {dq.get('completeness_pct', 0):.0f}%",
    ]
    for dflag in dq.get("data_flags", []):
        lines.append(f"- ⚠️ {dflag}")

    overrides = card.get("learned_overrides", [])
    if overrides:
        lines += ["", "*Pattern overrides applied:*"]
        for ov in overrides:
            lines.append(f"- {ov}")

    lines.append("\n---")
    return "\n".join(lines)


def _methodology_appendix(
    downtime_treatment: str,
    default_uptime_pct: float,
    forecast_case: str,
    economic_limit_boepd: float,
    projection_years: int,
) -> str:
    return f"""## Appendix — Methodology

### Decline Curve Analysis
Production history is fitted using Arps hyperbolic decline:

    q(t) = qi / (1 + b·Di·t)^(1/b)

where t is time in months, qi is initial rate, Di is monthly decline rate, and b is the
hyperbolic exponent. If the hyperbolic fit fails (R² < 0.70 or scipy convergence error),
exponential decline is used as a conservative fallback. EUR is computed by numerical
integration (trapezoid rule) to economic limit ({economic_limit_boepd:.0f} boe/d) over a
{projection_years}-year horizon.

**GoM deepwater benchmarks applied:**
- Initial decline: 15–25%/yr (Miocene subsea tie-backs)
- Terminal decline: 3–6%/yr
- b-factor: 0.3–0.7 for partial water-drive Miocene sands; b > 0.8 flagged anomalous
- Minimum data requirement: 6 production months

### Downtime Normalization
Treatment: **{downtime_treatment}**
- Default uptime assumption (where no actuals): **{default_uptime_pct:.0f}%**
- Formula: `rate_normalized = rate_actual / uptime_factor`
- All assumed uptime values are flagged in the data quality section

### RAG Classification
| Status | Criterion |
|--------|-----------|
| 🟢 GREEN (Outperformer) | Actual ≥ +10% vs CPR base case |
| 🟢 GREEN (On-track) | Actual −10% to +10% vs CPR |
| 🟡 AMBER | Actual −10% to −25% vs CPR, or GOR rise +20%/yr, or WC rise +8 ppts/yr |
| 🔴 RED | Actual < −25% vs CPR, or GOR rise +40%/yr, or WC rise +15 ppts/yr, or decline >50%/yr |
| ⚫ BLACK | Shut-in, suspended, plugged & abandoned |

Secondary metrics (GOR trend, WC trend, annual decline, uptime) can escalate but not improve the primary classification.

### CPR Forecast Case Used
`{forecast_case}` — loaded from Agent 02 data store.

### Data Sources
- Production history: Agent 02 SQLite data store (`production_series` table)
- Reserve estimates: Agent 02 `reserve_estimates` table (1P / 2P / 3P)
- Scalar metrics: Agent 02 `scalar_datapoints` table
- Domain knowledge: GoM technical playbook, Upstream Oil & Gas 101
"""


# ── Main report generator ─────────────────────────────────────────────────────

def generate_md_report(
    well_cards:           list[dict],
    deal_name:            str,
    deal_id:              str,
    output_path:          str,
    fleet_chart_path:     str | None = None,
    dashboard_path:       str | None = None,
    downtime_treatment:   str        = "strip_estimated",
    default_uptime_pct:   float      = 90.0,
    forecast_case:        str        = "cpr_base_case",
    economic_limit_boepd: float      = 25.0,
    projection_years:     int        = 20,
) -> str:
    """
    Assemble and write the Markdown fleet performance report.

    Args:
        well_cards:       List of WellCard dicts from build_well_card().
        deal_name:        Human-readable deal/asset name.
        deal_id:          Deal identifier (for file paths).
        output_path:      Where to write the .md file.
        fleet_chart_path: Path to fleet_summary.png (embedded in overview).
        dashboard_path:   Path to Plotly HTML dashboard (linked, not embedded).
        downtime_treatment, default_uptime_pct, forecast_case, economic_limit_boepd,
        projection_years: Passed to methodology appendix for transparency.

    Returns:
        The output_path that was written.
    """
    now = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
    n   = len(well_cards)

    # Fleet stats
    fleet = summarize_fleet_rag(well_cards)
    fleet["total_wells"] = n

    # Sort: GREEN → AMBER → RED → BLACK
    sorted_cards = sorted(well_cards, key=lambda c: _RAG_ORDER.get(c.get("rag_status", GREEN), 0))

    # Relative charts directory (sibling folder)
    charts_dir  = os.path.dirname(output_path)
    charts_rel  = "07_well_charts"  # relative to report location

    # ── Assemble sections ─────────────────────────────────────────────────────
    sections: list[str] = []

    # Header
    sections.append(
        f"# Well Performance Intelligence Cards — {deal_name}\n"
        f"*Generated: {now} | {n} well{'s' if n != 1 else ''} | Deal ID: `{deal_id}`*\n"
    )

    # Fleet overview
    sections.append("## Fleet Overview\n")
    sections.append(_fleet_overview_table(fleet))
    sections.append("")

    if fleet_chart_path:
        rel = os.path.relpath(fleet_chart_path, charts_dir).replace("\\", "/")
        sections.append(f"![Fleet production overview]({rel})\n")

    if dashboard_path:
        rel = os.path.relpath(dashboard_path, charts_dir).replace("\\", "/")
        sections.append(f"📊 [Interactive Fleet Dashboard]({rel})\n")

    # RAG summary table
    sections.append("## RAG Status Summary\n")
    sections.append(_rag_summary_table(sorted_cards))
    sections.append("")

    # Individual well cards
    sections.append("---\n## Individual Well Cards\n")
    sections.append(
        "> Wells ordered by RAG severity (GREEN → AMBER → RED → BLACK), "
        "then by current production rate.\n"
    )

    for card in sorted_cards:
        sections.append(_well_section(card, charts_rel))

    # Methodology appendix
    sections.append(_methodology_appendix(
        downtime_treatment   = downtime_treatment,
        default_uptime_pct   = default_uptime_pct,
        forecast_case        = forecast_case,
        economic_limit_boepd = economic_limit_boepd,
        projection_years     = projection_years,
    ))

    # Write file
    content = "\n".join(sections)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    log.info("Written well performance report: %s", output_path)
    return output_path
