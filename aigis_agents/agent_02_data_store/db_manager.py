"""
Database manager for Agent 02 — VDR Financial & Operational Data Store.

Handles:
- SQLite schema creation
- Connection management
- Typed insert/upsert helpers
- Per-deal DB file management
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Schema DDL ────────────────────────────────────────────────────────────────

_SCHEMA_DDL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS deals (
    deal_id         TEXT PRIMARY KEY,
    deal_name       TEXT NOT NULL,
    deal_type       TEXT NOT NULL,
    jurisdiction    TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    agent_version   TEXT NOT NULL DEFAULT '1.0'
);

CREATE TABLE IF NOT EXISTS source_documents (
    doc_id              TEXT PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    filename            TEXT NOT NULL,
    folder_path         TEXT NOT NULL DEFAULT '',
    file_type           TEXT NOT NULL,
    doc_category        TEXT,
    doc_label           TEXT,
    source_date         TEXT,
    ingest_timestamp    TEXT NOT NULL,
    ingest_run_id       TEXT NOT NULL,
    case_name           TEXT,
    sheet_count         INTEGER DEFAULT 0,
    table_count         INTEGER DEFAULT 0,
    cell_count          INTEGER DEFAULT 0,
    status              TEXT DEFAULT 'complete',
    error_message       TEXT
);

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

CREATE TABLE IF NOT EXISTS production_series (
    id               TEXT PRIMARY KEY,
    deal_id          TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id           TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name        TEXT NOT NULL,
    entity_name      TEXT,
    period_type      TEXT NOT NULL,
    period_start     TEXT NOT NULL,
    period_end       TEXT NOT NULL,
    product          TEXT NOT NULL,
    value            REAL NOT NULL,
    unit             TEXT NOT NULL,
    unit_normalised  TEXT,
    value_normalised REAL,
    confidence       TEXT DEFAULT 'HIGH',
    source_sheet     TEXT,
    source_cell      TEXT,
    source_page      INTEGER,
    extraction_note  TEXT,
    UNIQUE(deal_id, case_name, entity_name, period_start, product) ON CONFLICT REPLACE
);

CREATE TABLE IF NOT EXISTS reserve_estimates (
    id               TEXT PRIMARY KEY,
    deal_id          TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id           TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name        TEXT NOT NULL,
    entity_name      TEXT,
    reserve_class    TEXT NOT NULL,
    product          TEXT NOT NULL,
    value            REAL NOT NULL,
    unit             TEXT NOT NULL,
    unit_normalised  TEXT,
    value_normalised REAL,
    effective_date   TEXT,
    report_date      TEXT,
    reserve_engineer TEXT,
    confidence       TEXT DEFAULT 'HIGH',
    source_section   TEXT,
    source_page      INTEGER,
    extraction_note  TEXT
);

CREATE TABLE IF NOT EXISTS financial_series (
    id               TEXT PRIMARY KEY,
    deal_id          TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id           TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name        TEXT NOT NULL,
    line_item        TEXT NOT NULL,
    line_item_label  TEXT,
    period_type      TEXT NOT NULL,
    period_start     TEXT NOT NULL,
    period_end       TEXT NOT NULL,
    value            REAL NOT NULL,
    unit             TEXT NOT NULL,
    unit_normalised  TEXT DEFAULT 'USD',
    value_normalised REAL,
    confidence       TEXT DEFAULT 'HIGH',
    source_sheet     TEXT,
    source_cell      TEXT,
    source_page      INTEGER,
    extraction_note  TEXT
);

CREATE TABLE IF NOT EXISTS cost_benchmarks (
    id               TEXT PRIMARY KEY,
    deal_id          TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id           TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name        TEXT NOT NULL,
    metric           TEXT NOT NULL,
    period_start     TEXT,
    period_end       TEXT,
    value            REAL NOT NULL,
    unit             TEXT NOT NULL,
    confidence       TEXT DEFAULT 'HIGH',
    source_sheet     TEXT,
    source_cell      TEXT,
    source_page      INTEGER,
    extraction_note  TEXT
);

CREATE TABLE IF NOT EXISTS fiscal_terms (
    id               TEXT PRIMARY KEY,
    deal_id          TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id           TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name        TEXT NOT NULL,
    term_name        TEXT NOT NULL,
    term_label       TEXT,
    value            REAL NOT NULL,
    unit             TEXT NOT NULL,
    effective_from   TEXT,
    effective_to     TEXT,
    conditions       TEXT,
    confidence       TEXT DEFAULT 'HIGH',
    source_section   TEXT,
    source_page      INTEGER,
    extraction_note  TEXT
);

CREATE TABLE IF NOT EXISTS scalar_datapoints (
    id               TEXT PRIMARY KEY,
    deal_id          TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id           TEXT NOT NULL REFERENCES source_documents(doc_id),
    case_name        TEXT NOT NULL,
    category         TEXT NOT NULL,
    metric_name      TEXT NOT NULL,
    metric_key       TEXT,
    value            REAL NOT NULL,
    unit             TEXT NOT NULL,
    as_of_date       TEXT,
    context          TEXT,
    confidence       TEXT DEFAULT 'HIGH',
    source_section   TEXT,
    source_page      INTEGER,
    source_cell      TEXT,
    extraction_note  TEXT
);

CREATE TABLE IF NOT EXISTS excel_cells (
    id                TEXT PRIMARY KEY,
    deal_id           TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id            TEXT NOT NULL REFERENCES source_documents(doc_id),
    sheet_name        TEXT NOT NULL,
    cell_address      TEXT NOT NULL,
    row_num           INTEGER NOT NULL,
    col_num           INTEGER NOT NULL,
    raw_value         TEXT,
    numeric_value     REAL,
    formula           TEXT,
    data_type         TEXT,
    number_format     TEXT,
    semantic_label    TEXT,
    semantic_category TEXT,
    unit              TEXT,
    row_header        TEXT,
    col_header        TEXT,
    is_assumption     INTEGER DEFAULT 0,
    is_output         INTEGER DEFAULT 0,
    case_name         TEXT,
    UNIQUE(deal_id, doc_id, sheet_name, cell_address)
);

CREATE TABLE IF NOT EXISTS excel_sheets (
    id               TEXT PRIMARY KEY,
    deal_id          TEXT NOT NULL REFERENCES deals(deal_id),
    doc_id           TEXT NOT NULL REFERENCES source_documents(doc_id),
    sheet_name       TEXT NOT NULL,
    sheet_index      INTEGER NOT NULL,
    sheet_type       TEXT,
    row_count        INTEGER,
    col_count        INTEGER,
    assumption_cells INTEGER DEFAULT 0,
    output_cells     INTEGER DEFAULT 0,
    formula_cells    INTEGER DEFAULT 0,
    ingest_notes     TEXT
);

CREATE TABLE IF NOT EXISTS data_conflicts (
    id               TEXT PRIMARY KEY,
    deal_id          TEXT NOT NULL REFERENCES deals(deal_id),
    conflict_type    TEXT NOT NULL,
    metric_name      TEXT NOT NULL,
    period_start     TEXT,
    period_end       TEXT,
    source_a_doc_id  TEXT REFERENCES source_documents(doc_id),
    source_a_case    TEXT,
    source_a_value   REAL,
    source_a_unit    TEXT,
    source_b_doc_id  TEXT REFERENCES source_documents(doc_id),
    source_b_case    TEXT,
    source_b_value   REAL,
    source_b_unit    TEXT,
    discrepancy_pct  REAL,
    severity         TEXT NOT NULL,
    resolved         INTEGER DEFAULT 0,
    resolution_note  TEXT,
    detected_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_runs (
    id                   TEXT PRIMARY KEY,
    deal_id              TEXT NOT NULL REFERENCES deals(deal_id),
    base_case            TEXT NOT NULL,
    scenario_name        TEXT,
    modified_assumptions TEXT NOT NULL,
    engine               TEXT NOT NULL,
    result_summary       TEXT NOT NULL,
    full_result          TEXT,
    run_timestamp        TEXT NOT NULL,
    cost_usd             REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    id                  TEXT PRIMARY KEY,
    deal_id             TEXT NOT NULL REFERENCES deals(deal_id),
    operation           TEXT NOT NULL,
    run_id              TEXT NOT NULL,
    timestamp           TEXT NOT NULL,
    files_processed     INTEGER DEFAULT 0,
    data_points_added   INTEGER DEFAULT 0,
    conflicts_detected  INTEGER DEFAULT 0,
    main_model          TEXT,
    audit_model         TEXT,
    cost_usd            REAL DEFAULT 0.0,
    status              TEXT DEFAULT 'complete',
    errors              TEXT
);
"""

# ── Indexes ───────────────────────────────────────────────────────────────────

_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_prod_deal_case   ON production_series(deal_id, case_name);
CREATE INDEX IF NOT EXISTS idx_prod_period       ON production_series(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_fin_deal_case     ON financial_series(deal_id, case_name);
CREATE INDEX IF NOT EXISTS idx_fin_line_item     ON financial_series(line_item);
CREATE INDEX IF NOT EXISTS idx_scalar_deal       ON scalar_datapoints(deal_id, metric_key);
CREATE INDEX IF NOT EXISTS idx_cells_sheet       ON excel_cells(deal_id, doc_id, sheet_name);
CREATE INDEX IF NOT EXISTS idx_cells_assumption  ON excel_cells(deal_id, is_assumption);
CREATE INDEX IF NOT EXISTS idx_conflicts_deal    ON data_conflicts(deal_id, severity);
CREATE INDEX IF NOT EXISTS idx_reserves_deal     ON reserve_estimates(deal_id, reserve_class);
CREATE INDEX IF NOT EXISTS idx_cost_deal         ON cost_benchmarks(deal_id, metric);
CREATE INDEX IF NOT EXISTS idx_fiscal_deal       ON fiscal_terms(deal_id, term_name);
"""


# ── Public API ─────────────────────────────────────────────────────────────────

def db_path_for_deal(deal_id: str, output_dir: str | Path = "./outputs") -> Path:
    """Return canonical path to the deal's SQLite DB file."""
    return Path(output_dir) / deal_id / "02_data_store.db"


def ensure_db(deal_id: str, output_dir: str | Path = "./outputs") -> Path:
    """
    Create (or open) the SQLite DB for the given deal.

    Returns the resolved path to the DB file.
    """
    path = db_path_for_deal(deal_id, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(_SCHEMA_DDL)
        conn.executescript(_INDEX_DDL)
        conn.commit()
    finally:
        conn.close()

    return path


def get_connection(deal_id: str, output_dir: str | Path = "./outputs") -> sqlite3.Connection:
    """Return an open SQLite connection with row_factory and FK support."""
    path = db_path_for_deal(deal_id, output_dir)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ── Upsert helpers ─────────────────────────────────────────────────────────────

def upsert_deal(
    conn: sqlite3.Connection,
    deal_id: str,
    deal_name: str,
    deal_type: str,
    jurisdiction: str,
    agent_version: str = "1.0",
) -> None:
    now = now_iso()
    conn.execute(
        """
        INSERT INTO deals (deal_id, deal_name, deal_type, jurisdiction, created_at, updated_at, agent_version)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(deal_id) DO UPDATE SET
            deal_name = excluded.deal_name,
            deal_type = excluded.deal_type,
            jurisdiction = excluded.jurisdiction,
            agent_version = excluded.agent_version,
            updated_at = excluded.updated_at
        """,
        (deal_id, deal_name, deal_type, jurisdiction, now, now, agent_version),
    )


def insert_source_document(conn: sqlite3.Connection, doc: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO source_documents
        (doc_id, deal_id, filename, folder_path, file_type, doc_category, doc_label,
         source_date, ingest_timestamp, ingest_run_id, case_name, sheet_count,
         table_count, cell_count, status, error_message)
        VALUES
        (:doc_id, :deal_id, :filename, :folder_path, :file_type, :doc_category, :doc_label,
         :source_date, :ingest_timestamp, :ingest_run_id, :case_name, :sheet_count,
         :table_count, :cell_count, :status, :error_message)
        """,
        _fill(doc, doc_id=new_id(), folder_path="", sheet_count=0,
              table_count=0, cell_count=0, status="complete", error_message=None,
              doc_category=None, doc_label=None, source_date=None, case_name=None),
    )


def upsert_case(
    conn: sqlite3.Connection,
    deal_id: str,
    case_name: str,
    case_type: str,
    display_label: str | None = None,
    description: str | None = None,
    source_doc_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO cases (case_id, deal_id, case_name, case_type, display_label, description, source_doc_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(deal_id, case_name) DO NOTHING
        """,
        (new_id(), deal_id, case_name, case_type,
         display_label or case_name.replace("_", " ").title(),
         description, source_doc_id, now_iso()),
    )


def bulk_insert_production(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT OR REPLACE INTO production_series
        (id, deal_id, doc_id, case_name, entity_name, period_type, period_start, period_end,
         product, value, unit, unit_normalised, value_normalised, confidence,
         source_sheet, source_cell, source_page, extraction_note)
        VALUES
        (:id, :deal_id, :doc_id, :case_name, :entity_name, :period_type, :period_start, :period_end,
         :product, :value, :unit, :unit_normalised, :value_normalised, :confidence,
         :source_sheet, :source_cell, :source_page, :extraction_note)
        """,
        [_fill(r, id=new_id(), entity_name=None, unit_normalised=None,
               value_normalised=None, confidence="HIGH",
               source_sheet=None, source_cell=None, source_page=None, extraction_note=None)
         for r in rows],
    )
    return len(rows)


def bulk_insert_reserves(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT OR IGNORE INTO reserve_estimates
        (id, deal_id, doc_id, case_name, entity_name, reserve_class, product, value, unit,
         unit_normalised, value_normalised, effective_date, report_date, reserve_engineer,
         confidence, source_section, source_page, extraction_note)
        VALUES
        (:id, :deal_id, :doc_id, :case_name, :entity_name, :reserve_class, :product, :value, :unit,
         :unit_normalised, :value_normalised, :effective_date, :report_date, :reserve_engineer,
         :confidence, :source_section, :source_page, :extraction_note)
        """,
        [_fill(r, id=new_id(), entity_name=None, unit_normalised=None,
               value_normalised=None, effective_date=None, report_date=None,
               reserve_engineer=None, confidence="HIGH",
               source_section=None, source_page=None, extraction_note=None)
         for r in rows],
    )
    return len(rows)


def bulk_insert_financials(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT OR IGNORE INTO financial_series
        (id, deal_id, doc_id, case_name, line_item, line_item_label, period_type,
         period_start, period_end, value, unit, unit_normalised, value_normalised,
         confidence, source_sheet, source_cell, source_page, extraction_note)
        VALUES
        (:id, :deal_id, :doc_id, :case_name, :line_item, :line_item_label, :period_type,
         :period_start, :period_end, :value, :unit, :unit_normalised, :value_normalised,
         :confidence, :source_sheet, :source_cell, :source_page, :extraction_note)
        """,
        [_fill(r, id=new_id(), line_item_label=None, unit_normalised="USD",
               value_normalised=None, confidence="HIGH",
               source_sheet=None, source_cell=None, source_page=None, extraction_note=None)
         for r in rows],
    )
    return len(rows)


def bulk_insert_costs(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT OR IGNORE INTO cost_benchmarks
        (id, deal_id, doc_id, case_name, metric, period_start, period_end, value, unit,
         confidence, source_sheet, source_cell, source_page, extraction_note)
        VALUES
        (:id, :deal_id, :doc_id, :case_name, :metric, :period_start, :period_end, :value, :unit,
         :confidence, :source_sheet, :source_cell, :source_page, :extraction_note)
        """,
        [_fill(r, id=new_id(), period_start=None, period_end=None, confidence="HIGH",
               source_sheet=None, source_cell=None, source_page=None, extraction_note=None)
         for r in rows],
    )
    return len(rows)


def bulk_insert_fiscal(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT OR IGNORE INTO fiscal_terms
        (id, deal_id, doc_id, case_name, term_name, term_label, value, unit,
         effective_from, effective_to, conditions, confidence, source_section, source_page, extraction_note)
        VALUES
        (:id, :deal_id, :doc_id, :case_name, :term_name, :term_label, :value, :unit,
         :effective_from, :effective_to, :conditions, :confidence, :source_section, :source_page, :extraction_note)
        """,
        [_fill(r, id=new_id(), term_label=None, effective_from=None, effective_to=None,
               conditions=None, confidence="HIGH",
               source_section=None, source_page=None, extraction_note=None)
         for r in rows],
    )
    return len(rows)


def bulk_insert_scalars(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT OR IGNORE INTO scalar_datapoints
        (id, deal_id, doc_id, case_name, category, metric_name, metric_key, value, unit,
         as_of_date, context, confidence, source_section, source_page, source_cell, extraction_note)
        VALUES
        (:id, :deal_id, :doc_id, :case_name, :category, :metric_name, :metric_key, :value, :unit,
         :as_of_date, :context, :confidence, :source_section, :source_page, :source_cell, :extraction_note)
        """,
        [_fill(r, id=new_id(), metric_key=None, as_of_date=None, context=None,
               confidence="HIGH", source_section=None, source_page=None,
               source_cell=None, extraction_note=None)
         for r in rows],
    )
    return len(rows)


def bulk_insert_excel_cells(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT OR IGNORE INTO excel_cells
        (id, deal_id, doc_id, sheet_name, cell_address, row_num, col_num,
         raw_value, numeric_value, formula, data_type, number_format,
         semantic_label, semantic_category, unit, row_header, col_header,
         is_assumption, is_output, case_name)
        VALUES
        (:id, :deal_id, :doc_id, :sheet_name, :cell_address, :row_num, :col_num,
         :raw_value, :numeric_value, :formula, :data_type, :number_format,
         :semantic_label, :semantic_category, :unit, :row_header, :col_header,
         :is_assumption, :is_output, :case_name)
        """,
        [_fill(r, id=new_id(), raw_value=None, numeric_value=None, formula=None,
               data_type=None, number_format=None, semantic_label=None,
               semantic_category=None, unit=None, row_header=None, col_header=None,
               is_assumption=0, is_output=0, case_name=None)
         for r in rows],
    )
    return len(rows)


def insert_excel_sheet(conn: sqlite3.Connection, sheet: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO excel_sheets
        (id, deal_id, doc_id, sheet_name, sheet_index, sheet_type, row_count, col_count,
         assumption_cells, output_cells, formula_cells, ingest_notes)
        VALUES
        (:id, :deal_id, :doc_id, :sheet_name, :sheet_index, :sheet_type, :row_count, :col_count,
         :assumption_cells, :output_cells, :formula_cells, :ingest_notes)
        """,
        _fill(sheet, id=new_id(), sheet_type=None, row_count=None, col_count=None,
              assumption_cells=0, output_cells=0, formula_cells=0, ingest_notes=None),
    )


def insert_conflict(conn: sqlite3.Connection, conflict: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO data_conflicts
        (id, deal_id, conflict_type, metric_name, period_start, period_end,
         source_a_doc_id, source_a_case, source_a_value, source_a_unit,
         source_b_doc_id, source_b_case, source_b_value, source_b_unit,
         discrepancy_pct, severity, resolved, resolution_note, detected_at)
        VALUES
        (:id, :deal_id, :conflict_type, :metric_name, :period_start, :period_end,
         :source_a_doc_id, :source_a_case, :source_a_value, :source_a_unit,
         :source_b_doc_id, :source_b_case, :source_b_value, :source_b_unit,
         :discrepancy_pct, :severity, :resolved, :resolution_note, :detected_at)
        """,
        _fill(conflict, id=new_id(), period_start=None, period_end=None,
              source_a_doc_id=None, source_a_case=None, source_a_value=None, source_a_unit=None,
              source_b_doc_id=None, source_b_case=None, source_b_value=None, source_b_unit=None,
              discrepancy_pct=None, resolved=0, resolution_note=None, detected_at=now_iso()),
    )


def insert_scenario_run(conn: sqlite3.Connection, run: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO scenario_runs
        (id, deal_id, base_case, scenario_name, modified_assumptions, engine,
         result_summary, full_result, run_timestamp, cost_usd)
        VALUES
        (:id, :deal_id, :base_case, :scenario_name, :modified_assumptions, :engine,
         :result_summary, :full_result, :run_timestamp, :cost_usd)
        """,
        _fill(run, id=new_id(), scenario_name=None, full_result=None,
              run_timestamp=now_iso(), cost_usd=0.0),
    )


def log_ingestion(conn: sqlite3.Connection, log: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO ingestion_log
        (id, deal_id, operation, run_id, timestamp, files_processed, data_points_added,
         conflicts_detected, main_model, audit_model, cost_usd, status, errors)
        VALUES
        (:id, :deal_id, :operation, :run_id, :timestamp, :files_processed, :data_points_added,
         :conflicts_detected, :main_model, :audit_model, :cost_usd, :status, :errors)
        """,
        _fill(log, id=new_id(), timestamp=now_iso(), files_processed=0,
              data_points_added=0, conflicts_detected=0, main_model=None,
              audit_model=None, cost_usd=0.0, status="complete", errors=None),
    )


# ── Query helpers ──────────────────────────────────────────────────────────────

def query_all(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute a SELECT and return list of dicts."""
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_cases(conn: sqlite3.Connection, deal_id: str) -> list[str]:
    rows = query_all(conn, "SELECT case_name FROM cases WHERE deal_id = ?", (deal_id,))
    return [r["case_name"] for r in rows]


def get_conflicts(conn: sqlite3.Connection, deal_id: str,
                  severity: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM data_conflicts WHERE deal_id = ?"
    params: tuple = (deal_id,)
    if severity:
        sql += " AND severity = ?"
        params = (deal_id, severity)
    return query_all(conn, sql, params)


def get_source_docs(conn: sqlite3.Connection, deal_id: str) -> list[dict[str, Any]]:
    return query_all(conn, "SELECT * FROM source_documents WHERE deal_id = ?", (deal_id,))


def count_data_points(conn: sqlite3.Connection, deal_id: str) -> int:
    tables = ["production_series", "reserve_estimates", "financial_series",
              "cost_benchmarks", "fiscal_terms", "scalar_datapoints"]
    total = 0
    for t in tables:
        row = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE deal_id = ?", (deal_id,)).fetchone()
        total += row[0] if row else 0
    return total


# ── Internal helpers ───────────────────────────────────────────────────────────

def _fill(d: dict[str, Any], **defaults) -> dict[str, Any]:
    """Return dict with defaults applied for missing keys."""
    result = dict(defaults)
    result.update(d)
    return result
