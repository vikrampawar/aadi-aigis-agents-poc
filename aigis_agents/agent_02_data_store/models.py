"""
Pydantic models for Agent 02 — VDR Financial & Operational Data Store.

All models mirror the SQLite schema defined in db_manager.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────────

class FileType(str, Enum):
    excel = "excel"
    pdf   = "pdf"
    csv   = "csv"
    other = "other"


class PeriodType(str, Enum):
    monthly   = "monthly"
    quarterly = "quarterly"
    annual    = "annual"


class Product(str, Enum):
    oil   = "oil"
    gas   = "gas"
    ngl   = "ngl"
    water = "water"
    boe   = "boe"
    boepd = "boepd"


class ReserveClass(str, Enum):
    p1   = "1P"
    p2   = "2P"
    p3   = "3P"
    pdp  = "PDP"
    pnp  = "PNP"
    pdnp = "PDnP"


class Confidence(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"


class SheetType(str, Enum):
    production   = "production"
    financials   = "financials"
    assumptions  = "assumptions"
    summary      = "summary"
    dcf          = "dcf"
    sensitivity  = "sensitivity"
    reserves     = "reserves"
    costs        = "costs"
    other        = "other"


class CaseType(str, Enum):
    management   = "management"
    independent  = "independent"
    conservative = "conservative"
    low          = "low"
    mid          = "mid"
    high         = "high"
    custom       = "custom"


class ConflictType(str, Enum):
    value_mismatch      = "value_mismatch"
    unit_inconsistency  = "unit_inconsistency"
    date_overlap        = "date_overlap"
    missing_in_source   = "missing_in_source"


class ConflictSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING  = "WARNING"
    INFO     = "INFO"


class FormulaEngine(str, Enum):
    xlcalculator = "xlcalculator"
    agent_04     = "agent_04"
    hybrid       = "hybrid"


# ── DB row models ──────────────────────────────────────────────────────────────

class Deal(BaseModel):
    deal_id:       str
    deal_name:     str
    deal_type:     str
    jurisdiction:  str
    created_at:    str
    updated_at:    str
    agent_version: str = "1.0"


class SourceDocument(BaseModel):
    doc_id:           str
    deal_id:          str
    filename:         str
    folder_path:      str
    file_type:        FileType
    doc_category:     str | None = None
    doc_label:        str | None = None
    source_date:      str | None = None
    ingest_timestamp: str
    ingest_run_id:    str
    case_name:        str | None = None
    sheet_count:      int = 0
    table_count:      int = 0
    cell_count:       int = 0
    status:           str = "complete"
    error_message:    str | None = None


class Case(BaseModel):
    case_id:       str
    deal_id:       str
    case_name:     str
    case_type:     CaseType
    display_label: str
    description:   str | None = None
    source_doc_id: str | None = None
    created_at:    str


class ProductionDataPoint(BaseModel):
    id:               str
    deal_id:          str
    doc_id:           str
    case_name:        str
    entity_name:      str | None = None
    period_type:      PeriodType
    period_start:     str
    period_end:       str
    product:          str
    value:            float
    unit:             str
    unit_normalised:  str | None = None
    value_normalised: float | None = None
    confidence:       Confidence = Confidence.HIGH
    source_sheet:     str | None = None
    source_cell:      str | None = None
    source_page:      int | None = None
    extraction_note:  str | None = None


class ReserveEstimate(BaseModel):
    id:               str
    deal_id:          str
    doc_id:           str
    case_name:        str
    entity_name:      str | None = None
    reserve_class:    str
    product:          str
    value:            float
    unit:             str
    unit_normalised:  str | None = None
    value_normalised: float | None = None
    effective_date:   str | None = None
    report_date:      str | None = None
    reserve_engineer: str | None = None
    confidence:       Confidence = Confidence.HIGH
    source_section:   str | None = None
    source_page:      int | None = None
    extraction_note:  str | None = None


class FinancialDataPoint(BaseModel):
    id:               str
    deal_id:          str
    doc_id:           str
    case_name:        str
    line_item:        str
    line_item_label:  str | None = None
    period_type:      PeriodType
    period_start:     str
    period_end:       str
    value:            float
    unit:             str
    unit_normalised:  str = "USD"
    value_normalised: float | None = None
    confidence:       Confidence = Confidence.HIGH
    source_sheet:     str | None = None
    source_cell:      str | None = None
    source_page:      int | None = None
    extraction_note:  str | None = None


class CostBenchmark(BaseModel):
    id:              str
    deal_id:         str
    doc_id:          str
    case_name:       str
    metric:          str
    period_start:    str | None = None
    period_end:      str | None = None
    value:           float
    unit:            str
    confidence:      Confidence = Confidence.HIGH
    source_sheet:    str | None = None
    source_cell:     str | None = None
    source_page:     int | None = None
    extraction_note: str | None = None


class FiscalTerm(BaseModel):
    id:              str
    deal_id:         str
    doc_id:          str
    case_name:       str
    term_name:       str
    term_label:      str | None = None
    value:           float
    unit:            str
    effective_from:  str | None = None
    effective_to:    str | None = None
    conditions:      str | None = None
    confidence:      Confidence = Confidence.HIGH
    source_section:  str | None = None
    source_page:     int | None = None
    extraction_note: str | None = None


class ScalarDataPoint(BaseModel):
    id:              str
    deal_id:         str
    doc_id:          str
    case_name:       str
    category:        str
    metric_name:     str
    metric_key:      str | None = None
    value:           float
    unit:            str
    as_of_date:      str | None = None
    context:         str | None = None
    confidence:      Confidence = Confidence.HIGH
    source_section:  str | None = None
    source_page:     int | None = None
    source_cell:     str | None = None
    extraction_note: str | None = None


class ExcelCell(BaseModel):
    id:                str
    deal_id:           str
    doc_id:            str
    sheet_name:        str
    cell_address:      str
    row_num:           int
    col_num:           int
    raw_value:         str | None = None
    numeric_value:     float | None = None
    formula:           str | None = None
    data_type:         str | None = None
    number_format:     str | None = None
    semantic_label:    str | None = None
    semantic_category: str | None = None
    unit:              str | None = None
    row_header:        str | None = None
    col_header:        str | None = None
    is_assumption:     bool = False
    is_output:         bool = False
    case_name:         str | None = None


class ExcelSheet(BaseModel):
    id:               str
    deal_id:          str
    doc_id:           str
    sheet_name:       str
    sheet_index:      int
    sheet_type:       SheetType | None = None
    row_count:        int | None = None
    col_count:        int | None = None
    assumption_cells: int = 0
    output_cells:     int = 0
    formula_cells:    int = 0
    ingest_notes:     str | None = None


class DataConflict(BaseModel):
    id:               str
    deal_id:          str
    conflict_type:    ConflictType
    metric_name:      str
    period_start:     str | None = None
    period_end:       str | None = None
    source_a_doc_id:  str | None = None
    source_a_case:    str | None = None
    source_a_value:   float | None = None
    source_a_unit:    str | None = None
    source_b_doc_id:  str | None = None
    source_b_case:    str | None = None
    source_b_value:   float | None = None
    source_b_unit:    str | None = None
    discrepancy_pct:  float | None = None
    severity:         ConflictSeverity
    resolved:         bool = False
    resolution_note:  str | None = None
    detected_at:      str


class ScenarioRun(BaseModel):
    id:                   str
    deal_id:              str
    base_case:            str
    scenario_name:        str | None = None
    modified_assumptions: str          # JSON string
    engine:               FormulaEngine
    result_summary:       str          # JSON string
    full_result:          str | None = None  # JSON string
    run_timestamp:        str
    cost_usd:             float = 0.0


class IngestionLog(BaseModel):
    id:                 str
    deal_id:            str
    operation:          str
    run_id:             str
    timestamp:          str
    files_processed:    int = 0
    data_points_added:  int = 0
    conflicts_detected: int = 0
    main_model:         str | None = None
    audit_model:        str | None = None
    cost_usd:           float = 0.0
    status:             str = "complete"
    errors:             str | None = None  # JSON array string


# ── Output models (returned by _run()) ────────────────────────────────────────

class ConflictSummary(BaseModel):
    critical: int = 0
    warning:  int = 0
    info:     int = 0
    items:    list[dict[str, Any]] = Field(default_factory=list)


class IngestionResult(BaseModel):
    """Raw output from ingest_vdr or ingest_file operations."""
    operation:         str
    files_processed:   int = 0
    data_points_added: int = 0
    conflicts:         ConflictSummary = Field(default_factory=ConflictSummary)
    cases_ingested:    list[str] = Field(default_factory=list)
    db_path:           str = ""
    output_paths:      dict[str, str] = Field(default_factory=dict)
    cost_usd:          float = 0.0
    errors:            list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Raw output from query operation."""
    operation:      str = "query"
    query:          str = ""
    sql_executed:   str = ""
    data:           list[dict[str, Any]] = Field(default_factory=list)
    row_count:      int = 0
    cases_present:  list[str] = Field(default_factory=list)
    conflicts:      list[dict[str, Any]] = Field(default_factory=list)
    scenario_result: dict[str, Any] | None = None
    metadata:       dict[str, Any] = Field(default_factory=dict)
    cost_usd:       float = 0.0


# ── LLM extraction helpers ─────────────────────────────────────────────────────

class ExtractedDataPoint(BaseModel):
    """LLM-extracted data point from a PDF table or CSV column."""
    metric_name: str
    value:       float
    unit:        str
    period:      str | None = None       # ISO date range "YYYY-MM-DD/YYYY-MM-DD"
    category:    str = "other"
    case_name:   str = "base_case"
    confidence:  Confidence = Confidence.MEDIUM
    context:     str | None = None
    source_page: int | None = None
    source_cell: str | None = None


class SheetClassification(BaseModel):
    """LLM output for classifying an Excel sheet."""
    sheet_type:       SheetType
    primary_metric:   str | None = None
    unit_system:      str | None = None
    period_type:      PeriodType | None = None
    case_name:        str | None = None
    is_time_series:   bool = False
    notes:            str = ""
