"""
VectorStore — SQLite-backed vector store for Aigis semantic search.

Two storage modes depending on what's installed:

  Mode A (sqlite-vec available): Uses the vec0 virtual table for fast
    approximate nearest-neighbour search.  Ideal for large corpora (hundreds
    of VDR document chunks).

  Mode B (pure-Python fallback): Stores embeddings as JSON in a regular
    SQLite column and performs brute-force cosine similarity search in
    Python.  Sufficient for small corpora (DK files = ~100 chunks).

Both modes expose the same public API so callers don't need to know which
is active.  The active mode is reported by VectorStore.backend.

Schema (both modes):
  chunk_metadata(rowid, chunk_id, source_file, chunk_index, text,
                 doc_type, deal_id, embedding_json, created_at)

Additional (Mode A only):
  vec_chunks virtual table with vec0 extension

Usage:
    store = VectorStore(db_path="./dk_vectors.db", dim=1536)
    store.upsert("c-001", [0.1, 0.2, ...], {
        "source_file": "playbook.md",
        "chunk_index": 0,
        "text": "first chunk ...",
        "doc_type": "dk",
    })
    hits = store.search(query_vector, top_k=5)
    for hit in hits:
        print(hit.score, hit.metadata["text_preview"])
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── sqlite-vec availability ─────────────────────────────────────────────────────

_SQLITE_VEC_AVAILABLE = False
try:
    import sqlite_vec  # type: ignore[import]
    _SQLITE_VEC_AVAILABLE = True
except ImportError:
    pass


# ── Dataclasses ─────────────────────────────────────────────────────────────────

@dataclass
class VectorHit:
    chunk_id: str
    score:    float             # higher = more similar (cosine); lower = closer (L2 dist)
    metadata: dict = field(default_factory=dict)
    # metadata keys: source_file, chunk_index, text_preview, doc_type, deal_id


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity in [−1, 1]; 1 = identical direction."""
    dot  = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    denom = norm_a * norm_b
    return dot / denom if denom > 1e-10 else 0.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── VectorStore ─────────────────────────────────────────────────────────────────

class VectorStore:
    """SQLite-backed vector store with sqlite-vec acceleration when available.

    Args:
        db_path: Path to the SQLite database file.  Created if absent.
        dim:     Embedding dimension (must match the EmbeddingProvider used).
    """

    def __init__(self, db_path: str | Path, dim: int) -> None:
        self._db_path = Path(db_path)
        self._dim = dim
        self._use_vec = _SQLITE_VEC_AVAILABLE
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup_schema()
        logger.debug(
            "VectorStore initialised: %s (dim=%d, backend=%s)",
            self._db_path, dim, self.backend,
        )

    # ── Public API ──────────────────────────────────────────────────────────────

    @property
    def backend(self) -> str:
        """Return 'sqlite-vec' or 'pure-python' to indicate active storage mode."""
        return "sqlite-vec" if self._use_vec else "pure-python"

    def upsert(
        self,
        chunk_id: str,
        vector:   list[float],
        metadata: dict,
    ) -> None:
        """Insert or replace a vector with its metadata.

        Args:
            chunk_id: Unique identifier for this chunk.
            vector:   Embedding vector (must match *dim*).
            metadata: Dict with keys: source_file, chunk_index, text, doc_type,
                      deal_id (all optional except source_file + chunk_index + text).
        """
        if len(vector) != self._dim:
            raise ValueError(
                f"Vector dimension mismatch: expected {self._dim}, got {len(vector)}"
            )
        emb_json = json.dumps(vector)
        conn = self._connect()
        try:
            # Get or create chunk_metadata row
            existing = conn.execute(
                "SELECT rowid FROM chunk_metadata WHERE chunk_id = ?", [chunk_id]
            ).fetchone()

            if existing:
                rowid = existing[0]
                conn.execute(
                    """UPDATE chunk_metadata
                       SET source_file=?, chunk_index=?, text=?, doc_type=?,
                           deal_id=?, embedding_json=?
                       WHERE chunk_id=?""",
                    [
                        metadata.get("source_file", ""),
                        metadata.get("chunk_index", 0),
                        metadata.get("text", ""),
                        metadata.get("doc_type", "dk"),
                        metadata.get("deal_id"),
                        emb_json,
                        chunk_id,
                    ],
                )
            else:
                conn.execute(
                    """INSERT INTO chunk_metadata
                       (chunk_id, source_file, chunk_index, text, doc_type,
                        deal_id, embedding_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        chunk_id,
                        metadata.get("source_file", ""),
                        metadata.get("chunk_index", 0),
                        metadata.get("text", ""),
                        metadata.get("doc_type", "dk"),
                        metadata.get("deal_id"),
                        emb_json,
                        _now(),
                    ],
                )
                rowid = conn.execute(
                    "SELECT rowid FROM chunk_metadata WHERE chunk_id=?", [chunk_id]
                ).fetchone()[0]

            # Also write to vec_chunks if sqlite-vec is active
            if self._use_vec:
                import struct
                blob = struct.pack(f"{len(vector)}f", *vector)
                conn.execute(
                    "INSERT OR REPLACE INTO vec_chunks(rowid, embedding) VALUES (?, ?)",
                    [rowid, blob],
                )

            conn.commit()
        finally:
            conn.close()

    def search(
        self,
        query_vector: list[float],
        top_k: int = 8,
    ) -> list[VectorHit]:
        """Return the *top_k* most similar chunks to *query_vector*.

        Results are sorted descending by cosine similarity (highest first).
        """
        if self._use_vec:
            return self._search_vec(query_vector, top_k)
        return self._search_fallback(query_vector, top_k)

    def delete_by_source(self, source_file: str) -> int:
        """Delete all chunks originating from *source_file*.

        Returns the number of rows deleted.
        """
        conn = self._connect()
        try:
            if self._use_vec:
                # Delete from vec_chunks first (requires rowids)
                rowids = [
                    r[0] for r in conn.execute(
                        "SELECT rowid FROM chunk_metadata WHERE source_file=?",
                        [source_file]
                    ).fetchall()
                ]
                for rid in rowids:
                    conn.execute("DELETE FROM vec_chunks WHERE rowid=?", [rid])

            result = conn.execute(
                "DELETE FROM chunk_metadata WHERE source_file=?", [source_file]
            )
            conn.commit()
            return result.rowcount
        finally:
            conn.close()

    def count(self) -> int:
        """Return total number of indexed chunks."""
        conn = self._connect()
        try:
            return conn.execute("SELECT COUNT(*) FROM chunk_metadata").fetchone()[0]
        finally:
            conn.close()

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        if self._use_vec:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)  # type: ignore[name-defined]
            conn.enable_load_extension(False)
        return conn

    def _setup_schema(self) -> None:
        conn = self._connect()
        try:
            # Metadata table (always)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunk_metadata (
                    rowid          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id       TEXT    UNIQUE NOT NULL,
                    source_file    TEXT    NOT NULL,
                    chunk_index    INTEGER NOT NULL DEFAULT 0,
                    text           TEXT    NOT NULL DEFAULT '',
                    doc_type       TEXT    DEFAULT 'dk',
                    deal_id        TEXT,
                    embedding_json TEXT,
                    created_at     TEXT    NOT NULL
                )
            """)
            # Vec virtual table (only when sqlite-vec loaded)
            if self._use_vec:
                conn.execute(
                    f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks "
                    f"USING vec0(embedding float[{self._dim}])"
                )
            conn.commit()
        finally:
            conn.close()

    def _search_vec(self, query_vector: list[float], top_k: int) -> list[VectorHit]:
        """KNN search using sqlite-vec virtual table."""
        import struct
        blob = struct.pack(f"{len(query_vector)}f", *query_vector)
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT m.chunk_id, v.distance,
                       m.source_file, m.chunk_index, m.text, m.doc_type, m.deal_id
                FROM vec_chunks v
                JOIN chunk_metadata m ON v.rowid = m.rowid
                WHERE v.embedding MATCH ?
                  AND k = ?
                ORDER BY v.distance
                """,
                [blob, top_k],
            ).fetchall()
        finally:
            conn.close()

        return [
            VectorHit(
                chunk_id=row[0],
                # sqlite-vec returns L2 distance; convert to similarity for consistency
                score=1.0 / (1.0 + row[1]),
                metadata={
                    "source_file":  row[2],
                    "chunk_index":  row[3],
                    "text_preview": row[4][:300] if row[4] else "",
                    "doc_type":     row[5],
                    "deal_id":      row[6],
                },
            )
            for row in rows
        ]

    def _search_fallback(self, query_vector: list[float], top_k: int) -> list[VectorHit]:
        """Brute-force cosine search using JSON-stored embeddings."""
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT chunk_id, embedding_json, source_file, chunk_index,
                          text, doc_type, deal_id
                   FROM chunk_metadata
                   WHERE embedding_json IS NOT NULL"""
            ).fetchall()
        finally:
            conn.close()

        scored: list[tuple[float, tuple]] = []
        for row in rows:
            try:
                emb = json.loads(row[1])
                score = _cosine_similarity(query_vector, emb)
                scored.append((score, row))
            except (json.JSONDecodeError, ValueError):
                continue

        scored.sort(key=lambda x: -x[0])

        return [
            VectorHit(
                chunk_id=row[0],
                score=score,
                metadata={
                    "source_file":  row[2],
                    "chunk_index":  row[3],
                    "text_preview": row[4][:300] if row[4] else "",
                    "doc_type":     row[5],
                    "deal_id":      row[6],
                },
            )
            for score, row in scored[:top_k]
        ]
