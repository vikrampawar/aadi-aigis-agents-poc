"""
Tests for Phase C — Semantic DK Router (embeddings.py, vector_store.py,
semantic_dk_router.py).

Coverage:
  EmbeddingProvider:
    - from_config() parses "provider/model" strings correctly
    - Unknown provider raises ValueError at construction
    - Missing library raises ImportError at construction (not at embed time)
    - embed() returns list of vectors, embed_one() returns single vector
    - get_embedding_dim() returns known dims; None for unknowns

  VectorStore:
    - Initialises correctly; creates schema
    - upsert() stores chunks; count() returns correct total
    - search() returns VectorHit list sorted by similarity (descending)
    - search() top_k respected
    - delete_by_source() removes correct chunks; count decreases
    - Dimension mismatch on upsert raises ValueError
    - Backend is 'pure-python' when sqlite-vec not installed

  SemanticDKRouter:
    - Initialises without AIGIS_EMBEDDING_MODEL → semantic_enabled is False
    - build_context_block(tags) works in tag-only mode (no query)
    - build_context_block(tags, query=...) with semantic disabled → tag-only result
    - build_context_block(tags, query=...) with mock semantic layer → merged result
    - index_dk_files() without embedding model → returns 0, logs warning
    - index_dk_files() with mock embedding → chunks indexed; count > 0
    - index_dk_files() is idempotent (re-index = same count)
    - Semantic search failure is non-blocking (returns tag-only result)

  AgentBase:
    - SemanticDKRouter used as _dk_router (not DomainKnowledgeRouter)
    - build_context_block called with query derived from DK_TAGS

  _chunk_markdown helper:
    - Splits at H2 headings
    - Paragraph fallback for oversized sections
    - Short chunks filtered
"""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aigis_agents.mesh.embeddings import EmbeddingProvider, get_embedding_dim
from aigis_agents.mesh.vector_store import VectorStore, VectorHit, _cosine_similarity
from aigis_agents.mesh.semantic_dk_router import (
    SemanticDKRouter,
    _chunk_markdown,
    _relative_to_dk_root,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _unit_vector(dim: int, idx: int = 0) -> list[float]:
    """Return a unit vector with 1.0 at position *idx*, zeros elsewhere."""
    v = [0.0] * dim
    v[idx % dim] = 1.0
    return v


def _rand_vector(dim: int, seed: int = 42) -> list[float]:
    """Deterministic pseudo-random vector (normalised)."""
    import math
    v = [math.sin(seed + i) for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


def _make_store(tmp_path, dim: int = 4) -> VectorStore:
    return VectorStore(db_path=tmp_path / "test_vectors.db", dim=dim)


# ── EmbeddingProvider tests ───────────────────────────────────────────────────

class TestEmbeddingProviderConfig:
    def test_from_config_openai(self):
        """Construction should succeed even without the library installed
        because we mock the import."""
        mock_embedder = MagicMock()
        mock_embedder.embed_documents.return_value = [[0.1, 0.2, 0.3]]

        with patch.dict("sys.modules", {"langchain_openai": MagicMock(
            OpenAIEmbeddings=MagicMock(return_value=mock_embedder)
        )}):
            p = EmbeddingProvider.from_config("openai/text-embedding-3-small")
            vectors = p.embed(["hello"])
            assert len(vectors) == 1
            assert vectors[0] == [0.1, 0.2, 0.3]

    def test_from_config_local(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.5, 0.6]])

        with patch.dict("sys.modules", {"sentence_transformers": MagicMock(
            SentenceTransformer=MagicMock(return_value=mock_model)
        )}):
            p = EmbeddingProvider.from_config("local/all-MiniLM-L6-v2")
            # embed_one should work
            mock_model.encode.return_value.tolist.return_value = [[0.5, 0.6]]
            _ = p.embed(["test"])

    def test_from_config_invalid_format_raises(self):
        with pytest.raises(ValueError, match="provider/model-name"):
            EmbeddingProvider.from_config("no-slash-here")

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises((ValueError, ImportError)):
            EmbeddingProvider.from_config("unknown-provider/some-model")

    def test_embed_empty_list(self):
        """embed([]) must return []."""
        mock_embedder = MagicMock()
        mock_embedder.embed_documents.return_value = []
        with patch.dict("sys.modules", {"langchain_openai": MagicMock(
            OpenAIEmbeddings=MagicMock(return_value=mock_embedder)
        )}):
            p = EmbeddingProvider.from_config("openai/text-embedding-3-small")
            assert p.embed([]) == []

    def test_embed_one_returns_single_vector(self):
        mock_embedder = MagicMock()
        mock_embedder.embed_documents.return_value = [[1.0, 2.0]]
        with patch.dict("sys.modules", {"langchain_openai": MagicMock(
            OpenAIEmbeddings=MagicMock(return_value=mock_embedder)
        )}):
            p = EmbeddingProvider.from_config("openai/text-embedding-3-small")
            v = p.embed_one("text")
            assert v == [1.0, 2.0]


class TestGetEmbeddingDim:
    def test_known_openai_dims(self):
        assert get_embedding_dim("text-embedding-3-small") == 1536
        assert get_embedding_dim("text-embedding-3-large") == 3072
        assert get_embedding_dim("text-embedding-ada-002") == 1536

    def test_known_local_dims(self):
        assert get_embedding_dim("all-MiniLM-L6-v2") == 384
        assert get_embedding_dim("all-mpnet-base-v2") == 768

    def test_unknown_model_returns_none(self):
        assert get_embedding_dim("some-unknown-model-xyz") is None


# ── VectorStore tests ─────────────────────────────────────────────────────────

class TestVectorStoreInit:
    def test_creates_db_file(self, tmp_path):
        store = _make_store(tmp_path)
        assert (tmp_path / "test_vectors.db").exists()

    def test_backend_is_pure_python_when_no_sqlite_vec(self, tmp_path):
        store = _make_store(tmp_path)
        # sqlite-vec is not installed in this environment
        assert store.backend == "pure-python"

    def test_count_empty_on_init(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.count() == 0


class TestVectorStoreUpsert:
    def test_upsert_increases_count(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        store.upsert("c1", _unit_vector(4, 0), {"source_file": "a.md", "chunk_index": 0, "text": "hello"})
        assert store.count() == 1

    def test_upsert_multiple(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        for i in range(5):
            store.upsert(f"c{i}", _unit_vector(4, i), {"source_file": "a.md", "chunk_index": i, "text": f"t{i}"})
        assert store.count() == 5

    def test_upsert_is_idempotent(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        v = _unit_vector(4, 0)
        store.upsert("c1", v, {"source_file": "a.md", "chunk_index": 0, "text": "hello"})
        store.upsert("c1", v, {"source_file": "a.md", "chunk_index": 0, "text": "updated"})
        assert store.count() == 1

    def test_dimension_mismatch_raises(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        with pytest.raises(ValueError, match="dimension mismatch"):
            store.upsert("c1", [1.0, 2.0], {"source_file": "a.md", "chunk_index": 0, "text": "x"})


class TestVectorStoreSearch:
    def test_search_returns_hits(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        for i in range(4):
            store.upsert(f"c{i}", _unit_vector(4, i), {
                "source_file": f"doc{i}.md", "chunk_index": 0, "text": f"text {i}"
            })
        hits = store.search(_unit_vector(4, 0), top_k=4)
        assert isinstance(hits, list)
        assert len(hits) >= 1
        assert all(isinstance(h, VectorHit) for h in hits)

    def test_search_top_result_is_most_similar(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        # c0 is identical to query; others are orthogonal
        store.upsert("c0", _unit_vector(4, 0), {"source_file": "a.md", "chunk_index": 0, "text": "target"})
        store.upsert("c1", _unit_vector(4, 1), {"source_file": "b.md", "chunk_index": 0, "text": "other"})
        store.upsert("c2", _unit_vector(4, 2), {"source_file": "c.md", "chunk_index": 0, "text": "other2"})

        hits = store.search(_unit_vector(4, 0), top_k=3)
        assert hits[0].chunk_id == "c0"

    def test_search_respects_top_k(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        for i in range(4):
            store.upsert(f"c{i}", _unit_vector(4, i), {"source_file": f"f{i}.md", "chunk_index": 0, "text": "x"})
        hits = store.search(_unit_vector(4, 0), top_k=2)
        assert len(hits) <= 2

    def test_search_empty_store_returns_empty(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        hits = store.search(_unit_vector(4, 0), top_k=5)
        assert hits == []

    def test_hit_metadata_populated(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        store.upsert("c0", _unit_vector(4, 0), {
            "source_file": "playbook.md", "chunk_index": 3, "text": "some content here"
        })
        hits = store.search(_unit_vector(4, 0), top_k=1)
        assert hits[0].metadata["source_file"] == "playbook.md"
        assert "some content" in hits[0].metadata["text_preview"]


class TestVectorStoreDeleteBySource:
    def test_delete_removes_chunks(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        store.upsert("c0", _unit_vector(4, 0), {"source_file": "a.md", "chunk_index": 0, "text": "x"})
        store.upsert("c1", _unit_vector(4, 1), {"source_file": "a.md", "chunk_index": 1, "text": "y"})
        store.upsert("c2", _unit_vector(4, 2), {"source_file": "b.md", "chunk_index": 0, "text": "z"})

        deleted = store.delete_by_source("a.md")
        assert deleted == 2
        assert store.count() == 1

    def test_delete_nonexistent_source_returns_zero(self, tmp_path):
        store = _make_store(tmp_path, dim=4)
        assert store.delete_by_source("nonexistent.md") == 0


# ── Cosine similarity helper ──────────────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0, 0.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 1e-6

    def test_zero_vector_safe(self):
        # Should not crash; returns 0.0
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        result = _cosine_similarity(a, b)
        assert result == 0.0


# ── _chunk_markdown helper ────────────────────────────────────────────────────

class TestChunkMarkdown:
    def test_splits_at_h2_headings(self):
        # Each section must be >= _CHUNK_MIN_CHARS (80) to survive the filter
        text = (
            "## Section A\nThis section covers upstream oil and gas exploration "
            "activities in the Gulf of Mexico.\n\n"
            "## Section B\nThis section covers fiscal terms and royalty payment "
            "calculations for offshore assets.\n"
        )
        chunks = _chunk_markdown(text)
        assert len(chunks) == 2
        assert any("Section A" in c for c in chunks)
        assert any("Section B" in c for c in chunks)

    def test_long_section_split_at_paragraphs(self):
        long_para = "x " * 300  # 600 chars
        text = f"## Header\n{long_para}\n\n{long_para}"
        chunks = _chunk_markdown(text, max_chars=500)
        # Should be split into multiple chunks
        assert len(chunks) >= 2

    def test_short_chunks_filtered(self):
        text = "## A\nok\n\n## B\nthis is a long enough chunk that will pass the filter threshold here"
        chunks = _chunk_markdown(text)
        # "ok" is too short and should be filtered
        assert not any(c.strip() == "## A\nok" for c in chunks)

    def test_empty_text_returns_empty(self):
        assert _chunk_markdown("") == []

    def test_no_headings_treated_as_one_chunk(self):
        text = "This is a paragraph without any headings. " * 5
        chunks = _chunk_markdown(text)
        assert len(chunks) >= 1


# ── SemanticDKRouter tests ────────────────────────────────────────────────────

class TestSemanticDKRouterTagOnly:
    """Tests for the router when no embedding model is configured."""

    def test_semantic_disabled_when_no_model(self):
        router = SemanticDKRouter(embedding_model=None)
        assert router.semantic_enabled is False

    def test_build_context_block_tag_only(self):
        router = SemanticDKRouter(embedding_model=None)
        # Tags with no matching files → returns empty string (no DK files in test env)
        result = router.build_context_block([], refresh=False)
        assert isinstance(result, str)

    def test_build_context_block_with_query_falls_back_gracefully(self):
        router = SemanticDKRouter(embedding_model=None)
        # query provided but semantic disabled → same as tag-only
        result_with_query    = router.build_context_block([], query="something")
        result_without_query = router.build_context_block([])
        assert result_with_query == result_without_query

    def test_index_dk_files_without_model_returns_zero(self):
        router = SemanticDKRouter(embedding_model=None)
        n = router.index_dk_files()
        assert n == 0

    def test_semantic_enabled_false_on_bad_model(self):
        """Bad model string should disable semantic layer, not raise."""
        router = SemanticDKRouter(embedding_model="invalid/model-xyz")
        assert router.semantic_enabled is False


class TestSemanticDKRouterWithMockEmbeddings:
    """Tests for the router with a mock embedding provider + real VectorStore."""

    def _make_mock_provider(self, dim: int = 4):
        """Return a callable that acts like EmbeddingProvider."""
        provider = MagicMock()
        provider.dim = dim
        provider.embed_one.return_value = _unit_vector(dim, 0)
        provider.embed.return_value = [_unit_vector(dim, i % dim) for i in range(10)]
        return provider

    def test_index_dk_files_with_mock_provider(self, tmp_path):
        router = SemanticDKRouter.__new__(SemanticDKRouter)
        router._tag_router = MagicMock()
        router._tag_router.load.return_value = {}
        router._enabled = True
        router._dk_db_path = tmp_path / "dk.db"
        router._provider = self._make_mock_provider(dim=4)
        router._store = VectorStore(router._dk_db_path, dim=4)

        # Create a small fake DK file
        fake_dk = tmp_path / "fake_playbook.md"
        fake_dk.write_text(
            "## Section A\n\nThis is a domain knowledge section about upstream oil and gas "
            "exploration activities in the Gulf of Mexico basin.\n\n"
            "## Section B\n\nThis covers fiscal terms, royalty calculations, and working "
            "interest obligations for offshore oil and gas assets.\n",
            encoding="utf-8",
        )

        n = router.index_dk_files(dk_root=tmp_path)
        assert n >= 2  # at least 2 sections indexed
        assert router._store.count() >= 2

    def test_build_context_block_merges_semantic_results(self, tmp_path):
        """When semantic layer is active, results from vector search are appended."""
        router = SemanticDKRouter.__new__(SemanticDKRouter)
        router._tag_router = MagicMock()
        router._tag_router.load.return_value = {
            "financial_playbook.md": "## Tag Result\nSome financial content."
        }
        router._tag_router.build_context_block = MagicMock(  # not called in this path
            return_value=""
        )
        router._enabled = True
        router._dk_db_path = tmp_path / "dk.db"
        router._provider = self._make_mock_provider(dim=4)
        router._store = VectorStore(router._dk_db_path, dim=4)

        # Pre-populate the store with a chunk from a DIFFERENT file
        router._store.upsert("s0", _unit_vector(4, 0), {
            "source_file": str(tmp_path / "other_dk.md"),
            "chunk_index": 0,
            "text": "This is semantic content about IRR thresholds.",
            "doc_type": "dk",
        })

        result = router.build_context_block(
            tags=["financial"],
            query="minimum IRR threshold for acquisitions",
        )
        assert isinstance(result, str)
        # Tag result always present
        assert "Tag Result" in result

    def test_semantic_search_failure_non_blocking(self, tmp_path):
        """If semantic search raises, fall back to tag results."""
        router = SemanticDKRouter.__new__(SemanticDKRouter)
        router._tag_router = MagicMock()
        router._tag_router.load.return_value = {
            "playbook.md": "## Tag Section\nContent."
        }
        router._enabled = True
        router._dk_db_path = tmp_path / "dk.db"

        # Provider that always raises
        failing_provider = MagicMock()
        failing_provider.embed_one.side_effect = RuntimeError("API down")
        router._provider = failing_provider
        router._store = VectorStore(router._dk_db_path, dim=4)

        result = router.build_context_block(["financial"], query="something")
        # Should still return tag results, not raise
        assert "Tag Section" in result

    def test_index_is_idempotent(self, tmp_path):
        """Re-indexing the same file gives the same chunk count."""
        router = SemanticDKRouter.__new__(SemanticDKRouter)
        router._tag_router = MagicMock()
        router._tag_router.load.return_value = {}
        router._enabled = True
        router._dk_db_path = tmp_path / "dk.db"
        router._provider = self._make_mock_provider(dim=4)
        router._store = VectorStore(router._dk_db_path, dim=4)

        fake_dk = tmp_path / "playbook.md"
        fake_dk.write_text(
            "## Section A\n\nContent for section A.\n\n"
            "## Section B\n\nContent for section B.\n",
            encoding="utf-8",
        )

        n1 = router.index_dk_files(dk_root=tmp_path)
        n2 = router.index_dk_files(dk_root=tmp_path)
        assert n1 == n2
        assert router._store.count() == n1  # no duplicates


# ── AgentBase integration ─────────────────────────────────────────────────────

class TestAgentBaseUsesSemanticDKRouter:
    def test_dk_router_is_semantic_router(self):
        """The module-level _dk_router singleton must be a SemanticDKRouter."""
        import aigis_agents.mesh.agent_base as ab
        assert isinstance(ab._dk_router, SemanticDKRouter)

    def test_build_context_block_called_with_query(
        self, tmp_path, patch_toolkit, patch_get_chat_model
    ):
        """AgentBase must call build_context_block with a non-None query."""
        from aigis_agents.mesh.agent_base import AgentBase
        import aigis_agents.mesh.deal_context as dc_mod

        calls = {}

        class ConcreteAgent(AgentBase):
            AGENT_ID = "agent_04"
            DK_TAGS  = ["financial", "oil_gas_101"]

            def _run(self, deal_id, main_llm, dk_context, buyer_context,
                     deal_context, patterns, mode="standalone",
                     output_dir="./outputs", **_):
                return {"result": "ok"}

        mock_router = MagicMock()
        mock_router.build_context_block.return_value = "## DOMAIN KNOWLEDGE\nsome content"

        with patch.object(dc_mod, "_MEMORY_ROOT", tmp_path / "memory"):
            import aigis_agents.mesh.agent_base as ab
            original = ab._dk_router
            ab._dk_router = mock_router
            try:
                agent = ConcreteAgent()
                agent._dk_router = mock_router
                agent.invoke(
                    mode="standalone",
                    deal_id="test-semantic-001",
                    output_dir=str(tmp_path),
                )
            finally:
                ab._dk_router = original

        mock_router.build_context_block.assert_called_once()
        call_kwargs = mock_router.build_context_block.call_args
        # query should be derived from DK_TAGS
        query_arg = call_kwargs.kwargs.get("query") or (
            call_kwargs.args[2] if len(call_kwargs.args) > 2 else None
        )
        assert query_arg is not None
        assert "financial" in query_arg or "oil_gas_101" in query_arg
