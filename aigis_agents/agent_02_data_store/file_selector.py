"""
VDR file selection for Agent 02 — VDR Financial & Operational Data Store.

Selects financially/operationally significant files from a VDR for ingestion.
Two modes:
  1. With Agent 01: Calls Agent 01 in tool_call mode to classify all files,
     then filters by INGEST_CATEGORIES.
  2. Without Agent 01: Heuristic filename/extension scan of the VDR root.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ── Category whitelist ─────────────────────────────────────────────────────────

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

# Extensions we can ingest
INGESTIBLE_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".pdf", ".csv", ".tsv"}

# Extension priority for ordering (lower = higher priority)
EXTENSION_PRIORITY = {".xlsx": 0, ".xlsm": 1, ".csv": 2, ".tsv": 3, ".pdf": 4, ".xls": 5}

# Filename keyword patterns for heuristic selection (case-insensitive)
_FINANCIAL_PATTERNS = [
    re.compile(r"financ", re.I),
    re.compile(r"model", re.I),
    re.compile(r"budget", re.I),
    re.compile(r"account", re.I),
    re.compile(r"p[&_]?l|profit.*loss|income.*state", re.I),
    re.compile(r"ebitda", re.I),
    re.compile(r"los|lease.*operat", re.I),
]

_OPERATIONAL_PATTERNS = [
    re.compile(r"production|prod[\s_\-]hist", re.I),
    re.compile(r"\bcpr\b|competen.*person|reserves.*report", re.I),
    re.compile(r"decline.*curv", re.I),
    re.compile(r"well.*perf|perf.*well", re.I),
    re.compile(r"capex|capital.*expenditure", re.I),
    re.compile(r"operat.*report|monthly.*report|quarterly.*report", re.I),
    re.compile(r"forecast|projection", re.I),
]

# Patterns to explicitly exclude (avoid ingesting scanned images, etc.)
_EXCLUDE_PATTERNS = [
    re.compile(r"\.docx?$", re.I),
    re.compile(r"\.pptx?$", re.I),
    re.compile(r"\.msg$|\.eml$", re.I),
    re.compile(r"nda|non.?disclosure|confidential.?agreement", re.I),
    re.compile(r"template|blank|example|sample", re.I),
]


# ── Public API ─────────────────────────────────────────────────────────────────

def select_files_for_ingestion(
    vdr_path: str | Path,
    agent01: Any | None = None,
    deal_id: str | None = None,
    deal_type: str = "producing_asset",
    jurisdiction: str = "GoM",
    file_filter: list[str] | None = None,
    max_files: int = 200,
) -> list[dict[str, Any]]:
    """
    Select files from a VDR folder for ingestion.

    Args:
        vdr_path:    Root directory of the VDR.
        agent01:     Agent01 instance (optional). If provided, calls it to classify
                     files first and uses INGEST_CATEGORIES whitelist.
        deal_id:     Deal UUID (required for Agent 01 call).
        deal_type:   E.g., "producing_asset", "exploration".
        jurisdiction: E.g., "GoM", "UKCS".
        file_filter: Limit to these categories (None = all INGEST_CATEGORIES).
        max_files:   Safety cap on total files returned.

    Returns:
        List of dicts: {path, filename, file_type, category, doc_label, priority}
        Sorted by (priority asc, file_size desc).
    """
    root = Path(vdr_path)
    if not root.exists():
        return []

    categories = set(file_filter) if file_filter else INGEST_CATEGORIES

    if agent01 is not None and deal_id:
        files = _select_via_agent01(root, agent01, deal_id, deal_type, jurisdiction, categories)
    else:
        files = _select_heuristic(root, categories)

    # Remove excluded files
    files = [f for f in files if not _is_excluded(f["path"])]

    # Sort: priority asc (xlsx first), then file size desc (larger = richer)
    files.sort(key=lambda f: (EXTENSION_PRIORITY.get(Path(f["path"]).suffix.lower(), 99),
                               -Path(f["path"]).stat().st_size))

    return files[:max_files]


# ── Agent 01 integration ───────────────────────────────────────────────────────

def _select_via_agent01(
    root: Path,
    agent01: Any,
    deal_id: str,
    deal_type: str,
    jurisdiction: str,
    categories: set[str],
) -> list[dict[str, Any]]:
    """Call Agent 01 in tool_call mode to enumerate and classify VDR files."""
    try:
        result = agent01.invoke(
            mode="tool_call",
            deal_id=deal_id,
            vdr_path=str(root),
            deal_type=deal_type,
            jurisdiction=jurisdiction,
        )
        # Agent 01 returns file_manifest list
        classified = result.get("file_manifest", []) or result.get("files", [])
        selected = []
        for item in classified:
            cat = item.get("category", "")
            ext = Path(item.get("path", "")).suffix.lower()
            # Filter by category whitelist and ingestible extension
            if cat in categories and ext in INGESTIBLE_EXTENSIONS:
                selected.append({
                    "path":      item.get("path"),
                    "filename":  Path(item["path"]).name,
                    "file_type": _ext_to_type(ext),
                    "category":  cat,
                    "doc_label": item.get("doc_label") or item.get("label"),
                    "priority":  EXTENSION_PRIORITY.get(ext, 99),
                })
        return selected
    except Exception:
        # Graceful fallback to heuristic if Agent 01 unavailable
        return _select_heuristic(root, categories)


# ── Heuristic selection ────────────────────────────────────────────────────────

def _select_heuristic(root: Path, categories: set[str]) -> list[dict[str, Any]]:
    """
    Walk VDR directory and select files using filename pattern matching.
    Used when Agent 01 is not available.
    """
    selected = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in INGESTIBLE_EXTENSIONS:
            continue
        if _is_excluded(path):
            continue

        category, doc_label = _classify_by_name(path)
        if category is None:
            continue

        selected.append({
            "path":      str(path),
            "filename":  path.name,
            "file_type": _ext_to_type(ext),
            "category":  category,
            "doc_label": doc_label,
            "priority":  EXTENSION_PRIORITY.get(ext, 99),
        })

    return selected


def _classify_by_name(path: Path) -> tuple[str | None, str | None]:
    """Return (category, doc_label) for a file based on name/path heuristics."""
    name = path.name
    # Build a search string from filename + parent folders
    search_str = " ".join(p.name for p in path.parts[-4:])

    for pattern in _FINANCIAL_PATTERNS:
        if pattern.search(search_str):
            if re.search(r"model|financial.?model|fin.?mod", search_str, re.I):
                return "Financial/Financial Model", "Financial Model"
            if re.search(r"los|lease.*operat", search_str, re.I):
                return "Technical/LOS", "Lease Operating Statement"
            if re.search(r"audit|annual.?account|historica", search_str, re.I):
                return "Financial/Audited Accounts", "Audited Accounts"
            if re.search(r"budget|capex", search_str, re.I):
                return "Financial/Financial Model", "CAPEX Budget"
            return "Financial/Management Accounts", "Management Accounts"

    for pattern in _OPERATIONAL_PATTERNS:
        if pattern.search(search_str):
            if re.search(r"\bcpr\b|competen.*person", search_str, re.I):
                return "Reserves/CPR", "CPR"
            if re.search(r"reserve", search_str, re.I):
                return "Reserves/Competent Person Report", "Reserve Report"
            if re.search(r"well.*perf|perf.*well", search_str, re.I):
                return "Technical/Well Performance", "Well Performance"
            if re.search(r"monthly|quarterly", search_str, re.I):
                return "Operations/Monthly Reports", "Operating Report"
            if re.search(r"forecast|projection", search_str, re.I):
                return "Production/Forecast", "Production Forecast"
            return "Production/History", "Production Data"

    return None, None


def _is_excluded(path: str | Path) -> bool:
    """Return True if the file should be excluded from ingestion."""
    path_str = str(path)
    for pattern in _EXCLUDE_PATTERNS:
        if pattern.search(path_str):
            return True
    return False


def _ext_to_type(ext: str) -> str:
    if ext in (".xlsx", ".xlsm", ".xls"):
        return "excel"
    if ext == ".pdf":
        return "pdf"
    if ext in (".csv", ".tsv"):
        return "csv"
    return "other"
