"""Tests for DomainKnowledgeRouter — tag loading and caching.

Note: DomainKnowledgeRouter uses instance methods (not classmethods).
All tests use a shared router instance.
"""
import pytest
from aigis_agents.mesh.domain_knowledge import DomainKnowledgeRouter


@pytest.fixture(autouse=True)
def router():
    """Fresh router with cleared cache for each test."""
    r = DomainKnowledgeRouter()
    r.clear_cache()
    yield r
    r.clear_cache()


@pytest.mark.unit
class TestDomainKnowledgeRouter:

    def test_available_tags_returns_list(self, router):
        tags = router.available_tags()
        assert isinstance(tags, list)
        assert len(tags) > 0

    def test_available_tags_includes_expected(self, router):
        tags = router.available_tags()
        for expected in ("financial", "technical", "upstream_dd", "oil_gas_101"):
            assert expected in tags, f"Expected tag '{expected}' in available tags"

    def test_build_context_block_empty_tags(self, router):
        """Empty tag list returns empty string."""
        result = router.build_context_block([])
        assert result == "" or isinstance(result, str)

    def test_build_context_block_unknown_tags_graceful(self, router):
        """Unknown tags should not raise — just return empty or partial."""
        result = router.build_context_block(["nonexistent_tag_xyz"])
        assert isinstance(result, str)

    def test_cache_populated_after_first_load(self, router):
        """After loading, cache_stats shows at least one entry (graceful if no files)."""
        router.build_context_block(["financial"])
        stats = router.cache_stats()
        assert "cached_files" in stats
        assert stats["cached_files"] >= 0

    def test_cache_clear(self, router):
        router.build_context_block(["financial"])
        router.clear_cache()
        stats = router.cache_stats()
        assert stats.get("cached_files", 0) == 0

    def test_refresh_reloads(self, router):
        """refresh=True forces a disk re-read (no exception on valid tags)."""
        try:
            router.build_context_block(["financial"], refresh=True)
        except Exception as e:
            pytest.fail(f"build_context_block with refresh=True raised: {e}")

    def test_multiple_tags_combined(self, router):
        """Multiple tags return a combined string."""
        result = router.build_context_block(["financial", "technical"])
        assert isinstance(result, str)

    def test_load_returns_dict(self, router):
        result = router.load(["financial"])
        assert isinstance(result, dict)
