"""Pydantic data models for Agent 01 — VDR Document Inventory & Gap Analyst."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


# ── Enumerations ─────────────────────────────────────────────────────────────

class DealType(str, Enum):
    producing_asset = "producing_asset"
    exploration = "exploration"
    development = "development"
    corporate = "corporate"


class Jurisdiction(str, Enum):
    GoM = "GoM"
    UKCS = "UKCS"
    Norway = "Norway"
    International = "International"


class DocumentSource(str, Enum):
    filesystem = "filesystem"
    db = "db"
    csv = "csv"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNCLASSIFIED = "UNCLASSIFIED"


class ChecklistStatus(str, Enum):
    present = "present"       # ✅ HIGH-confidence match found
    partial = "partial"       # ⚠️ MEDIUM-confidence or outdated
    missing = "missing"       # ❌ No match found
    not_applicable = "not_applicable"  # Jurisdiction/deal_type excludes this item


class DocumentTier(str, Enum):
    need_to_have = "need_to_have"
    good_to_have = "good_to_have"


# ── VDR File ─────────────────────────────────────────────────────────────────

class VDRFile(BaseModel):
    id: str = Field(default="")               # uuid assigned during processing
    folder_path: str = ""
    filename: str
    file_extension: str = ""
    size_kb: float = 0.0
    date_modified: str | None = None          # ISO date string
    source: DocumentSource = DocumentSource.filesystem
    # Populated after classification
    classification: str | None = None         # aigis doc_type
    classification_confidence: Confidence = Confidence.UNCLASSIFIED
    classification_reasoning: str | None = None
    checklist_item_matched: str | None = None  # checklist item id
    checklist_category: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.folder_path}/{self.filename}".lstrip("/")


# ── Checklist ─────────────────────────────────────────────────────────────────

class ChecklistItem(BaseModel):
    id: str                                    # e.g. "corp_001"
    description: str
    tier: dict[str, DocumentTier]              # deal_type → NTH/GTH
    jurisdictions: list[str] = ["all"]         # ["all"] or ["GoM", "UKCS"]
    jurisdiction_notes: dict[str, str] = {}
    search_keywords: list[str] = []
    doc_types: list[str] = []                  # aigis doc_type hints
    age_threshold_years: int | None = None     # None = no threshold
    multi_document: bool = False               # e.g. "3 years of accounts"
    notes: str = ""
    drl_request_text: str = ""                 # pre-written DRL language


class ChecklistCategory(BaseModel):
    label: str
    items: list[ChecklistItem]


class Checklist(BaseModel):
    version: str
    last_updated: str
    categories: dict[str, ChecklistCategory]  # category_key → category

    def get_item(self, item_id: str) -> ChecklistItem | None:
        for cat in self.categories.values():
            for item in cat.items:
                if item.id == item_id:
                    return item
        return None

    def all_items(self) -> list[tuple[str, ChecklistItem]]:
        """Returns (category_key, item) tuples for all items."""
        result = []
        for cat_key, cat in self.categories.items():
            for item in cat.items:
                result.append((cat_key, item))
        return result


# ── Classification Result ─────────────────────────────────────────────────────

class ClassificationResult(BaseModel):
    file: VDRFile
    matched_item_id: str | None = None
    matched_category: str | None = None
    confidence: Confidence = Confidence.UNCLASSIFIED
    match_stage: Literal["keyword", "fuzzy", "llm", "db", "none"] = "none"
    fuzzy_score: float | None = None
    llm_reasoning: str | None = None
    is_outdated: bool = False                  # True if beyond age threshold


# ── Gap Report ────────────────────────────────────────────────────────────────

class ChecklistItemResult(BaseModel):
    item_id: str
    category_key: str
    category_label: str
    description: str
    tier: DocumentTier
    status: ChecklistStatus
    matched_files: list[VDRFile] = []
    notes: str = ""
    drl_request_text: str = ""


class GapReportSummary(BaseModel):
    total_files: int = 0
    # Need to Have counts
    present_nth: int = 0
    partial_nth: int = 0
    missing_nth: int = 0
    # Good to Have counts
    present_gth: int = 0
    partial_gth: int = 0
    missing_gth: int = 0
    # Classification stats
    high_confidence: int = 0
    medium_confidence: int = 0
    low_confidence: int = 0
    unclassified: int = 0
    novel_count: int = 0


class GapReport(BaseModel):
    deal_id: str
    deal_name: str
    deal_type: DealType
    jurisdiction: Jurisdiction
    checklist_version: str
    run_timestamp: str
    summary: GapReportSummary
    items: list[ChecklistItemResult] = []
    low_confidence_files: list[VDRFile] = []   # files needing human review

    def by_status(self, tier: DocumentTier, status: ChecklistStatus) -> list[ChecklistItemResult]:
        return [i for i in self.items if i.tier == tier and i.status == status]


# ── Self-Learning Proposals ────────────────────────────────────────────────────

class ChecklistProposal(BaseModel):
    proposal_id: str
    deal_id: str
    run_timestamp: str
    filenames: list[str]
    folder_path: str
    suggested_category: str
    suggested_item_description: str
    suggested_tier: DocumentTier
    applicable_deal_types: list[DealType]
    reasoning: str
    status: Literal["pending", "accepted", "rejected"] = "pending"
    reviewed_at: str | None = None


# ── Agent Result ─────────────────────────────────────────────────────────────

class AgentOutputPaths(BaseModel):
    inventory_json: str
    gap_report_md: str
    drl_docx: str


class AgentResult(BaseModel):
    status: Literal["success", "partial", "error"]
    outputs: AgentOutputPaths | None = None
    findings: GapReportSummary | None = None
    proposals: list[ChecklistProposal] = []
    gap_delta: "GapDelta | None" = None
    error: str | None = None
    run_timestamp: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    primer_updates_count: int = 0


# ── Deal Registry & Gap Delta ─────────────────────────────────────────────────

class RunRecord(BaseModel):
    """Snapshot of one agent run — stored in registry for future delta comparisons."""
    run_id: str
    timestamp: str
    checklist_version: str
    total_files: int
    classified: int
    nth_present: int
    nth_partial: int
    nth_missing: int
    gth_present: int
    gth_partial: int
    gth_missing: int
    novel_proposals: int = 0
    cost_usd: float = 0.0
    output_dir: str = ""
    item_statuses: dict[str, str] = {}   # item_id → "present"|"partial"|"missing"|"not_applicable"


class GapDeltaItem(BaseModel):
    """A checklist item that changed status (or is still outstanding) between runs."""
    item_id: str
    category_label: str
    description: str
    tier: DocumentTier
    prev_status: ChecklistStatus
    curr_status: ChecklistStatus
    days_outstanding: int | None = None


class GapDelta(BaseModel):
    """Changes between two consecutive runs on the same deal."""
    deal_id: str
    deal_name: str
    prev_run_id: str
    curr_run_id: str
    prev_timestamp: str
    curr_timestamp: str
    days_between_runs: int
    gaps_filled: list[GapDeltaItem] = []        # missing/partial → present
    gaps_opened: list[GapDeltaItem] = []         # present → missing/partial (regression)
    still_missing_nth: list[GapDeltaItem] = []   # still ❌ NTH
    still_partial_nth: list[GapDeltaItem] = []   # still ⚠️ NTH


class DealRecord(BaseModel):
    """Registry entry for one deal — accumulates all runs over time."""
    deal_id: str
    deal_name: str
    deal_type: str
    jurisdiction: str
    buyer: str | None = None
    first_run_timestamp: str
    last_run_timestamp: str
    run_count: int = 1
    runs: list[RunRecord] = []


class AgentRegistryStats(BaseModel):
    """Agent-level aggregate stats across all deals ever processed."""
    total_deals: int = 0
    total_files_reviewed: int = 0
    total_runs: int = 0
    checklist_improvements_contributed: int = 0
    first_run_timestamp: str | None = None
    last_run_timestamp: str | None = None


class AgentRegistry(BaseModel):
    """Top-level registry: agent stats + all deal records."""
    schema_version: str = "1.0"
    generated_at: str = ""
    agent_stats: AgentRegistryStats = AgentRegistryStats()
    deals: list[DealRecord] = []

    def get_deal(self, deal_id: str) -> "DealRecord | None":
        for d in self.deals:
            if d.deal_id == deal_id:
                return d
        return None
