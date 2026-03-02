# Agent 07 — Well Performance Intelligence Cards
## Spec v1.0 | 01 Mar 2026
**Target file:** `plan_docs/aigis-agent-07-well-cards-spec.md`

---

## Context

Agent 07 is specified in the EasyWins document as a Quick Win (Tier 1, Sprint 3). The concept: generate one-page "Well Intelligence Cards" per well, plus a fleet-level portfolio summary — mimicking how a senior reservoir engineer or COO approaches well performance review in M&A DD.

This spec expands the original EasyWins concept with: native scipy-based DCA (Arps), like-for-like downtime normalization, LLM-driven anomaly narrative, traffic-light RAG rating, matplotlib PNGs + Plotly HTML dashboard, and self-learning memory.

**Design decisions (pre-confirmed):**
- DCA: scipy.optimize.curve_fit for Arps fitting; LLM writes narrative + flags anomalies
- Charts: matplotlib PNGs (embedded in MD report) + Plotly HTML fleet dashboard
- Downtime default: strip estimated downtime; GoM 90% uptime if no VDR data; flag assumption
- Mode: `well_name` provided → single-well JSON card; omitted → full fleet run (standalone only)

---

## Reservoir Engineer Mental Model (Research Basis)

Expert DD workflow:
1. Assemble & clean production history — monthly actuals; exclude shut-ins, choke events; compute on-stream factor
2. Normalize for downtime — rate = cumulative / producing_days; flag if uptime < 85%
3. Fit multi-segment Arps decline curve: early hyperbolic (transient) → BDF → terminal exponential (Dmin 2–8%/yr)
4. Validate b-factor vs. geology — water-drive should show b=0.1–0.3; solution-gas drive b=0.6–0.95; mismatch = red flag
5. Cross-check CPR EUR — DCA EUR vs. CPR 2P; variance >±15% requires explanation
6. Trend surveillance — GOR rising >20%/yr (gas coning); WC rising >10 ppts/yr (water breakthrough); rate below type curve (skin/compartmentalization)
7. Infrastructure context — host platform capacity, tie-back distance, lease expiry
8. Assign RAG: GREEN (±10% forecast), AMBER (−10% to −25%), RED (>−25% or critical anomaly), BLACK (shut-in)

**GoM deepwater benchmarks (DK-grounded):**
- Initial decline: 15–25%/yr; terminal: 3–6%/yr
- b-factor: 0.3–0.7 for deepwater Miocene sands with partial water support
- Uptime: 88–92% for subsea tie-backs; < 85% = operational red flag

---

## Architecture

### Class & File Structure

```
aigis_agents/agent_07_well_cards/
  __init__.py
  agent.py                  ← Agent07(AgentBase) — _run() orchestrator
  __main__.py               ← CLI entry point
  dca_engine.py             ← scipy Arps fitting, EUR projection, DCAResult dataclass
  production_processor.py  ← DB queries (Agent 02 SQLite), downtime normalization, GOR/WC calc
  rag_classifier.py         ← Traffic-light classification, RAGResult dataclass
  chart_generator.py        ← matplotlib per-well charts + Plotly fleet dashboard
  well_card_builder.py      ← Assembles WellCard dict per well (calls LLM for narrative)
  report_generator.py       ← MD report assembly + chart embedding
```

### Agent Class

```python
class Agent07(AgentBase):
    AGENT_ID = "agent_07"
    DK_TAGS  = ["technical", "upstream_dd", "oil_gas_101"]
    # Loads: technical_analyst_playbook.md, upstream_vdr_playbook.md, Upstream Oil & Gas 101*.md
```

### _run() Signature

```python
def _run(
    self,
    deal_id:              str,
    main_llm,
    dk_context:           str,
    buyer_context:        str,
    deal_context:         str,
    entity_context:       str,
    patterns:             list[dict],
    mode:                 str   = "standalone",
    output_dir:           str   = "./outputs",
    well_name:            str | None = None,    # None → fleet; str → single-well
    downtime_treatment:   str   = "strip_estimated",
    default_uptime_pct:   float = 90.0,
    forecast_case:        str   = "cpr_base_case",
    economic_limit_boepd: float = 25.0,
    projection_years:     int   = 20,
    **_,
) -> dict:
```

---

## Sub-Component Specifications

### 1. `production_processor.py`

Queries Agent 02's SQLite DB directly (same `get_connection()` / `query_all()` helpers from `db_manager.py`):

```python
from aigis_agents.agent_02_data_store.db_manager import get_connection, query_all

def load_well_names(deal_id, output_dir) -> list[str]:
    sql = "SELECT DISTINCT entity_name FROM production_series WHERE deal_id=? AND entity_name IS NOT NULL"

def load_production_series(deal_id, well_name, output_dir) -> pd.DataFrame:
    sql = """SELECT period_start, product, value_normalised, case_name
             FROM production_series WHERE deal_id=? AND entity_name=?
             ORDER BY period_start ASC"""

def load_reserve_estimates(deal_id, well_name, output_dir) -> dict:
    sql = """SELECT reserve_class, product, value_normalised, effective_date, reserve_engineer
             FROM reserve_estimates WHERE deal_id=? AND entity_name=?"""

def load_scalar_metrics(deal_id, well_name, output_dir) -> dict:
    sql = """SELECT metric_name, value, unit FROM scalar_datapoints
             WHERE deal_id=? AND (metric_key LIKE ? OR context LIKE ?)"""
```

**Downtime normalization:**
```python
def normalize_production(monthly_df, uptime_data=None, default_uptime=0.90):
    # Formula: rate_normalized = rate_actual / uptime_factor
    # If no uptime_data: apply default_uptime and append flag
    # Returns (normalized_df, assumption_flags: list[str])
```

**Secondary metrics:**
```python
def compute_secondary_metrics(df) -> pd.DataFrame:
    df["gor"] = df["gas_mmcfd"] * 1000 / df["oil_bopd"].replace(0, np.nan)
    df["wc_pct"] = df["water_bwpd"] / (df["water_bwpd"] + df["oil_bopd"]) * 100
    df["gor_12m_trend_pct"] = df["gor"].pct_change(12) * 100
    df["wc_12m_trend_ppts"] = df["wc_pct"].diff(12)
```

---

### 2. `dca_engine.py`

```python
from scipy.optimize import curve_fit

def arps_hyperbolic(t, qi, Di, b):
    """q(t) = qi / (1 + b*Di*t)^(1/b)  [t in months]"""

def arps_exponential(t, qi, Di):
    """q(t) = qi * exp(-Di * t)"""

def compute_eur(qi, Di, b, economic_limit, projection_months) -> float:
    """Integrate q(t) to abandonment (q < economic_limit)."""

def fit_decline_curve(times, rates, economic_limit=25.0, projection_years=20) -> DCAResult:
    """
    Fit Arps hyperbolic with GoM parameter bounds:
      qi: [0, inf], Di: [0.001, 0.5]/month, b: [0.05, 1.0]
    Falls back to exponential if curve_fit fails.
    DCAResult: qi, Di_annual_pct, b_factor, eur_mmboe, fit_r2, curve_type, insufficient_data
    Flag if b > 0.8 (anomalous — cross-check geology in LLM step).
    """
```

**LLM narrative prompt pattern (called from `well_card_builder.py`):**
```python
DCA_REVIEW_PROMPT = """
You are a senior reservoir engineer. Review this DCA for well {well_name}.

DK CONTEXT: {dk_context}
DCA: qi={qi:.0f} boe/d | Di={Di:.1f}%/yr | b={b:.2f} | EUR={eur:.2f} MMboe | R²={r2:.3f}
ENTITY CONTEXT: {entity_context}
CPR 2P EUR: {cpr_eur} MMboe
GOR trend 12mo: {gor_trend:+.1f}% | WC trend 12mo: {wc_trend:+.1f} ppts

Tasks:
1. Validate b-factor vs. stated drive mechanism — flag if inconsistent
2. Comment on Di vs. GoM deepwater benchmarks (15–25%/yr typical initial)
3. If EUR deviates >15% from CPR, state likely cause
4. List top 2–3 reservoir engineering red flags
5. Write 3–4 sentence well card narrative (cite specific numbers)

Return JSON: {"b_flag": str|null, "di_flag": str|null, "eur_flag": str|null,
              "red_flags": list[str], "narrative": str}
"""
```

---

### 3. `rag_classifier.py`

```python
RAG_THRESHOLDS = {
    "outperformer":     +0.10,   # >+10% vs forecast
    "on_track_lower":   -0.10,   # -10% to +10%
    "amber_lower":      -0.25,   # -25% to -10%
    # < -25% → RED
}

SECONDARY_THRESHOLDS = {
    "gor_rise_amber_pct":   20.0,
    "gor_rise_red_pct":     40.0,
    "wc_rise_amber_ppts":    8.0,
    "wc_rise_red_ppts":     15.0,
    "di_steep_amber_pct":   30.0,
    "r2_poor":               0.70,
}

# patterns list[dict] from MemoryManager can override thresholds at runtime
# e.g. {"classification": "gor_threshold", "rule": "gas condensate: GOR rise 30% is normal"}

def classify_well(actual_rate, forecast_rate, gor_trend, wc_trend,
                  di_annual, r2, well_status, patterns) -> RAGResult:
    # Returns RAGResult(status, label, variance_pct, flags, learned_overrides)
```

---

### 4. `chart_generator.py`

**Per-well matplotlib figure (3-panel, 10×8 inches, dark Aigis theme):**
- Panel 1 (50%): Stacked bar oil/gas/water + BOE line + DCA fitted/projected curve + CPR forecast dashed
- Panel 2 (25%): GOR trend + warning/critical horizontal bands
- Panel 3 (25%): Water cut % + threshold bands + CPR forecast WC overlay

**Plotly fleet dashboard (single HTML, 2×2 grid):**
- Top-left: RAG summary table (sortable; well name, rate, EUR, status badge)
- Top-right: Production overlay line chart (all wells, toggle by well)
- Bot-left: Scatter — DCA EUR vs. CPR EUR (colour = RAG status)
- Bot-right: Waterfall — fleet production by well (descending, stacked oil/gas/water)

---

### 5. MD Report Structure (`report_generator.py`)

```markdown
# Well Performance Intelligence Cards — {deal_name}
*Generated: {date} | {N} wells*

## Fleet Overview
[Summary table: total wells, rates, EUR, RAG counts, critical flags]
[Embedded fleet_summary.png]

## RAG Summary Table
[All wells: name, current rate, DCA EUR, vs CPR, RAG badge, top flag]

---
## Individual Well Cards
[Ordered: GREEN → AMBER → RED → BLACK]

### 🟢 [WELL NAME]
[Header: Field | WI% | Status]
[Metrics table: rate, cumulative, EUR, GOR, WC, uptime, decline, b-factor]
[Decline Curve: type | R² | parameters]
![Chart]({well_name}_production.png)
[LLM narrative paragraph]
[Flags list]
[Data quality + assumptions]
---

## Appendix — Methodology
[DCA method, normalization assumptions, RAG thresholds, data sources cited]
```

---

## Return Structures

### Single-well mode (`well_name` provided)
```python
{
    "deal_id": str, "well_name": str,
    "rag_status": "GREEN"|"AMBER"|"RED"|"BLACK", "rag_label": str,
    "metrics": {
        "current_rate_boepd": float, "peak_rate_boepd": float,
        "cumulative_mmboe": float,
        "ip30_boepd": float|None, "ip90_boepd": float|None, "ip180_boepd": float|None,
        "trend_12m_pct": float, "gor_scf_stb": float, "gor_trend_12m_pct": float,
        "water_cut_pct": float, "wc_trend_12m_ppts": float,
        "uptime_pct": float, "uptime_source": "actual"|"assumed",
    },
    "decline_curve": {
        "qi_boepd": float, "Di_annual_pct": float, "b_factor": float,
        "eur_mmboe": float, "eur_vs_cpr_2p_pct": float|None,
        "curve_type": "hyperbolic"|"exponential"|"insufficient_data", "fit_r2": float,
    },
    "flags": list[str], "narrative": str,
    "data_quality": {"months_of_data": int, "completeness_pct": float},
    "_deal_context_section": {...},  # standalone single-well only
}
```

### Fleet mode (`well_name=None`, standalone)
```python
{
    "deal_id": str, "total_wells": int,
    "rag_summary": {"GREEN": int, "AMBER": int, "RED": int, "BLACK": int},
    "fleet_metrics": {
        "total_current_rate_boepd": float, "total_eur_mmboe": float,
        "eur_vs_cpr_pct": float|None, "critical_flag_count": int,
        "weighted_decline_rate_pct": float,
    },
    "well_cards": list[dict],
    "output_paths": {"md_report": str, "html_dashboard": str, "well_charts_dir": str},
    "_deal_context_section": {
        "section_name": "Agent 07 — Well Performance Summary",
        "content": "Fleet: {N} wells | RAG: {G}G/{A}A/{R}R/{B}B | EUR: {eur:.1f} MMboe vs CPR {cpr:.1f} MMboe ({var:+.0%}) | Critical flags: {N}"
    }
}
```

---

## Self-Learning Memory

**`aigis_agents/agent_07_well_cards/memory/learned_patterns.json`** — seed entries:
```json
[
  {"classification": "gom_b_factor_range",
   "rule": "GoM Miocene deepwater sands with partial water support: b typically 0.35–0.65",
   "weight": "MEDIUM"},
  {"classification": "gom_uptime_benchmark",
   "rule": "GoM subsea tie-back: 88–92% uptime typical; <85% warrants operational red flag",
   "weight": "MEDIUM"},
  {"classification": "gor_threshold_gas_condensate",
   "rule": "Gas condensate wells: GOR rising 20–30%/yr is normal retrograde behavior — do not flag AMBER unless also declining faster than type curve",
   "weight": "MEDIUM"}
]
```

AuditLayer generates improvement suggestions (queued for human review via `/review-memory`):
- "b-factor=0.82 flagged AMBER but geologist confirmed normal for this reservoir — suggest raising b_amber threshold to 0.85"
- "CPR EUR variance ±15% may be too tight for old CPRs — suggest ±20% as threshold"

---

## Output Folder Convention (addition to MEMORY.md)
```
outputs/{deal_id}/
  07_well_performance_report.md
  07_fleet_dashboard.html
  07_well_charts/
    {well_name}_production.png
    fleet_summary.png
  _audit_log.jsonl
```

---

## New Dependencies

| Package | Purpose | pyproject.toml group |
|---------|---------|---------------------|
| `scipy>=1.11` | Arps curve fitting | `well_cards` optional |
| `plotly>=5.18` | Fleet dashboard HTML | `well_cards` optional |
| `matplotlib>=3.8` | Per-well charts | `well_cards` optional |
| `pandas>=2.0` | Production DataFrame ops | `well_cards` optional |
| `openpyxl` | Portfolio Excel | Already present (Agent 02) |

---

## Implementation Steps

| Step | File | Action |
|------|------|--------|
| S1 | `aigis_agents/toolkit.json` | Update Agent 07 entry: `mesh_class`, full `input_params`, `dependencies` |
| S2 | `aigis_agents/agent_07_well_cards/__init__.py` | Create package |
| S3 | `aigis_agents/agent_07_well_cards/dca_engine.py` | `DCAResult` dataclass, `arps_hyperbolic()`, `arps_exponential()`, `fit_decline_curve()`, `compute_eur()` |
| S4 | `aigis_agents/agent_07_well_cards/production_processor.py` | DB queries, downtime normalization, GOR/WC computation |
| S5 | `aigis_agents/agent_07_well_cards/rag_classifier.py` | `RAGResult` dataclass, `classify_well()`, threshold constants, pattern override logic |
| S6 | `aigis_agents/agent_07_well_cards/chart_generator.py` | `generate_well_chart()` (matplotlib), `generate_fleet_dashboard()` (Plotly) |
| S7 | `aigis_agents/agent_07_well_cards/well_card_builder.py` | `build_well_card()` — orchestrates S3–S5, calls LLM for narrative/flags via DCA_REVIEW_PROMPT |
| S8 | `aigis_agents/agent_07_well_cards/report_generator.py` | `generate_md_report()` — assembles markdown with embedded chart paths |
| S9 | `aigis_agents/agent_07_well_cards/agent.py` | `Agent07(AgentBase)._run()` — top-level orchestrator; returns dict with `_deal_context_section` |
| S10 | `aigis_agents/agent_07_well_cards/__main__.py` | CLI: `python -m aigis_agents.agent_07_well_cards --deal-id X [--well-name Y]` |
| S11 | `pyproject.toml` | Add `well_cards` optional dependency group |
| S12 | `tests/test_agent07_dca.py` | Arps fit with synthetic data, EUR calculation, edge cases (≤5 pts, all-zeros, single product) |
| S13 | `tests/test_agent07_rag.py` | RAG classification matrix, secondary flag escalation, pattern overrides |
| S14 | `tests/test_agent07_normalization.py` | Downtime stripping (with/without uptime data), GOR/WC computation, flag messages |
| S15 | `tests/test_agent07_charts.py` | Chart file creation (matplotlib Agg backend; no pixel-perfect check) |
| S16 | `tests/test_agent07_integration.py` | Full `Agent07.invoke()` with MockLLM + mock SQLite DB; standalone and tool_call modes |
| S17 | `plan_docs/aigis-agent-07-well-cards-spec.md` | Commit this spec as a plan doc |
| S18 | `memory/MEMORY.md` | Update Agent Status + output folder convention |

---

## Verification

```bash
# After S9 — smoke test
python -m aigis_agents.agent_07_well_cards \
  --deal-id test-deal-001 --output-dir ./outputs --mode standalone
# Confirm: 07_well_performance_report.md, 07_fleet_dashboard.html, 07_well_charts/*.png created

# After S1 — toolkit resolution
python -c "from aigis_agents.mesh.toolkit_registry import ToolkitRegistry; \
           r=ToolkitRegistry(); print(r.get_agent_class('agent_07'))"
# Confirm: resolves to Agent07

# After S16 — tests
python -m pytest tests/test_agent07_*.py -v
# Target: ~55+ tests passing
```

---

*Spec v1.0 — ready for implementation. No existing agents modified. All changes additive.*
