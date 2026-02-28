# Agent 02 — VDR Financial & Operational Data Store
## Specification v1.0 | 28 Feb 2026 | Status: Approved
**Author:** Aaditya Chintalapati

---

## Context & Objectives

The Aigis mesh currently has no persistent numerical data layer. Every agent re-extracts numbers from raw documents on each run. This agent creates a **single source of truth** for all financial and operational data in a VDR — a queryable, deal-scoped relational database that every other agent can read from and write to.

This agent **merges and expands** the planned Agent 02 (Production Data Collator → SQL) and Agent 03 (Internal Consistency Auditor) into one comprehensive data store. The consistency auditing function becomes a built-in post-ingestion step rather than a separate agent.

---

## What It Does

| Mode | Operation | Description |
|------|-----------|-------------|
| `ingest_vdr` | Full VDR scan | Walk folder tree, select significant files from gold-standard checklist, extract all numerical data into typed SQL tables |
| `ingest_file` | Single file | Ingest one file, append to deal DB with schema connections to existing data |
| `query` | Data retrieval | Return data from deal DB as structured JSON (NL query or direct SQL) |

### What makes it different from other agents
- **No output documents** in `tool_call` mode — pure data in, data out
- **Cell-level Excel storage** — both `.value` and `.formula` stored for every relevant cell
- **Case system** — every data point tagged with its scenario/case (management, CPR base, conservative, etc.)
- **Conflict detection built-in** — discrepancies across sources flagged automatically on ingestion (merged Agent 03)
- **Hybrid computation engine** — xlcalculator for simple table re-evaluation; Agent 04 for full model scenarios

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent identity | Replaces planned Agent 02 + Agent 03 | Single comprehensive data layer; simpler registry |
| DB backend | SQLite primary, PostgreSQL optional sync | Zero-infra default; existing PostgreSQL for cross-deal analytics |
| Formula execution | Hybrid: xlcalculator + Agent 04 | xlcalculator for operational tables; Agent 04 for NPV/IRR/decline |
| Conflict resolution | Case tagging (no automatic winner) | All cases available for query; analyst decides which to use |

---

## Operation Modes

All three operations use the same `_run()` method, dispatched via the `operation` parameter:

```python
result = Agent02().invoke(
    mode="standalone",          # or "tool_call"
    deal_id="...",
    operation="ingest_vdr",     # or "ingest_file" or "query"
    **operation_specific_inputs
)
```

### Mode 1: `ingest_vdr`

**Inputs:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `vdr_path` | str | Yes | — | Root folder of the VDR |
| `deal_type` | str | Yes | — | producing_asset \| exploration \| development \| corporate |
| `jurisdiction` | str | Yes | — | GoM \| UKCS \| Norway \| International |
| `checklist_version` | str | No | "v1.0" | Gold-standard checklist version |
| `case_name` | str\|None | No | None | Default case tag for all data |
| `overwrite` | bool | No | False | Re-ingest existing files if True |
| `file_filter` | list[str]\|None | No | None | Limit to specific categories |

**Pipeline:**
1. Call Agent 01 (tool_call) to enumerate + classify all VDR files
2. Filter to financially/operationally significant files
3. Per-file: parse → classify semantically → normalise units → write to SQLite
4. Post-ingestion: run consistency check across all newly ingested data
5. Return: files ingested, data points added, conflicts detected

### Mode 2: `ingest_file`

**Inputs:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | str | Yes | — | Absolute path to the file |
| `file_type` | str\|None | No | None | Override: "pdf" \| "excel" \| "csv" |
| `case_name` | str\|None | No | None | Case tag for this file's data |
| `source_doc_hint` | str\|None | No | None | Document type hint ("CPR", "LOS", "financial_model") |
| `sheet_names` | list[str]\|None | No | None | Excel only: sheets to ingest |
| `run_consistency_check` | bool | No | True | Check new data against existing |

### Mode 3: `query`

**Inputs:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query_text` | str\|None | — | — | Natural language query |
| `query_sql` | str\|None | — | — | Direct SQL (for agent calls) |
| `data_type` | str\|None | No | None | Filter: production \| financials \| reserves \| costs \| fiscal |
| `case_name` | str\|None | No | None | Filter by case (default: all) |
| `period_start` | str\|None | No | None | ISO date filter |
| `period_end` | str\|None | No | None | ISO date filter |
| `format` | str | No | "json" | "table" \| "array" \| "json" |
| `include_metadata` | bool | No | True | Include source, confidence, conflicts |
| `scenario` | dict\|None | No | None | Modified assumptions for re-evaluation |

*Either `query_text` or `query_sql` is required.*

**Returns:**
```json
{
  "query": "What was average daily oil production in 2024?",
  "sql_executed": "SELECT ...",
  "data": [...],
  "cases_present": ["management_case", "cpr_base_case"],
  "conflicts": [...],
  "scenario_result": {...},
  "metadata": {"rows": 12, "source_docs": ["CPR_2024.pdf", "LOS_Oct2024.xlsx"]}
}
```

---

## File Selection Logic (`ingest_vdr`)

Agent 01's classification output identifies financially/operationally significant files:

### Checklist categories that trigger ingestion:
```python
INGEST_CATEGORIES = {
    "Financial/Audited Accounts",
    "Financial/Management Accounts",
    "Financial/Financial Model",
    "Production/History",
    "Production/Forecast",
    "Reserves/CPR",
    "Reserves/Competent Person Report",
    "Technical/LOS",
    "Technical/Well Performance",
    "Technical/Production Data",
    "Operations/Monthly Reports",
}
```

### Extension treatment:
| Extension | Treatment |
|-----------|-----------|
| `.xlsx`, `.xlsm`, `.xls` | Full cell-level ingestion (values + formulas) |
| `.csv` | Table ingestion, no formula support |
| `.pdf` | LLM-assisted table extraction + semantic classification |

---

## Database Schema

### Storage
- **Primary:** `{output_dir}/{deal_id}/02_data_store.db` (SQLite)
- **Optional sync:** PostgreSQL `aigis` DB (schema: `deal_{deal_id_short}`)

### Tables (11)

#### `deals` — Deal metadata
```sql
CREATE TABLE IF NOT EXISTS deals (
    deal_id         TEXT PRIMARY KEY,
    deal_name       TEXT NOT NULL,
    deal_type       TEXT NOT NULL,
    jurisdiction    TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    agent_version   TEXT NOT NULL
);
```

#### `source_documents` — Every ingested VDR file
```sql
CREATE TABLE IF NOT EXISTS source_documents (
    doc_id              TEXT PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    filename            TEXT NOT NULL,
    folder_path         TEXT NOT NULL,
    file_type           TEXT NOT NULL,
    doc_category        TEXT,
    doc_label           TEXT,
    source_date         TEXT,
    ingest_timestamp    TEXT NOT NULL,
    ingest_run_id       TEXT NOT NULL,
    case_name           TEXT,
    sheet_count         INT DEFAULT 0,
    table_count         INT DEFAULT 0,
    cell_count          INT DEFAULT 0,
    status              TEXT DEFAULT 'complete',
    error_message       TEXT
);
```

#### `cases` — Named assumption scenarios
```sql
CREATE TABLE IF NOT EXISTS cases (
    case_id         TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    case_name       TEXT NOT NULL,
    case_type       TEXT NOT NULL,
    display_label   TEXT NOT NULL,
    description     TEXT,
    source_doc_id   TEXT REFERENCES source_documents(doc_id),
    created_at      TEXT NOT NULL,
    UNIQUE(deal_id, case_name)
);
```

Standard cases: `management_case`, `cpr_base_case`, `cpr_low_case`, `cpr_high_case`, `conservative_case`, `mid_case`, `base_case`

#### `production_series` — Time-series production data
```sql
CREATE TABLE IF NOT EXISTS production_series (
    id              TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id          TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name       TEXT NOT NULL,
    entity_name     TEXT,
    period_type     TEXT NOT NULL,          -- monthly | quarterly | annual
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    product         TEXT NOT NULL,          -- oil | gas | ngl | water | boe | boepd
    value           REAL NOT NULL,
    unit            TEXT NOT NULL,
    unit_normalised TEXT,
    value_normalised REAL,
    confidence      TEXT DEFAULT 'HIGH',
    source_sheet    TEXT,
    source_cell     TEXT,
    source_page     INT,
    extraction_note TEXT,
    UNIQUE(deal_id, case_name, entity_name, period_start, product) ON CONFLICT REPLACE
);
```

#### `reserve_estimates` — Point-in-time reserve figures
```sql
CREATE TABLE IF NOT EXISTS reserve_estimates (
    id              TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id          TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name       TEXT NOT NULL,
    entity_name     TEXT,
    reserve_class   TEXT NOT NULL,          -- 1P | 2P | 3P | PDP | PNP | PDnP
    product         TEXT NOT NULL,
    value           REAL NOT NULL,
    unit            TEXT NOT NULL,
    unit_normalised TEXT,
    value_normalised REAL,
    effective_date  TEXT,
    report_date     TEXT,
    reserve_engineer TEXT,
    confidence      TEXT DEFAULT 'HIGH',
    source_section  TEXT,
    source_page     INT,
    extraction_note TEXT
);
```

#### `financial_series` — Time-series financial data
```sql
CREATE TABLE IF NOT EXISTS financial_series (
    id              TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id          TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name       TEXT NOT NULL,
    line_item       TEXT NOT NULL,          -- revenue | loe | g_and_a | ebitda | capex | net_income | fcf
    line_item_label TEXT,
    period_type     TEXT NOT NULL,
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    value           REAL NOT NULL,
    unit            TEXT NOT NULL,
    unit_normalised TEXT DEFAULT 'USD',
    value_normalised REAL,
    confidence      TEXT DEFAULT 'HIGH',
    source_sheet    TEXT,
    source_cell     TEXT,
    source_page     INT,
    extraction_note TEXT
);
```

#### `cost_benchmarks` — Per-unit cost metrics
```sql
CREATE TABLE IF NOT EXISTS cost_benchmarks (
    id              TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id          TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name       TEXT NOT NULL,
    metric          TEXT NOT NULL,          -- loe_per_boe | g_and_a_per_boe | transport_per_boe
    period_start    TEXT,
    period_end      TEXT,
    value           REAL NOT NULL,
    unit            TEXT NOT NULL,
    confidence      TEXT DEFAULT 'HIGH',
    source_sheet    TEXT,
    source_cell     TEXT,
    source_page     INT,
    extraction_note TEXT
);
```

#### `fiscal_terms` — Fiscal/contract terms
```sql
CREATE TABLE IF NOT EXISTS fiscal_terms (
    id              TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id          TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name       TEXT NOT NULL,
    term_name       TEXT NOT NULL,          -- royalty_rate | severance_tax | income_tax | wi_pct | nri_pct
    term_label      TEXT,
    value           REAL NOT NULL,
    unit            TEXT NOT NULL,          -- % | ratio | USD
    effective_from  TEXT,
    effective_to    TEXT,
    conditions      TEXT,
    confidence      TEXT DEFAULT 'HIGH',
    source_section  TEXT,
    source_page     INT,
    extraction_note TEXT
);
```

#### `scalar_datapoints` — All other quantitative facts
```sql
CREATE TABLE IF NOT EXISTS scalar_datapoints (
    id              TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id          TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name       TEXT NOT NULL,
    category        TEXT NOT NULL,          -- production | financial | reserve | cost | fiscal | asset | well | other
    metric_name     TEXT NOT NULL,
    metric_key      TEXT,
    value           REAL NOT NULL,
    unit            TEXT NOT NULL,
    as_of_date      TEXT,
    context         TEXT,
    confidence      TEXT DEFAULT 'HIGH',
    source_section  TEXT,
    source_page     INT,
    source_cell     TEXT,
    extraction_note TEXT
);
```

#### `excel_cells` — Cell-level Excel data (values + formulas)
```sql
CREATE TABLE IF NOT EXISTS excel_cells (
    id              TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id          TEXT NOT NULL REFERENCES source_documents(doc_id),
    sheet_name      TEXT NOT NULL,
    cell_address    TEXT NOT NULL,
    row_num         INT NOT NULL,
    col_num         INT NOT NULL,
    raw_value       TEXT,
    numeric_value   REAL,
    formula         TEXT,                   -- e.g. "=SUM(B2:B12)"
    data_type       TEXT,                   -- numeric | text | date | boolean | formula | empty
    number_format   TEXT,
    semantic_label  TEXT,
    semantic_category TEXT,
    unit            TEXT,
    row_header      TEXT,
    col_header      TEXT,
    is_assumption   BOOL DEFAULT FALSE,
    is_output       BOOL DEFAULT FALSE,
    case_name       TEXT,
    UNIQUE(deal_id, doc_id, sheet_name, cell_address)
);
```

#### `excel_sheets` — Sheet-level metadata
```sql
CREATE TABLE IF NOT EXISTS excel_sheets (
    id              TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id          TEXT NOT NULL REFERENCES source_documents(doc_id),
    sheet_name      TEXT NOT NULL,
    sheet_index     INT NOT NULL,
    sheet_type      TEXT,                   -- production | financials | assumptions | summary | dcf | sensitivity | other
    row_count       INT,
    col_count       INT,
    assumption_cells INT DEFAULT 0,
    output_cells    INT DEFAULT 0,
    formula_cells   INT DEFAULT 0,
    ingest_notes    TEXT
);
```

#### `data_conflicts` — Cross-source inconsistencies
```sql
CREATE TABLE IF NOT EXISTS data_conflicts (
    id              TEXT PRIMARY KEY,
    deal_id         TEXT NOT NULL REFERENCES deals(deal_id),
    conflict_type   TEXT NOT NULL,          -- value_mismatch | unit_inconsistency | date_overlap | missing_in_source
    metric_name     TEXT NOT NULL,
    period_start    TEXT,
    period_end      TEXT,
    source_a_doc_id TEXT REFERENCES source_documents(doc_id),
    source_a_case   TEXT,
    source_a_value  REAL,
    source_a_unit   TEXT,
    source_b_doc_id TEXT REFERENCES source_documents(doc_id),
    source_b_case   TEXT,
    source_b_value  REAL,
    source_b_unit   TEXT,
    discrepancy_pct REAL,
    severity        TEXT NOT NULL,          -- CRITICAL (>20%) | WARNING (5-20%) | INFO (<5%)
    resolved        BOOL DEFAULT FALSE,
    resolution_note TEXT,
    detected_at     TEXT NOT NULL
);
```

#### `scenario_runs` — Scenario computation log
```sql
CREATE TABLE IF NOT EXISTS scenario_runs (
    id                      TEXT PRIMARY KEY,
    deal_id                 TEXT NOT NULL REFERENCES deals(deal_id),
    base_case               TEXT NOT NULL,
    scenario_name           TEXT,
    modified_assumptions    TEXT NOT NULL,
    engine                  TEXT NOT NULL,  -- xlcalculator | agent_04 | hybrid
    result_summary          TEXT NOT NULL,
    full_result             TEXT,
    run_timestamp           TEXT NOT NULL,
    cost_usd                REAL DEFAULT 0.0
);
```

#### `ingestion_log` — Full ingestion audit trail
```sql
CREATE TABLE IF NOT EXISTS ingestion_log (
    id                  TEXT PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    operation           TEXT NOT NULL,
    run_id              TEXT NOT NULL,
    timestamp           TEXT NOT NULL,
    files_processed     INT DEFAULT 0,
    data_points_added   INT DEFAULT 0,
    conflicts_detected  INT DEFAULT 0,
    main_model          TEXT,
    audit_model         TEXT,
    cost_usd            REAL DEFAULT 0.0,
    status              TEXT DEFAULT 'complete',
    errors              TEXT
);
```

---

## File Ingestion Pipeline

```
file_path
    │
    ▼
┌──────────────────────────────────┐
│ 1. FILE TYPE DETECTION           │
│    Extension → pdf | excel | csv │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 2. DOCUMENT CLASSIFICATION       │
│    (Main LLM)                    │
│    Doc type, case, effective date│
└──────────────┬───────────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
 Excel                 PDF / CSV
    │                     │
┌──────────┐        ┌──────────────────┐
│ openpyxl │        │ pdfplumber (PDF)  │
│ Pass 1:  │        │ pandas (CSV)      │
│  formulas│        │ LLM table labeling│
│ Pass 2:  │        └────────┬──────────┘
│  values  │                 │
└────┬─────┘                 │
     └──────────┬────────────┘
                │
                ▼
┌──────────────────────────────────┐
│ 3. SEMANTIC CLASSIFICATION       │
│    (Main LLM + dk_context)       │
│    metric, category, unit,       │
│    period, case                  │
│    is_assumption / is_output     │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 4. UNIT NORMALISATION            │
│    Agent 04 for domain-specific  │
│    conversions                   │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 5. WRITE TO SQLite               │
│    Typed tables + excel_cells    │
│    Upsert on UNIQUE constraints  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ 6. CONSISTENCY CHECK             │
│    Compare vs existing data      │
│    Write to data_conflicts       │
└──────────────┘
```

### Excel: Two-pass read (openpyxl)
- **Pass 1** (`data_only=False`) — reads formulas
- **Pass 2** (`data_only=True`) — reads last-computed cached values
- Circular references → logged in `excel_sheets.ingest_notes`, formula stored but xlcalculator skipped

### PDF: pdfplumber + LLM
- Extract tables page-by-page
- LLM labels each table: metric, unit, period, category
- Narrative-only pages skipped

### CSV: pandas
- Multi-encoding fallback (`utf-8-sig`, `utf-8`, `latin-1`)
- LLM classifies each column
- Each row = one time period record

---

## Case System

| case_name | case_type | Description |
|-----------|-----------|-------------|
| `management_case` | management | Seller/operator assumptions |
| `cpr_base_case` | independent | CPR/RPS/ERCE base case |
| `cpr_low_case` | independent | CPR low case |
| `cpr_high_case` | independent | CPR high case |
| `conservative_case` | conservative | Buyer conservative case |
| `mid_case` | mid | Mid-point/consensus |
| `base_case` | management | Default when case not identifiable |

Query returns all cases by default; filter via `case_name` parameter.

---

## Conflict Detection (Merged Agent 03)

Post-ingestion scan, per new file ingested:

| Conflict Type | Trigger | Severity |
|---------------|---------|---------|
| `value_mismatch` | Same metric + period + case, different values | CRITICAL >20%, WARNING 5–20%, INFO <5% |
| `unit_inconsistency` | Same metric + period, incompatible units | WARNING |
| `date_overlap` | Overlapping periods with different values | WARNING |
| `missing_in_source` | Metric in Source A absent from Source B | INFO |

Output: `data_conflicts` table + `02_conflict_report.md` (standalone mode)

---

## Formula Evaluation Engine (Hybrid)

### xlcalculator — for simple operational tables
```python
from xlcalculator import ModelCompiler, Evaluator
model = ModelCompiler().read_and_parse_archive(workbook_path)
evaluator = Evaluator(model)
evaluator.set_cell_value("Assumptions!B5", new_oil_price)
result = evaluator.evaluate("Summary!C12")
```
**When to use:** LOE schedules, revenue re-computation, royalty/tax schedules, simple production tables.

### Agent 04 delegation — for full financial models
```python
fi = self._build_financial_inputs(deal_id, base_case, scenario_overrides)
result = self.call_agent("agent_04", deal_id=deal_id, inputs=fi.model_dump())
```
**When to use:** NPV, IRR, payback, full decline projection, sensitivity analysis.

---

## Query Interface

| Mode | How | Example |
|------|-----|---------|
| Natural language | LLM → SQL (audit LLM validates before execution) | `"Average monthly oil production 2024"` |
| Direct SQL | Parameterised query, no LLM | `"SELECT ... FROM production_series WHERE ..."` |
| Scenario | NL query + `scenario` dict → xlcalculator or Agent 04 | `query_text="NPV10", scenario={"oil_price_usd_bbl": 65}` |

---

## AgentBase Skeleton

```python
class Agent02(AgentBase):
    AGENT_ID = "agent_02"
    DK_TAGS  = ["financial", "technical", "upstream_dd", "oil_gas_101"]

    def _run(self, deal_id, main_llm, dk_context, patterns,
             mode="standalone", output_dir="./outputs",
             operation="ingest_vdr", **inputs) -> dict:
        db_path = self._ensure_db(deal_id, output_dir)
        if operation == "ingest_vdr":   return self._ingest_vdr(...)
        elif operation == "ingest_file": return self._ingest_file(...)
        elif operation == "query":       return self._query(...)
```

---

## toolkit.json Changes

- **Expand `agent_02`** from "Production Data Collator" to full Data Store
- **Remove `agent_03`** — merged into Agent 02's consistency_checker.py
- New `mesh_class`: `"aigis_agents.agent_02_data_store.agent.Agent02"`
- New dependencies: `["agent_01", "agent_04"]`

---

## File Structure

```
aigis_agents/
├── toolkit.json                           MODIFIED
└── agent_02_data_store/                   NEW
    ├── __init__.py
    ├── __main__.py
    ├── agent.py                           Agent02(AgentBase)
    ├── models.py
    ├── db_manager.py                      SQLite schema + connections
    ├── pg_sync.py                         Optional PostgreSQL sync
    ├── file_selector.py                   Calls Agent 01
    ├── excel_ingestor.py                  openpyxl two-pass
    ├── pdf_ingestor.py                    pdfplumber + LLM
    ├── csv_ingestor.py                    pandas
    ├── semantic_classifier.py             LLM prompts
    ├── unit_normaliser.py                 Unit conversion + Agent 04
    ├── consistency_checker.py             Conflict detection
    ├── formula_engine.py                  xlcalculator + Agent 04
    ├── query_engine.py                    NL→SQL + execution
    ├── report_generator.py                Conflict report MD
    └── memory/
        ├── learned_patterns.json
        ├── improvement_history.json
        └── run_history.json
```

---

## New Dependencies

| Package | Purpose |
|---------|---------|
| `openpyxl` | Excel read (values + formulas), two-pass |
| `pdfplumber` | PDF table extraction |
| `xlcalculator` | Python Excel formula evaluation |
| `pandas` | CSV parsing |
| `sqlalchemy` | DB ORM + query builder |
| `psycopg2-binary` | PostgreSQL adapter (optional sync) |

---

## CLI

```bash
# Full VDR ingest
python -m aigis_agents.agent_02_data_store \
    --deal-id <uuid> --operation ingest_vdr \
    --vdr-path /path/to/vdr --deal-type producing_asset --jurisdiction GoM

# Single file
python -m aigis_agents.agent_02_data_store \
    --deal-id <uuid> --operation ingest_file \
    --file-path /path/to/model.xlsx --case-name management_case

# Query
python -m aigis_agents.agent_02_data_store \
    --deal-id <uuid> --operation query \
    --query "Average oil production 2024" --format table

# Scenario
python -m aigis_agents.agent_02_data_store \
    --deal-id <uuid> --operation query --query "NPV10 and IRR" \
    --scenario '{"oil_price_usd_bbl": 65, "loe_per_boe": 18}'
```

---

## Implementation Sequence

| Step | File | Description |
|------|------|-------------|
| 1 | `db_manager.py` | Schema creation, connection management |
| 2 | `models.py` | Pydantic models |
| 3 | `excel_ingestor.py` | Two-pass openpyxl |
| 4 | `pdf_ingestor.py` | pdfplumber + LLM |
| 5 | `csv_ingestor.py` | pandas |
| 6 | `semantic_classifier.py` | LLM labeling prompts |
| 7 | `unit_normaliser.py` | Conversion + Agent 04 |
| 8 | `file_selector.py` | Agent 01 integration |
| 9 | `consistency_checker.py` | Conflict detection |
| 10 | `formula_engine.py` | xlcalculator + Agent 04 |
| 11 | `query_engine.py` | NL→SQL + execution |
| 12 | `report_generator.py` | MD report |
| 13 | `pg_sync.py` | PostgreSQL sync |
| 14 | `agent.py` | Agent02(AgentBase) |
| 15 | `__main__.py` | CLI |
| 16 | `toolkit.json` | Registry update |
| 17 | Memory stubs | Empty JSON files |

---

*Spec v1.0 — 28 Feb 2026 | Replaces: planned Agent 02 + planned Agent 03*
