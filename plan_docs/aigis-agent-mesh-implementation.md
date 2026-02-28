# Aigis Agent Mesh — Implementation Log
**Version:** 1.1 | **Date:** 28 Feb 2026 | **Status:** Phases 1–4 Complete (Agent 02 live)
**Companion doc:** `plan_docs/aigis-agent-mesh-framework.md` (approved spec)

---

## Overview

This document records exactly what was built across the three implementation phases
of the Agent Mesh Framework. It supplements the spec document with the actual
file-level changes, key design decisions made during implementation, and a
ready-to-use invocation reference for each migrated agent.

---

## Phase 1 — Mesh Infrastructure (Non-breaking)

**Goal:** Create the full mesh infrastructure without touching any existing agent code.

### Files Created

| File | Purpose |
|------|---------|
| `aigis_agents/toolkit.json` | Registry of all 20 agents. 2 production (`status: "production"`), 18 planned (`status: "planned"`). All agents listed immediately so Agent 06 (Q&A) can discover them. |
| `aigis_agents/mesh/__init__.py` | Exports: `ToolkitRegistry`, `DomainKnowledgeRouter`, `MemoryManager`, `AuditLayer`, `AgentBase` |
| `aigis_agents/mesh/toolkit_registry.py` | Loads `toolkit.json` (LRU-cached). Resolves `mesh_class` and `invoke_fn` by dynamic import. Key methods: `get()`, `list_agents(status)`, `get_agent_class()`, `get_invoke_fn()`, `llm_defaults()`, `dk_tags()` |
| `aigis_agents/mesh/domain_knowledge.py` | Session-cached DK Router. Class-level `_cache` dict lives for process lifetime. `load(tags)` resolves tags → file paths (supports glob wildcards). `build_context_block(tags)` returns formatted string for LLM injection. `refresh=True` forces reload. |
| `aigis_agents/mesh/memory_manager.py` | Atomic JSON-backed memory (temp file + `os.replace()`). Per-agent: `learned_patterns.json`, `improvement_history.json`, `run_history.json`. Global: `aigis_agents/memory/cross_agent_suggestions.json`. Auto-apply unlock: ≥80% approval rate + ≥10 reviews. |
| `aigis_agents/mesh/audit_layer.py` | Dual-LLM auditor. Input audit (before core logic) + Output audit (after). Falls back gracefully if audit LLM fails — never blocks a run. Appends to `{output_dir}/{deal_id}/_audit_log.jsonl`. |
| `aigis_agents/mesh/agent_base.py` | `AgentBase` with full 10-step `invoke()` pipeline. Subclasses set `AGENT_ID`, `DK_TAGS`, implement `_run()`. `mode` and `output_dir` are passed to `_run()` so subclasses can gate file I/O. |
| `aigis_agents/mesh/review_memory.py` | CLI: `--list`, `--review <id>`, `--stats`, `--enable-auto-apply <agent> --threshold 0.85`, `--disable-auto-apply`. Coloured terminal output. |
| `aigis_agents/agent_01_vdr_inventory/memory/learned_patterns.json` | Stub — empty patterns list |
| `aigis_agents/agent_01_vdr_inventory/memory/improvement_history.json` | Stub — zero stats, empty suggestions |
| `aigis_agents/agent_01_vdr_inventory/memory/run_history.json` | Stub — empty runs list |
| `aigis_agents/agent_04_finance_calculator/memory/learned_patterns.json` | Stub — empty patterns list |
| `aigis_agents/agent_04_finance_calculator/memory/improvement_history.json` | Stub — zero stats, empty suggestions |
| `aigis_agents/agent_04_finance_calculator/memory/run_history.json` | Stub — empty runs list |
| `aigis_agents/memory/cross_agent_suggestions.json` | Global pending queue — empty |

### Zero Changes to Existing Code
Both `agent_01_vdr_inventory/agent.py` and `agent_04_finance_calculator/agent.py` were **not touched** in Phase 1. All existing CLI calls continued to work identically.

---

## Phase 2 — Agent 04 Migration (Finance Calculator)

**Goal:** Subclass `AgentBase` in `agent_04/agent.py`. Core math logic unchanged; mesh wrapper added around it.

### Files Modified

#### `aigis_agents/agent_04_finance_calculator/agent.py`

**Added at top:**
```python
from aigis_agents.mesh.agent_base import AgentBase
```

**Added `Agent04(AgentBase)` class** immediately before `compute_single_metric()`.

Key design decisions:

| Decision | Rationale |
|----------|-----------|
| `dk_context` replaces `get_full_context()` | The DK Router loads the same playbook files via `DK_TAGS = ["financial", "oil_gas_101"]`. No logic change — same text, different loader. |
| `main_llm` stored but not yet used | Agent 04 is pure math in Sprint 1. LLM is reserved for future sensitivity narrative synthesis. Keeping it in the interface now means no signature change later. |
| File writes gated on `mode == "standalone"` | In `tool_call` mode (called by another agent), no files written. Both the MD report and JSON result are only produced in standalone. |
| Legacy `finance_calculator_agent()` unchanged | CLI (`python -m aigis_agents.agent_04_finance_calculator`) continues calling the legacy function. No regression risk. |
| `agent_version` bumped to `2.0` in toolkit.json | Signals mesh-ready status. |

**`_run()` signature:**
```python
def _run(self, deal_id, main_llm, dk_context, patterns,
         mode="standalone", output_dir="./outputs",
         inputs=None, run_sensitivity_analysis=True,
         sensitivity_variables=None, **_) -> dict:
```

**Raw output from `_run()` (used by mesh envelope):**
```python
{
    "deal_id", "deal_name", "deal_type", "jurisdiction", "run_timestamp",
    # Key metrics for tool_call consumers:
    "npv_10_usd", "irr_pct", "payback_years", "moic",
    "loe_per_boe", "netback_usd_bbl", "cash_breakeven_usd_bbl",
    "full_cycle_breakeven_usd_bbl", "ev_2p_usd_boe",
    "ev_production_usd_boepd", "eur_mmboe", "government_take_pct",
    "borrowing_base_usd", "flag_count_critical", "flag_count_warning",
    "flags", "sensitivity_variables",
    "output_paths"  # populated in standalone; {} in tool_call
}
```

#### `aigis_agents/toolkit.json`

```diff
- "mesh_class": null,          # agent_04
+ "mesh_class": "aigis_agents.agent_04_finance_calculator.agent.Agent04",
- "agent_version": "1.0",
+ "agent_version": "2.0",
```

### Mesh Invocation — Agent 04

```python
from aigis_agents.agent_04_finance_calculator.agent import Agent04

# Standalone (produces MD + JSON files)
result = Agent04().invoke(
    mode="standalone",
    deal_id="00000000-0000-0000-0000-c004a1000001",
    inputs="./inputs/example_producing_asset_gom.json",
    output_dir="./outputs",
    run_sensitivity_analysis=True,
)

# Tool-call from another agent (no file writes, compact JSON)
result = Agent04().invoke(
    mode="tool_call",
    deal_id="...",
    inputs=financial_inputs_dict,
    run_sensitivity_analysis=False,  # faster
)
print(result["data"]["npv_10_usd"])
print(result["data"]["irr_pct"])
print(result["audit"]["output_score"])
```

---

## Phase 3 — Agent 01 Migration (VDR Inventory)

**Goal:** Subclass `AgentBase` in `agent_01/agent.py`. Inject `main_llm` and `dk_context` into the classification and detection pipeline. Wire novelty proposals through the mesh memory system.

### Files Modified

#### `aigis_agents/agent_01_vdr_inventory/agent.py`

**Added at top:**
```python
from aigis_agents.mesh.agent_base import AgentBase
```

**Added `Agent01(AgentBase)` class** at the end of the file.

Key design decisions:

| Decision | Rationale |
|----------|-----------|
| `main_llm` injected into `batch_classify()` and `detect_novel_documents()` | These functions already accept `llm=` as a kwarg. The mesh now controls which model runs — no internal `get_chat_model()` call needed. |
| `dk_context` replaces `load_primer()` | The DK Router loads `vdr_structure`, `checklist`, `upstream_dd` files — a superset of what `load_primer()` loaded from the local file. The `primer_content=` kwarg already threads through `batch_classify()`, `detect_novel_documents()`, and `propose_primer_updates()`. |
| Memory patterns prepended to `effective_dk` | Confirmed `learned_patterns.json` entries are serialised into the DK context as a `## LEARNED PATTERNS FROM PREVIOUS DEALS` block before being passed to the LLM. Gives the classifier confirmed knowledge without modifying internal functions. |
| Novelty proposals dual-routed | Proposals continue to go into Agent 01's own `add_proposals()` system (checklist acceptance pipeline). **Additionally** routed through `self._memory.queue_suggestion()` so they appear in the global `review_memory.py` CLI for human review alongside all other agents' suggestions. |
| Primer update step remains in standalone only | The `propose_primer_updates()` + `save_primer()` call (which modifies the local `.md` file) only runs in standalone mode. In tool_call, no file mutations occur. |
| File writes gated on `mode == "standalone"` | Inventory JSON, gap report MD, DRL docx — only written in standalone. |
| Legacy `vdr_inventory_agent()` unchanged | CLI continues working. No regression risk. |
| `agent_version` bumped to `2.0` in toolkit.json | Signals mesh-ready status. |

**`_run()` signature:**
```python
def _run(self, deal_id, main_llm, dk_context, patterns,
         mode="standalone", output_dir="./outputs",
         deal_type="producing_asset", jurisdiction="GoM",
         vdr_path=None, vdr_export_csv=None, use_db=True,
         db_connection_string=None, checklist_version="v1.0",
         deal_name=None, buyer_name=None, round_number=1,
         **_) -> dict:
```

**Raw output from `_run()` (used by mesh envelope):**
```python
{
    "deal_id", "deal_name", "deal_type", "jurisdiction", "run_timestamp",
    "total_files",
    # Coverage metrics for tool_call consumers:
    "coverage_score",       # float 0–1: (present_nth + partial_nth) / total_nth
    "present_nth",          # list[str] — item descriptions
    "missing_nth",          # list[str] — item descriptions
    "missing_gth",          # list[str] — item descriptions
    "findings": {
        "present_nth", "partial_nth", "missing_nth",
        "present_gth", "partial_gth", "missing_gth",
        "novel_count", "total_files"
    },
    "novel_proposals",      # list[dict] — ChecklistProposal.model_dump()
    "gap_delta",            # dict | None — filled on repeat runs
    "cost_usd",
    "primer_updates_count",
    "output_paths"          # populated in standalone; {} in tool_call
}
```

#### `aigis_agents/toolkit.json`

```diff
- "mesh_class": null,          # agent_01
+ "mesh_class": "aigis_agents.agent_01_vdr_inventory.agent.Agent01",
- "agent_version": "1.2",
+ "agent_version": "2.0",
```

#### `aigis_agents/mesh/agent_base.py`

Minor update: `mode` and `output_dir` now passed from `invoke()` into `_run()`:

```python
raw_output = self._run(
    deal_id=deal_id,
    main_llm=main_llm,
    dk_context=dk_context,
    patterns=patterns,
    mode=mode,         # added in Phase 3 prep
    output_dir=output_dir,  # added in Phase 3 prep
    **inputs,
)
```

### Mesh Invocation — Agent 01

```python
from aigis_agents.agent_01_vdr_inventory.agent import Agent01

# Standalone (produces inventory JSON, gap report MD, DRL docx)
result = Agent01().invoke(
    mode="standalone",
    deal_id="00000000-0000-0000-0000-c005a1000001",
    deal_type="producing_asset",
    jurisdiction="GoM",
    vdr_path="/path/to/corsair_vdr",
    output_dir="./outputs",
    deal_name="Project Corsair",
    buyer_name="Aigis Analytics",
)

# Tool-call from another agent (returns coverage metrics, no file writes)
result = Agent01().invoke(
    mode="tool_call",
    deal_id="...",
    deal_type="producing_asset",
    jurisdiction="GoM",
    use_db=True,
)
print(result["data"]["coverage_score"])
print(result["data"]["missing_nth"])
print(result["audit"]["output_score"])
```

---

## Cross-Agent Tool-Call Pattern

Once both agents are migrated, Agent 06 (or any other agent) can call them:

```python
class Agent06(AgentBase):
    AGENT_ID = "agent_06"
    DK_TAGS  = ["upstream_dd", "golden_questions"]

    def _run(self, deal_id, main_llm, dk_context, patterns,
             mode, output_dir, **inputs):
        # Get VDR inventory results
        vdr_result = self.call_agent("agent_01", deal_id=deal_id,
                                     deal_type=inputs["deal_type"],
                                     jurisdiction=inputs["jurisdiction"])

        # Get financial metrics
        fin_result = self.call_agent("agent_04", deal_id=deal_id,
                                     inputs=inputs.get("financial_inputs"))

        coverage  = vdr_result["data"]["coverage_score"]
        npv_10    = fin_result["data"]["npv_10_usd"]
        missing   = vdr_result["data"]["missing_nth"]
        ...
```

---

## Memory Review CLI — Quick Reference

```bash
# See all pending improvement suggestions
python -m aigis_agents.mesh.review_memory --list

# Filter by agent
python -m aigis_agents.mesh.review_memory --list --agent agent_01

# Review a specific suggestion interactively (approve / modify / reject)
python -m aigis_agents.mesh.review_memory --review s001abcd

# See approval stats for all agents
python -m aigis_agents.mesh.review_memory --stats

# Enable auto-apply once approval rate ≥ 80% and n ≥ 10
python -m aigis_agents.mesh.review_memory --enable-auto-apply agent_01 --threshold 0.85
```

---

## Validation Checks Passed

```
[OK] All mesh imports resolve
[OK] agent_01 mesh_class → Agent01 class
[OK] agent_04 mesh_class → Agent04 class
[OK] Both are AgentBase subclasses
[OK] Agent01.DK_TAGS = ['vdr_structure', 'checklist', 'upstream_dd']
[OK] Agent04.DK_TAGS = ['financial', 'oil_gas_101']
[OK] Legacy functions still importable (backward compat confirmed)
[OK] Planned agents return None from get_agent_class() (no premature resolution)
```

---

---

## Phase 4 — Agent 02: VDR Financial & Operational Data Store

**Goal:** Build Agent 02 from scratch on `AgentBase`. Merges planned Agent 02 (Production Data Collator) and Agent 03 (Internal Consistency Auditor) into one comprehensive data store agent. Agent 03 entry removed from toolkit.json.

**Spec:** `plan_docs/aigis-agent-02-data-store-spec.md`

### Files Created

| File | Purpose |
|------|---------|
| `agent_02_data_store/__init__.py` | Lazy loader — `from aigis_agents.agent_02_data_store import Agent02` |
| `agent_02_data_store/models.py` | Pydantic models for all 13 DB tables + enums (FileType, PeriodType, Product, SheetType, CaseType, ConflictSeverity, etc.) |
| `agent_02_data_store/db_manager.py` | SQLite schema creation, connection management, bulk insert helpers for all 13 tables. Uses WAL mode + foreign keys. UNIQUE constraints on natural keys with `ON CONFLICT REPLACE`. |
| `agent_02_data_store/excel_ingestor.py` | Two-pass openpyxl (formulas + cached values). Cell-level `excel_cells` storage. Header detection (≥60% alpha ratio). Circular ref detection (cached `#` values). |
| `agent_02_data_store/pdf_ingestor.py` | pdfplumber table extraction. LLM labels each table (metric, unit, period, category). Routes to typed tables. Heuristic fallback. |
| `agent_02_data_store/csv_ingestor.py` | pandas multi-encoding fallback. LLM or heuristic column classification. Period parsing (YYYY/YYYY-MM/month-year formats). |
| `agent_02_data_store/semantic_classifier.py` | `make_classify_fn()` for Excel sheet classification. LLM + heuristic keyword fallback for SheetType, PeriodType, primary metric. |
| `agent_02_data_store/unit_normaliser.py` | Static conversion tables: production → boepd, volumes → boe, currency → USD, costs → USD/boe. Agent 04 delegation hook for complex conversions. 6:1 MCF:BOE (SPE/SEC standard). |
| `agent_02_data_store/file_selector.py` | Agent 01 integration (tool_call) + heuristic filename/regex fallback. `INGEST_CATEGORIES` whitelist. Extension priority ordering. |
| `agent_02_data_store/consistency_checker.py` | Cross-source conflict detection on production, financial, reserve tables. CRITICAL >20%, WARNING 5–20%, INFO 1–5%. Writes to `data_conflicts`. |
| `agent_02_data_store/formula_engine.py` | xlcalculator wrapper + Agent 04 delegation. Override resolution (semantic label → cell address via DB). Auto-selects engine based on output cell keywords (npv/irr → Agent 04). |
| `agent_02_data_store/query_engine.py` | NL→SQL (main LLM translates, audit LLM validates). Direct SQL mode with blocked-keyword guard. Summary mode when no query given. |
| `agent_02_data_store/report_generator.py` | Standalone mode: `02_ingestion_report.md` + `02_conflict_report.md` with severity-banded tables. |
| `agent_02_data_store/pg_sync.py` | Optional PostgreSQL sync. Per-deal schema (`deal_{id16}`). TEXT column fallback for schema-agnostic UPSERT. Explicit `--sync-db` or `pg_sync=True` only. |
| `agent_02_data_store/agent.py` | `Agent02(AgentBase)`. `_run()` dispatches to `_ingest_vdr()`, `_ingest_file()`, `_query()`. `_ingest_single_file()` handles all three parsers with unified source_documents registration. |
| `agent_02_data_store/__main__.py` | Full CLI. All 3 operation modes + `--list-data` shorthand, `--scenario`, `--sync-db`, `--format table|json`. |
| `agent_02_data_store/memory/learned_patterns.json` | Stub — empty patterns list |
| `agent_02_data_store/memory/improvement_history.json` | Stub — zero stats, empty suggestions |
| `agent_02_data_store/memory/run_history.json` | Stub — empty runs list |

### toolkit.json Changes

- `agent_02`: `status: "planned"` → `status: "production"`, full `mesh_class`, `input_params`, `output` schema, expanded `dependencies`
- `agent_03`: **REMOVED** — consistency auditing built into Agent 02
- `agent_05`, `agent_06`, `agent_14`, `agent_15`, `agent_17`, `agent_19`: agent_03 dependency references updated to agent_02

### Key Design Decisions

| Decision | Choice |
|----------|--------|
| Agent 03 merge | Consistency audit as post-ingestion step within Agent 02, not a separate agent |
| Formula engine | Hybrid: xlcalculator for operational tables, Agent 04 for NPV/IRR |
| Data conflicts | Case tagging — all cases stored with provenance; analyst picks winner |
| PostgreSQL sync | Opt-in only (`pg_sync=True`); never runs automatically |
| NL→SQL safety | Audit LLM validates + blocked-keyword regex before execution |

### Discoverability — How Other Agents Call Agent 02

```python
# Via AgentBase.call_agent() — works immediately for any mesh agent
result = self.call_agent("agent_02", deal_id=deal_id,
                         operation="query",
                         query_text="2P reserves by case")

# Via ToolkitRegistry directly
cls = ToolkitRegistry.get_agent_class("agent_02")  # → Agent02 class
assert cls is not None   # ✅ mesh_class set, class importable
```

---

## What Comes Next

| Phase | Deliverable | Notes |
|-------|------------|-------|
| 5 | Agent 06 — Q&A Synthesis Engine | First conversational agent. Calls Agent 01, 02, 04 via `call_agent()`. DK_TAGS: `["upstream_dd", "golden_questions", "dd_process_full"]`. |
| 5 | Agent 08 — HSE Red Flag Scanner | Sprint 1 completion. DK_TAGS: `["technical", "upstream_dd"]`. |
| Future | SQLite swap for MemoryManager | When agent count warrants it. `MemoryManager` interface unchanged — single-class swap. |
| Future | Auto-apply unlock | When `approval_rate ≥ 0.80` and `n ≥ 10` reviews for an agent, `review_memory --stats` surfaces the enable option. |

---

*Last updated: 28 February 2026 — Phases 1, 2, 3, 4 complete. 3 agents in production (01, 02, 04).*
