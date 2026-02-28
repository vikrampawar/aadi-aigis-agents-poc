"""VDR file crawlers — filesystem, VDR export CSV/XLSX, and aigis-poc DB."""

from __future__ import annotations

import uuid
from pathlib import Path

import pandas as pd

from aigis_agents.agent_01_vdr_inventory.models import DocumentSource, VDRFile

# ---------------------------------------------------------------------------
# Filesystem Crawler
# ---------------------------------------------------------------------------

# Extensions worth indexing (skip binaries, system files, etc.)
INDEXED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".xlsm", ".csv", ".docx", ".doc",
    ".pptx", ".ppt", ".txt", ".las", ".zip", ".rar", ".7z",
    ".tif", ".tiff", ".png", ".jpg", ".jpeg",  # scanned doc images
    ".xml", ".json",
}

_SKIP_DIRS = {"__MACOSX", ".DS_Store", "Thumbs.db", "$RECYCLE.BIN", ".git"}


def crawl_filesystem(vdr_path: str | Path) -> list[VDRFile]:
    """
    Recursively crawl a local directory and return a list of VDRFile objects.
    Skips system/hidden files and unindexed extensions.
    """
    root = Path(vdr_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"VDR path not found: {root}")
    if not root.is_dir():
        raise ValueError(f"VDR path is not a directory: {root}")

    files: list[VDRFile] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # Skip system dirs
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        # Skip hidden files
        if p.name.startswith("."):
            continue
        # Skip non-indexed extensions (but include files with no extension too)
        if p.suffix.lower() not in INDEXED_EXTENSIONS and p.suffix != "":
            continue

        try:
            stat = p.stat()
            size_kb = round(stat.st_size / 1024, 1)
            mtime = pd.Timestamp(stat.st_mtime, unit="s").strftime("%Y-%m-%d")
        except OSError:
            size_kb = 0.0
            mtime = None

        rel = p.relative_to(root)
        folder = str(rel.parent) if rel.parent != Path(".") else ""

        files.append(
            VDRFile(
                id=str(uuid.uuid4()),
                folder_path=folder,
                filename=p.name,
                file_extension=p.suffix.lower(),
                size_kb=size_kb,
                date_modified=mtime,
                source=DocumentSource.filesystem,
            )
        )
    return files


# ---------------------------------------------------------------------------
# VDR Platform Export CSV/XLSX Crawler
# ---------------------------------------------------------------------------

# Column name normalisation map — covers Datasite, Intralinks, Ansarada, Firmex, generic
_COLUMN_ALIASES: dict[str, list[str]] = {
    "filename":      ["filename", "file name", "document name", "name", "title", "file"],
    "folder_path":   ["folder", "folder path", "path", "directory", "location", "section", "room folder"],
    "size_kb":       ["size (kb)", "size kb", "size", "file size", "size (bytes)", "filesize"],
    "date_modified": ["date modified", "modified", "last modified", "modified date", "updated", "upload date", "date uploaded"],
    "file_extension": ["type", "file type", "extension", "format"],
}


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remap VDR platform column names to our internal schema."""
    lower_map = {col.lower().strip(): col for col in df.columns}
    rename = {}
    for target, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map:
                rename[lower_map[alias]] = target
                break
    return df.rename(columns=rename)


def crawl_vdr_export(csv_path: str | Path) -> list[VDRFile]:
    """
    Parse a VDR platform export file (CSV or XLSX) and return VDRFile objects.
    Handles Datasite, Intralinks, Ansarada, Firmex, and generic formats.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"VDR export not found: {path}")

    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path, dtype=str)
    else:
        # Try common CSV encodings
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                df = pd.read_csv(path, dtype=str, encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Could not read CSV with any supported encoding: {path}")

    df = _normalise_columns(df)
    df = df.fillna("")

    files: list[VDRFile] = []
    for _, row in df.iterrows():
        filename = str(row.get("filename", "")).strip()
        if not filename:
            continue

        folder = str(row.get("folder_path", "")).strip()
        raw_size = str(row.get("size_kb", "0")).replace(",", "").strip()
        try:
            size_kb = round(float(raw_size) / 1024, 1) if float(raw_size) > 1024 else round(float(raw_size), 1)
        except (ValueError, TypeError):
            size_kb = 0.0

        date_modified = str(row.get("date_modified", "")).strip() or None
        ext = str(row.get("file_extension", "")).strip()
        if not ext:
            ext = Path(filename).suffix.lower()

        files.append(
            VDRFile(
                id=str(uuid.uuid4()),
                folder_path=folder,
                filename=filename,
                file_extension=ext,
                size_kb=size_kb,
                date_modified=date_modified,
                source=DocumentSource.csv,
            )
        )
    return files


# ---------------------------------------------------------------------------
# DB Crawler (aigis-poc PostgreSQL)
# ---------------------------------------------------------------------------

def crawl_db(deal_id: str, connection_string: str | None = None) -> list[VDRFile]:
    """
    Query the aigis-poc PostgreSQL documents table for a given deal_id.
    Returns VDRFile objects using the already-ingested doc_type as classification.
    Gracefully returns empty list if DB is unavailable.
    """
    try:
        import psycopg
        from aigis_agents.shared.db_bridge import get_connection_string
        conn_str = connection_string or get_connection_string()
        with psycopg.connect(conn_str) as conn:
            rows = conn.execute(
                """
                SELECT id, filename, doc_type, processing_status, storage_path,
                       metadata, upload_date
                FROM documents
                WHERE deal_id = %s AND processing_status = 'complete'
                ORDER BY upload_date
                """,
                (deal_id,),
            ).fetchall()
    except Exception:
        # DB not available — return empty (crawler will fall back to filesystem)
        return []

    files: list[VDRFile] = []
    for row in rows:
        doc_id, filename, doc_type, status, storage_path, metadata, upload_date = row
        # Extract folder from storage_path if available, e.g. s3://aigis-vdr/{deal_id}/{doc_id}/filename
        folder = ""
        if storage_path:
            parts = storage_path.rstrip("/").split("/")
            folder = "/".join(parts[:-1]).replace(f"s3://aigis-vdr/{deal_id}/", "")

        files.append(
            VDRFile(
                id=str(doc_id),
                folder_path=folder,
                filename=filename,
                file_extension=Path(filename).suffix.lower(),
                size_kb=0.0,  # not stored in DB
                date_modified=upload_date.strftime("%Y-%m-%d") if upload_date else None,
                source=DocumentSource.db,
                classification=doc_type,
            )
        )
    return files


# ---------------------------------------------------------------------------
# Merge Sources
# ---------------------------------------------------------------------------

def merge_sources(sources: list[list[VDRFile]]) -> list[VDRFile]:
    """
    Merge VDRFile lists from multiple crawlers, deduplicating by (filename + folder_path).
    DB entries take precedence (carry classification already).
    """
    seen: dict[str, VDRFile] = {}  # key = normalised (folder + filename)

    for file_list in sources:
        for f in file_list:
            key = f"{f.folder_path.lower()}/{f.filename.lower()}"
            if key not in seen:
                seen[key] = f
            else:
                # DB classification takes precedence
                existing = seen[key]
                if f.source == DocumentSource.db and existing.source != DocumentSource.db:
                    # Merge: keep DB id/classification, update with filesystem metadata
                    merged = f.model_copy(update={
                        "size_kb": existing.size_kb or f.size_kb,
                        "date_modified": existing.date_modified or f.date_modified,
                    })
                    seen[key] = merged

    return list(seen.values())
