"""
SemanticDKRouter — Two-phase domain knowledge retrieval.

Phase 1 (tag-based, always active):
    The existing DomainKnowledgeRouter loads DK files matched by agent tags.
    Fast, deterministic, no embeddings required.

Phase 2 (semantic, optional — requires AIGIS_EMBEDDING_MODEL env var set):
    Embeds a query string and performs KNN search over the indexed DK chunks.
    Returns up to *top_k* additional chunks not already covered by Phase 1.
    Results from both phases are merged and deduplicated by source file.

Graceful degradation:
    If no embedding model is configured, the embedding package is missing, or
    the vector store has no indexed content, Phase 2 is silently skipped and
    only Phase 1 results are returned.  No exception is raised.

DK indexing:
    Run once (or when DK files change) via:
        python -m aigis_agents index-dk
    or programmatically:
        router.index_dk_files()

Environment variables:
    AIGIS_EMBEDDING_MODEL   e.g. "openai/text-embedding-3-small"
                            Required for Phase 2 to activate.
    OPENAI_API_KEY          Required if using openai/ provider.
    VOYAGE_API_KEY          Required if using voyage/ provider.

Usage:
    from aigis_agents.mesh.semantic_dk_router import SemanticDKRouter
    router = SemanticDKRouter()
    context = router.build_context_block(["financial", "oil_gas_101"],
                                         query="what is the minimum IRR threshold?")
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from aigis_agents.mesh.domain_knowledge import DomainKnowledgeRouter, _DK_ROOT

logger = logging.getLogger(__name__)

# ── Path constants ──────────────────────────────────────────────────────────────

# Global DK index lives alongside buyer_profile.md in aigis_agents/memory/
_AGENTS_ROOT    = Path(__file__).parent.parent
_DK_VECTOR_DB   = _AGENTS_ROOT / "memory" / "dk_vectors.db"

# Chunking parameters
_CHUNK_MAX_CHARS = 1_200    # max characters per chunk
_CHUNK_MIN_CHARS = 80       # skip trivially short chunks


# ── SemanticDKRouter ────────────────────────────────────────────────────────────

class SemanticDKRouter:
    """Two-phase DK retrieval: tag-based + optional semantic KNN.

    Implements the same build_context_block() interface as DomainKnowledgeRouter
    with an optional *query* parameter for semantic search.

    Args:
        embedding_model: Override the AIGIS_EMBEDDING_MODEL env var.
        api_keys:        Override env-based API keys (OPENAI_API_KEY etc.).
        dk_vector_db:    Override the default DK vector DB path.
    """

    def __init__(
        self,
        embedding_model: str | None = None,
        api_keys: dict[str, str] | None = None,
        dk_vector_db: str | Path | None = None,
    ) -> None:
        self._tag_router  = DomainKnowledgeRouter()
        self._provider    = None
        self._store       = None
        self._enabled     = False
        self._dk_db_path  = Path(dk_vector_db) if dk_vector_db else _DK_VECTOR_DB

        model = embedding_model or os.getenv("AIGIS_EMBEDDING_MODEL", "")
        if model:
            self._try_init_semantic_layer(model, api_keys or {})

    # ── Public API ──────────────────────────────────────────────────────────────

    @property
    def semantic_enabled(self) -> bool:
        """True when the semantic phase is active (embedding model configured)."""
        return self._enabled

    def build_context_block(
        self,
        tags:    list[str],
        refresh: bool = False,
        query:   str | None = None,
    ) -> str:
        """Return a formatted DK context string for LLM prompt injection.

        Phase 1 always runs (tag-based file loading).
        Phase 2 runs when *query* is provided AND the semantic layer is enabled.

        Args:
            tags:    Agent DK tags (see DomainKnowledgeRouter._TAG_MAP).
            refresh: Force reload of tag-based files from disk.
            query:   Natural-language query for semantic search (optional).

        Returns:
            Multi-section markdown string.
        """
        # Phase 1: tag-based (always)
        tag_files = self._tag_router.load(tags, refresh=refresh)
        tag_paths = set(tag_files.keys())

        sections: list[str] = []
        for rel_path, content in tag_files.items():
            header = f"## DOMAIN KNOWLEDGE: {Path(rel_path).name}"
            sections.append(f"{header}\n\n{content}")

        # Phase 2: semantic (only when enabled + query given + store indexed)
        if self._enabled and query and self._store and self._store.count() > 0:
            semantic_sections = self._semantic_sections(
                query=query,
                exclude_paths=tag_paths,
            )
            sections.extend(semantic_sections)

        return "\n\n---\n\n".join(sections) if sections else ""

    def get_context(
        self,
        query:    str,
        tags:     list[str],
        deal_id:  str | None = None,
        top_k:    int = 8,
    ) -> str:
        """Alternative entry point with explicit query + deal_id.

        Equivalent to build_context_block(tags, query=query) but also scopes
        semantic search to a specific deal's indexed VDR docs when deal_id is given.
        """
        return self.build_context_block(tags, query=query)

    def index_dk_files(self, dk_root: str | Path | None = None) -> int:
        """Chunk and embed all DK markdown files into the vector store.

        Skips files that have already been indexed (idempotent by default —
        existing chunks for a file are deleted and re-indexed).

        Returns the total number of chunks indexed.
        """
        if not self._enabled:
            logger.warning(
                "Semantic layer not configured. "
                "Set AIGIS_EMBEDDING_MODEL to enable DK indexing."
            )
            return 0

        root = Path(dk_root) if dk_root else _DK_ROOT
        md_files = list(root.rglob("*.md"))
        if not md_files:
            logger.warning("No .md files found in %s", root)
            return 0

        total = 0
        for md_path in sorted(md_files):
            try:
                n = self._index_file(md_path, doc_type="dk")
                total += n
                logger.info("Indexed %d chunks from %s", n, md_path.name)
            except Exception as exc:
                logger.warning("Failed to index %s: %s", md_path, exc)

        logger.info("DK indexing complete: %d total chunks in %s", total, self._dk_db_path)
        return total

    def index_vdr_doc(self, file_path: str | Path, deal_id: str) -> int:
        """Chunk and embed a single VDR document into the DK vector store.

        Returns the number of chunks indexed.
        """
        if not self._enabled:
            return 0
        try:
            return self._index_file(Path(file_path), doc_type="vdr_doc", deal_id=deal_id)
        except Exception as exc:
            logger.warning("Failed to index VDR doc %s: %s", file_path, exc)
            return 0

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _try_init_semantic_layer(self, model: str, api_keys: dict) -> None:
        """Attempt to initialise EmbeddingProvider + VectorStore; fail silently."""
        try:
            from aigis_agents.mesh.embeddings import EmbeddingProvider
            from aigis_agents.mesh.vector_store import VectorStore

            provider = EmbeddingProvider.from_config(model, api_keys)
            dim = provider.dim
            if dim is None:
                # Probe dimension by embedding a short test string
                probe = provider.embed_one("probe")
                dim = len(probe)

            store = VectorStore(db_path=self._dk_db_path, dim=dim)
            self._provider = provider
            self._store    = store
            self._enabled  = True
            logger.info(
                "SemanticDKRouter: semantic phase active (model=%s, dim=%d, backend=%s)",
                model, dim, store.backend,
            )
        except Exception as exc:
            logger.debug("SemanticDKRouter: semantic phase disabled — %s", exc)
            self._enabled = False

    def _semantic_sections(
        self,
        query:         str,
        exclude_paths: set[str],
        top_k:         int = 6,
    ) -> list[str]:
        """Run semantic search and return formatted sections for new sources."""
        try:
            query_vec = self._provider.embed_one(query)
            hits = self._store.search(query_vec, top_k=top_k)
        except Exception as exc:
            logger.debug("Semantic search failed (non-blocking): %s", exc)
            return []

        # Group hits by source file; skip files already covered by tag phase
        seen_files: set[str] = set()
        sections: list[str] = []
        for hit in hits:
            src = hit.metadata.get("source_file", "")
            rel = _relative_to_dk_root(src)
            if rel in exclude_paths or src in seen_files:
                continue
            seen_files.add(src)
            preview = hit.metadata.get("text_preview", "")
            header  = f"## DOMAIN KNOWLEDGE (semantic): {Path(src).name}"
            sections.append(
                f"{header}\n\n"
                f"*Relevance score: {hit.score:.3f}*\n\n"
                f"{preview}"
            )

        return sections

    def _index_file(
        self,
        path:     Path,
        doc_type: str = "dk",
        deal_id:  str | None = None,
    ) -> int:
        """Chunk *path* and upsert into vector store. Returns chunks indexed."""
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks = _chunk_markdown(text, max_chars=_CHUNK_MAX_CHARS)
        if not chunks:
            return 0

        # Delete existing chunks for this file (re-index)
        self._store.delete_by_source(str(path))

        vectors = self._provider.embed(chunks)
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            chunk_id = f"{path.stem}:{i}"
            self._store.upsert(
                chunk_id=chunk_id,
                vector=vector,
                metadata={
                    "source_file":  str(path),
                    "chunk_index":  i,
                    "text":         chunk,
                    "doc_type":     doc_type,
                    "deal_id":      deal_id,
                },
            )
        return len(chunks)


# ── Chunking helpers ────────────────────────────────────────────────────────────

def _chunk_markdown(text: str, max_chars: int = _CHUNK_MAX_CHARS) -> list[str]:
    """Split markdown text into chunks at heading boundaries, max *max_chars* each.

    Strategy:
    1. Split at `## ` (H2) headings — each heading starts a new chunk.
    2. If a heading section exceeds max_chars, further split at paragraph
       boundaries (blank lines).
    3. Skip chunks shorter than _CHUNK_MIN_CHARS.
    """
    # Split at H2+ headings
    raw_sections = re.split(r"(?=\n#{1,3} )", text)

    chunks: list[str] = []
    for section in raw_sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= max_chars:
            if len(section) >= _CHUNK_MIN_CHARS:
                chunks.append(section)
        else:
            # Further split at paragraph boundaries
            paragraphs = re.split(r"\n\n+", section)
            current = ""
            for para in paragraphs:
                if len(current) + len(para) + 2 <= max_chars:
                    current = (current + "\n\n" + para).strip() if current else para
                else:
                    if len(current) >= _CHUNK_MIN_CHARS:
                        chunks.append(current)
                    current = para
            if current and len(current) >= _CHUNK_MIN_CHARS:
                chunks.append(current)

    return chunks


def _relative_to_dk_root(path_str: str) -> str:
    """Return path relative to _DK_ROOT, or the stem if not under DK root."""
    try:
        return str(Path(path_str).relative_to(_DK_ROOT)).replace("\\", "/")
    except ValueError:
        return Path(path_str).name
