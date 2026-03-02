"""
Chart generator for Agent 07 — Well Performance Intelligence Cards.

Generates:
  - Per-well matplotlib PNG (3-panel, dark Aigis theme)
  - Fleet-level Plotly HTML dashboard (2×2 grid)

Matplotlib is imported lazily so the module is importable even when
matplotlib is not installed (charts are skipped with a warning flag).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ── Aigis dark theme palette ──────────────────────────────────────────────────

_BG        = "#0d1117"
_SURFACE   = "#161b22"
_BORDER    = "#30363d"
_TEXT      = "#e6edf3"
_MUTED     = "#8b949e"

_COL_OIL   = "#3fb950"   # green
_COL_GAS   = "#58a6ff"   # blue
_COL_WATER = "#79c0ff"   # light blue
_COL_BOE   = "#f0883e"   # orange
_COL_DCA   = "#f0883e"   # orange (DCA curve)
_COL_FORE  = "#d2a8ff"   # purple  (CPR forecast)
_COL_GOR   = "#e6c069"   # amber
_COL_WC    = "#79c0ff"   # light blue

_RAG_COLOURS = {
    "GREEN": "#3fb950",
    "AMBER": "#e3b341",
    "RED":   "#f85149",
    "BLACK": "#8b949e",
}


# ── Per-well matplotlib chart ─────────────────────────────────────────────────

def generate_well_chart(
    well_name:      str,
    periods:        list[dict],          # from production_processor (normalized)
    dca_result:     Any | None,          # DCAResult dataclass or None
    forecast_data:  dict[str, dict],     # {period_str: {"boe_boepd": float}} CPR forecast
    rag_status:     str,
    output_path:    str,
) -> str | None:
    """
    Render a 3-panel production chart for a single well and save to output_path.

    Panel 1 (top, 50%): Stacked bar oil/gas/water boe/d + BOE total line
                         + DCA fitted + projected curve (orange)
                         + CPR forecast dashed (purple)
    Panel 2 (mid, 25%): GOR trend (scf/stb) + 20% and 40% rise threshold bands
    Panel 3 (bot, 25%): Water cut (%) + 8 ppt and 15 ppt rise threshold bands

    Returns the saved file path, or None if matplotlib unavailable / data insufficient.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        import numpy as np
    except ImportError:
        log.warning("matplotlib not installed — skipping per-well chart for %s", well_name)
        return None

    if not periods:
        log.debug("No production periods for %s — skipping chart", well_name)
        return None

    # ── Build time axis ───────────────────────────────────────────────────────
    labels    = [p["period"] for p in periods]
    n         = len(labels)
    x_idx     = np.arange(n)

    oil_vals  = np.array([p.get("oil_norm",   p.get("oil_bopd",   0.0) or 0.0) for p in periods])
    gas_vals  = np.array([p.get("gas_norm",   p.get("gas_boe",    0.0) or 0.0) for p in periods])
    wat_vals  = np.array([p.get("water_norm", p.get("water_boe",  0.0) or 0.0) for p in periods])
    boe_vals  = np.array([p.get("boe_norm",   p.get("boe_boepd",  0.0) or 0.0) for p in periods])
    gor_vals  = np.array([p.get("gor_scf_stb", None) for p in periods], dtype=object)
    wc_vals   = np.array([p.get("wc_pct",      None) for p in periods], dtype=object)

    # ── CPR forecast on Panel 1 ───────────────────────────────────────────────
    forecast_boe = []
    for lbl in labels:
        fd = forecast_data.get(lbl, {})
        forecast_boe.append(fd.get("boe_boepd") or fd.get("boe_norm"))
    forecast_arr = np.array(forecast_boe, dtype=float)
    has_forecast = not np.all(np.isnan(forecast_arr))

    # ── DCA overlay on Panel 1 ────────────────────────────────────────────────
    dca_x = dca_y = None
    if dca_result is not None and dca_result.curve_type not in ("insufficient_data", "failed"):
        try:
            from aigis_agents.agent_07_well_cards.dca_engine import project_decline_curve
            proj_months = 60
            t_raw, q_raw = project_decline_curve(dca_result, months_ahead=n + proj_months)
            dca_x = t_raw
            dca_y = q_raw
        except Exception as exc:
            log.debug("DCA projection failed: %s", exc)

    # ── Figure setup ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(10, 8), facecolor=_BG)
    gs  = fig.add_gridspec(4, 1, hspace=0.45)
    ax1 = fig.add_subplot(gs[:2, 0])   # Panel 1 — 50%
    ax2 = fig.add_subplot(gs[2,  0])   # Panel 2 — 25%
    ax3 = fig.add_subplot(gs[3,  0])   # Panel 3 — 25%

    rag_colour = _RAG_COLOURS.get(rag_status, _MUTED)

    for ax in (ax1, ax2, ax3):
        ax.set_facecolor(_SURFACE)
        ax.tick_params(colors=_MUTED, labelsize=8)
        ax.spines[:].set_color(_BORDER)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)
        ax.xaxis.label.set_color(_MUTED)
        ax.yaxis.label.set_color(_MUTED)
        ax.title.set_color(_TEXT)

    fig.suptitle(
        f"{well_name}  |  {rag_status}",
        color=rag_colour, fontsize=13, fontweight="bold", y=0.98,
    )

    # ── Panel 1: Stacked bars + DCA + forecast ────────────────────────────────
    bar_w = 0.7
    ax1.bar(x_idx, oil_vals, bar_w, label="Oil (boe/d)", color=_COL_OIL,  alpha=0.85)
    ax1.bar(x_idx, gas_vals, bar_w, label="Gas (boe/d)", color=_COL_GAS,  alpha=0.80, bottom=oil_vals)
    ax1.bar(x_idx, wat_vals, bar_w, label="Water (boe/d)", color=_COL_WATER, alpha=0.65,
            bottom=oil_vals + gas_vals)
    ax1.plot(x_idx, boe_vals, color=_COL_BOE, linewidth=1.8, label="Total BOE/d", zorder=5)

    if has_forecast:
        ax1.plot(x_idx, forecast_arr, color=_COL_FORE, linewidth=1.5,
                 linestyle="--", label="CPR forecast", zorder=4)

    if dca_x is not None and dca_y is not None:
        # Offset DCA curve to align month-0 with first period
        ax1.plot(dca_x, dca_y, color=_COL_DCA, linewidth=1.8,
                 linestyle="-.", label="DCA curve", zorder=6, alpha=0.85)

    ax1.set_ylabel("boe/d", fontsize=9)
    ax1.set_title("Production History", fontsize=10, pad=4)
    _set_xticks(ax1, labels, x_idx)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax1.legend(fontsize=7, facecolor=_SURFACE, edgecolor=_BORDER,
               labelcolor=_TEXT, loc="upper right", ncol=3)

    # Separator at last historical period
    ax1.axvline(n - 1, color=_MUTED, linewidth=0.8, linestyle=":")

    # ── Panel 2: GOR trend ────────────────────────────────────────────────────
    gor_numeric = np.array([v if v is not None else np.nan for v in gor_vals], dtype=float)
    ax2.plot(x_idx, gor_numeric, color=_COL_GOR, linewidth=1.5, label="GOR (scf/stb)")
    ax2.fill_between(x_idx, gor_numeric, alpha=0.15, color=_COL_GOR)

    # Threshold bands (relative — draw as flat reference lines for anomaly context)
    if not np.all(np.isnan(gor_numeric)):
        gor_mean = float(np.nanmean(gor_numeric))
        ax2.axhline(gor_mean * 1.20, color=_RAG_COLOURS["AMBER"], linewidth=0.8,
                    linestyle="--", alpha=0.7, label="+20% from mean (AMBER)")
        ax2.axhline(gor_mean * 1.40, color=_RAG_COLOURS["RED"], linewidth=0.8,
                    linestyle="--", alpha=0.7, label="+40% from mean (RED)")

    ax2.set_ylabel("GOR scf/stb", fontsize=9)
    ax2.set_title("Gas-Oil Ratio Trend", fontsize=9, pad=4)
    _set_xticks(ax2, labels, x_idx)
    ax2.legend(fontsize=6, facecolor=_SURFACE, edgecolor=_BORDER,
               labelcolor=_TEXT, loc="upper left", ncol=2)

    # ── Panel 3: Water cut ────────────────────────────────────────────────────
    wc_numeric = np.array([v if v is not None else np.nan for v in wc_vals], dtype=float)
    ax3.plot(x_idx, wc_numeric, color=_COL_WC, linewidth=1.5, label="WC %")
    ax3.fill_between(x_idx, wc_numeric, alpha=0.15, color=_COL_WC)
    ax3.set_ylim(0, max(100.0, float(np.nanmax(wc_numeric)) * 1.15) if not np.all(np.isnan(wc_numeric)) else 100)

    ax3.set_ylabel("Water cut %", fontsize=9)
    ax3.set_title("Water Cut Trend", fontsize=9, pad=4)
    _set_xticks(ax3, labels, x_idx)

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    log.info("Saved well chart: %s", output_path)
    return output_path


def _set_xticks(ax: Any, labels: list[str], x_idx: Any) -> None:
    """Show every Nth label so they don't overlap."""
    import numpy as np
    n = len(labels)
    step = max(1, n // 10)
    visible = list(range(0, n, step))
    if (n - 1) not in visible:
        visible.append(n - 1)
    ax.set_xticks([x_idx[i] for i in visible])
    ax.set_xticklabels([labels[i][:7] for i in visible], rotation=45, ha="right", fontsize=7)


# ── Fleet summary matplotlib PNG ─────────────────────────────────────────────

def generate_fleet_summary_chart(
    well_cards: list[dict],
    output_path: str,
) -> str | None:
    """
    Render a fleet-level summary bar chart (production by well, coloured by RAG status).
    Saved as a PNG for embedding in the MD report.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        log.warning("matplotlib not installed — skipping fleet summary chart")
        return None

    if not well_cards:
        return None

    # Sort descending by current rate
    cards = sorted(
        well_cards,
        key=lambda c: c.get("metrics", {}).get("current_rate_boepd", 0),
        reverse=True,
    )
    names   = [c.get("well_name", "?") for c in cards]
    rates   = [c.get("metrics", {}).get("current_rate_boepd", 0) for c in cards]
    statuses = [c.get("rag_status", "GREEN") for c in cards]
    colours  = [_RAG_COLOURS.get(s, _MUTED) for s in statuses]

    fig, ax = plt.subplots(figsize=(max(8, len(names) * 0.9), 5), facecolor=_BG)
    ax.set_facecolor(_SURFACE)
    ax.tick_params(colors=_MUTED, labelsize=9)
    for sp in ax.spines.values():
        sp.set_color(_BORDER)

    x = np.arange(len(names))
    bars = ax.bar(x, rates, 0.65, color=colours, alpha=0.90)

    # Rate labels
    for bar, rate in zip(bars, rates):
        if rate > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(rates) * 0.01,
                    f"{rate:,.0f}", ha="center", va="bottom", fontsize=8, color=_TEXT)

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9, color=_TEXT)
    ax.set_ylabel("Current Rate (boe/d)", fontsize=10, color=_MUTED)
    ax.set_title("Fleet Production by Well", fontsize=12, color=_TEXT, pad=8)

    # Legend
    from matplotlib.patches import Patch
    legend_handles = [Patch(facecolor=_RAG_COLOURS[s], label=s) for s in ("GREEN", "AMBER", "RED", "BLACK")]
    ax.legend(handles=legend_handles, fontsize=8, facecolor=_SURFACE,
              edgecolor=_BORDER, labelcolor=_TEXT, loc="upper right")

    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    log.info("Saved fleet summary chart: %s", output_path)
    return output_path


# ── Plotly fleet HTML dashboard ───────────────────────────────────────────────

def generate_fleet_dashboard(
    well_cards: list[dict],
    output_path: str,
    deal_name: str = "",
) -> str | None:
    """
    Generate a Plotly HTML fleet dashboard with 2×2 grid:
      - Top-left:  RAG summary table (sortable)
      - Top-right: Production overlay line chart (all wells, toggleable)
      - Bot-left:  Scatter — DCA EUR vs. CPR EUR (colour = RAG)
      - Bot-right: Waterfall — fleet rate by well (descending)

    Returns the saved file path, or None if plotly unavailable.
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import numpy as np
    except ImportError:
        log.warning("plotly not installed — skipping fleet dashboard")
        return None

    if not well_cards:
        log.debug("No well cards — skipping fleet dashboard")
        return None

    cards = sorted(
        well_cards,
        key=lambda c: c.get("metrics", {}).get("current_rate_boepd", 0),
        reverse=True,
    )

    # ── Colour map ────────────────────────────────────────────────────────────
    def _rag_hex(status: str) -> str:
        return _RAG_COLOURS.get(status, _MUTED)

    # ── Build subplot grid ────────────────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("RAG Status Table", "Production Overlay",
                        "DCA EUR vs CPR EUR", "Fleet Rate by Well"),
        specs=[
            [{"type": "table"}, {"type": "scatter"}],
            [{"type": "scatter"}, {"type": "bar"}],
        ],
        horizontal_spacing=0.08,
        vertical_spacing=0.14,
    )

    # ── Top-left: RAG table ───────────────────────────────────────────────────
    table_headers = ["Well", "Rate (boe/d)", "EUR (MMboe)", "vs CPR", "Status", "Top Flag"]
    table_rows: list[list] = [[], [], [], [], [], []]

    for card in cards:
        m  = card.get("metrics", {})
        dc = card.get("decline_curve", {})
        rag = card.get("rag_status", "GREEN")
        table_rows[0].append(card.get("well_name", "?"))
        table_rows[1].append(f"{m.get('current_rate_boepd', 0):,.0f}")
        table_rows[2].append(f"{dc.get('eur_mmboe', 0):.2f}")
        eur_vs_cpr = dc.get("eur_vs_cpr_2p_pct")
        table_rows[3].append(f"{eur_vs_cpr:+.0f}%" if eur_vs_cpr is not None else "N/A")
        emoji = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴", "BLACK": "⚫"}.get(rag, "")
        table_rows[4].append(f"{emoji} {rag}")
        flags = card.get("flags", [])
        top_flag = flags[0][:60] + "…" if flags and len(flags[0]) > 60 else (flags[0] if flags else "")
        table_rows[5].append(top_flag)

    cell_colours_col = [
        [_rag_hex(c.get("rag_status", "GREEN")) + "33"] * len(cards)
        for _ in range(len(table_headers))
    ]

    fig.add_trace(
        go.Table(
            header=dict(
                values=[f"<b>{h}</b>" for h in table_headers],
                fill_color="#161b22",
                font=dict(color="#e6edf3", size=11),
                align="left",
                line_color="#30363d",
            ),
            cells=dict(
                values=table_rows,
                fill_color=cell_colours_col,
                font=dict(color="#e6edf3", size=10),
                align="left",
                line_color="#30363d",
                height=24,
            ),
        ),
        row=1, col=1,
    )

    # ── Top-right: Production overlay lines ───────────────────────────────────
    for card in cards:
        hist = card.get("_production_history", [])
        if not hist:
            continue
        periods = [p["period"] for p in hist]
        rates   = [p.get("boe_norm", p.get("boe_boepd", 0)) for p in hist]
        rag     = card.get("rag_status", "GREEN")
        fig.add_trace(
            go.Scatter(
                x=periods, y=rates,
                mode="lines",
                name=card.get("well_name", "?"),
                line=dict(color=_rag_hex(rag), width=1.8),
                hovertemplate="%{x}: %{y:,.0f} boe/d<extra>%{fullData.name}</extra>",
            ),
            row=1, col=2,
        )

    # ── Bot-left: EUR scatter ─────────────────────────────────────────────────
    for card in cards:
        dc  = card.get("decline_curve", {})
        eur = dc.get("eur_mmboe")
        res = card.get("_reserve_estimates", {})
        cpr = res.get("2P")
        if eur is None:
            continue
        rag  = card.get("rag_status", "GREEN")
        name = card.get("well_name", "?")
        fig.add_trace(
            go.Scatter(
                x=[cpr], y=[eur],
                mode="markers+text",
                marker=dict(color=_rag_hex(rag), size=12, line=dict(color="#ffffff33", width=1)),
                text=[name], textposition="top center",
                textfont=dict(size=9, color="#e6edf3"),
                showlegend=False,
                hovertemplate=f"{name}<br>DCA EUR: %{{y:.2f}} MMboe<br>CPR 2P: %{{x:.2f}} MMboe<extra></extra>",
            ),
            row=2, col=1,
        )

    # 45° parity line
    eur_vals = [c.get("decline_curve", {}).get("eur_mmboe", 0) for c in cards if c.get("decline_curve", {}).get("eur_mmboe")]
    if eur_vals:
        max_v = max(eur_vals) * 1.2
        fig.add_trace(
            go.Scatter(x=[0, max_v], y=[0, max_v], mode="lines",
                       line=dict(dash="dot", color=_MUTED, width=1),
                       showlegend=False, name="Parity"),
            row=2, col=1,
        )

    # ── Bot-right: Waterfall bar chart ────────────────────────────────────────
    names_sorted = [c.get("well_name", "?") for c in cards]
    oil_r  = [c.get("metrics", {}).get("current_rate_boepd", 0) for c in cards]
    colors_ = [_rag_hex(c.get("rag_status", "GREEN")) for c in cards]

    fig.add_trace(
        go.Bar(
            x=names_sorted,
            y=oil_r,
            marker_color=colors_,
            text=[f"{r:,.0f}" for r in oil_r],
            textposition="outside",
            textfont=dict(size=9, color="#e6edf3"),
            showlegend=False,
            hovertemplate="%{x}: %{y:,.0f} boe/d<extra></extra>",
        ),
        row=2, col=2,
    )

    # ── Layout ────────────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text=f"Fleet Performance Dashboard — {deal_name}" if deal_name else "Fleet Performance Dashboard",
            font=dict(size=15, color="#e6edf3"),
        ),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        font=dict(color="#8b949e", size=10),
        height=900,
        showlegend=True,
        legend=dict(
            bgcolor="#161b22", bordercolor="#30363d", font=dict(color="#e6edf3", size=9),
        ),
    )

    # Axis styling
    for row in (1, 2):
        for col in (1, 2):
            try:
                fig.update_xaxes(
                    gridcolor=_BORDER, linecolor=_BORDER, zerolinecolor=_BORDER,
                    tickfont=dict(color=_MUTED, size=9), row=row, col=col,
                )
                fig.update_yaxes(
                    gridcolor=_BORDER, linecolor=_BORDER, zerolinecolor=_BORDER,
                    tickfont=dict(color=_MUTED, size=9), row=row, col=col,
                )
            except Exception:
                pass

    for ann in fig.layout.annotations:
        ann.font.color = "#e6edf3"
        ann.font.size  = 12

    # EUR scatter axis labels
    fig.update_xaxes(title_text="CPR 2P EUR (MMboe)", row=2, col=1)
    fig.update_yaxes(title_text="DCA EUR (MMboe)", row=2, col=1)
    fig.update_xaxes(title_text="Well", row=2, col=2)
    fig.update_yaxes(title_text="boe/d", row=2, col=2)
    fig.update_yaxes(title_text="boe/d", row=1, col=2)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path, include_plotlyjs="cdn", full_html=True)
    log.info("Saved fleet dashboard: %s", output_path)
    return output_path
