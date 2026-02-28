# Aigis Agents — Test Suite Results
**Date:** 28 February 2026
**Run:** `pytest tests/ -v --tb=short`
**Environment:** Python 3.11.9 / pytest 9.0.2 / Windows 11
**Result: ✅ 180 passed, 0 failed, 0 errors in 3.65s**

---

## Summary

| Category | Tests | Pass | Fail |
|----------|------:|-----:|-----:|
| Mesh infrastructure | 53 | 53 | 0 |
| Agent 01 (VDR Inventory) | 10 | 10 | 0 |
| Agent 02 (Data Store) | 43 | 43 | 0 |
| Agent 04 (Finance Calculator) | 56 | 56 | 0 |
| Integration | 18 | 18 | 0 |
| **Total** | **180** | **180** | **0** |

---

## Test Files & Coverage

### Mesh Infrastructure (`tests/mesh/`)

| File | Tests | Coverage |
|------|------:|---------|
| `test_toolkit_registry.py` | 13 | load, get, list, llm_defaults, dk_tags, is_production, is_planned, get_agent_class, tool_call_schema, reload_clears_cache |
| `test_domain_knowledge.py` | 9 | available_tags, build_context_block (empty/unknown tags), cache populate/clear/refresh, multiple tags combined, load() |
| `test_memory_manager.py` | 11 | load_patterns, save+deduplicate patterns, log_run, queue_suggestion, get_pending, approve, reject, approval_stats, auto-apply eligibility |
| `test_audit_layer.py` | 9 | valid/invalid inputs, ERROR severity, malformed fallback, output confidence label, improvement suggestions, JSONL log creation/append |
| `test_agent_base.py` | 9 | invoke envelope (status/agent/deal_id/audit/data/run_metadata), no AGENT_ID raises, execution_error envelope, input validation abort |

### Agent Tests (`tests/agents/`)

| File | Tests | Coverage |
|------|------:|---------|
| `test_agent01.py` | 10 | AGENT_ID, DK_TAGS, AgentBase subclass, tool_call success, no file writes in tool_call, data key, standalone mode, None/nonexistent VDR path, audit block |
| `test_agent02_db.py` | 7 | ensure_db creates file, idempotent, get_connection, all 13 tables, upsert_deal creates/updates, insert_source_document |
| `test_agent02_ingest.py` | 14 | AGENT_ID, DK_TAGS, AgentBase subclass, CSV ingest (success/db/doc_id/data_points), Excel ingest (success/source_doc), missing/nonexistent file, invalid operation, standalone mode |
| `test_agent02_query.py` | 10 | direct SQL (rows/NPV), DROP TABLE blocked, DELETE blocked, NL query invokes LLM, result data key, empty query graceful |
| `test_agent02_consistency.py` | 6 | run returns severity dict, no conflict single source, detects CRITICAL (30% discrepancy), CRITICAL written to data_conflicts, <5% discrepancy is INFO, total = sum of severities |
| `test_agent04.py` | 12 | AGENT_ID, DK_TAGS, AgentBase subclass, tool_call success/no-files/NPV/IRR, standalone, NPV numeric, high-cost lower NPV, audit block |

### Integration Tests (`tests/integration/`)

| File | Tests | Coverage |
|------|------:|---------|
| `test_audit_quality.py` | 6 | HIGH quality passes, LOW quality returns success, LOW suggestions queued to memory, ERROR severity aborts before _run(), broken JSON fallback, _cost key stripped from data |
| `test_mesh_integration.py` | 10 | Agent02 scenario query with Agent04, ingest CSV then query data, ingest Excel then query cells, audit log created/valid JSONL/accumulates, call_agent resolves and invokes |

### Pre-existing Tests (`tests/`)

| File | Tests | Coverage |
|------|------:|---------|
| `test_agent_04_calculator.py` | 44 | Decline curves (exponential/hyperbolic/harmonic), lifting cost, netback, cash breakeven, NPV, IRR, cash flow schedule, royalty, government take, fiscal profile, quality flags, FinancialInputs validation |
| `test_agent_04_integration.py` | 27 | Corsair pipeline (status, deal_id, cashflow rows/years, headline metrics, IRR, LOE, PV10, output files, JSON validity, MD sections, deal registry, flags), Coulomb pipeline (status, IRR vs Corsair, critical flags, PV10), registry accumulation |

---

## Bugs Found and Fixed During Test Run

Four production bugs were discovered and fixed during test execution:

### 1. `agent_base.py` — `get_chat_model` not patchable (module import)
**File:** [`aigis_agents/mesh/agent_base.py`](../aigis_agents/mesh/agent_base.py)
**Bug:** `get_chat_model` was imported inside `invoke()` (local scope), making it inaccessible as a module attribute for monkeypatching.
**Fix:** Moved `from aigis_agents.shared.llm_bridge import get_chat_model` to module-level imports.
**Impact:** All 46 `invoke()` tests were failing with `AttributeError: module has no attribute 'get_chat_model'`.

### 2. `agent_04_finance_calculator/agent.py` — Wrong field name on `FinancialQualityFlag`
**File:** [`aigis_agents/agent_04_finance_calculator/agent.py`](../aigis_agents/agent_04_finance_calculator/agent.py) (line 773)
**Bug:** Code accessed `f.metric_name` but `FinancialQualityFlag` Pydantic model defines the field as `metric`.
**Fix:** Changed `f.metric_name` → `f.metric`.
**Impact:** Agent04 `_run()` raised `AttributeError` on every invocation, returning an error response instead of financial results.

### 3. `db_manager.py` — `upsert_deal` did not update `deal_type` / `jurisdiction`
**File:** [`aigis_agents/agent_02_data_store/db_manager.py`](../aigis_agents/agent_02_data_store/db_manager.py)
**Bug:** The `ON CONFLICT DO UPDATE SET` clause only updated `deal_name` and `updated_at`, leaving `deal_type` and `jurisdiction` stale when a deal was re-ingested.
**Fix:** Added `deal_type`, `jurisdiction`, `agent_version` to the ON CONFLICT update clause.
**Impact:** `test_upsert_deal_updates_existing` failed; real-world impact: re-ingesting a deal would silently retain stale deal metadata.

### 4. `test_agent02_consistency.py` — Test used wrong table for conflict fixture
**File:** [`tests/agents/test_agent02_consistency.py`](../tests/agents/test_agent02_consistency.py)
**Bug:** The `conn_with_conflict` fixture inserted two conflicting rows into `production_series`, which has a `UNIQUE(deal_id, case_name, entity_name, period_start, product) ON CONFLICT REPLACE` constraint. The second insert silently replaced the first, leaving only one row — so the consistency checker found no conflict to detect.
**Fix:** Changed fixture to insert conflicting rows into `reserve_estimates` (no compound UNIQUE constraint), which allows multiple rows per (case_name, entity_name, reserve_class, product) from different doc_ids to coexist.
**Design note:** The `production_series` REPLACE constraint means conflict detection for production data must happen at ingestion time (comparing new row against existing before writing), not post-ingestion.

---

## Infrastructure Files Created

All test files were created from scratch (the previous session produced a markdown spec only):

```
tests/
├── helpers.py                    MockLLM, MockMessage, VALID/FAILING audit canned responses
├── conftest.py                   Shared fixtures: mock_llm, deal_id, patch_toolkit,
│                                 patch_get_chat_model, sqlite_conn, sample_excel/csv files
├── mesh/
│   ├── __init__.py
│   ├── test_toolkit_registry.py  13 tests
│   ├── test_domain_knowledge.py  9 tests
│   ├── test_memory_manager.py    11 tests
│   ├── test_audit_layer.py       9 tests
│   └── test_agent_base.py        9 tests
├── agents/
│   ├── __init__.py
│   ├── test_agent01.py           10 tests
│   ├── test_agent02_db.py        7 tests
│   ├── test_agent02_ingest.py    14 tests
│   ├── test_agent02_query.py     10 tests
│   ├── test_agent02_consistency.py 6 tests
│   └── test_agent04.py           12 tests
└── integration/
    ├── __init__.py
    ├── test_audit_quality.py     6 tests
    └── test_mesh_integration.py  10 tests
```

---

## Key Test Infrastructure Design Decisions

| Decision | Rationale |
|----------|-----------|
| `tests/helpers.py` for MockLLM | Avoids `from conftest import` antipattern; `pythonpath = ["tests"]` makes it importable everywhere |
| `patch_toolkit` monkeypatches `_AGENTS_ROOT` | Prevents tests writing memory JSON to the real project directory (Windows `os.replace()` fails with Dropbox locks) |
| `patch_get_chat_model` uses single `MockLLM` for both main+audit LLM | Simplifies test setup; `get_chat_model` is now patched at module level after Fix #1 |
| MockLLM keyword routing | Returns canned JSON based on keyword in `str(messages)`; "add_to_checklist" keyword handles Agent01 novelty detector prompt |
| `reserve_estimates` for conflict test | `production_series` UNIQUE constraint prevents two rows per key coexisting — test uses `reserve_estimates` which has no such constraint |
