"""
Tests for HiddenDKDetector and its two capabilities.

Covers:
  - scan_for_hidden_dk() with mocked LLM (normal, empty, failure)
  - scan_for_hidden_dk() returns empty when no DK files found
  - scan_for_hidden_dk() filters by confidence >= 0.5
  - scan_for_hidden_dk() with pre-extracted text (no file read)
  - check_contradictions() delegates to ConceptGraph.find_contradictions()
  - check_contradictions() graceful when DB absent
  - check_contradictions() returns Contradiction objects with correct severity
  - DKDiscovery dataclass fields
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from helpers import MockLLM

from aigis_agents.mesh.hidden_dk_detector import HiddenDKDetector, DKDiscovery, _list_dk_files, _read_text
from aigis_agents.mesh.concept_graph import ConceptGraph


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def dk_root(tmp_path):
    """Create a minimal DK root with one markdown file."""
    dk_dir = tmp_path / "domain_knowledge"
    dk_dir.mkdir()
    (dk_dir / "fiscal_terms_playbook.md").write_text(
        "# Fiscal Terms\n\n## Royalty\nRoyalty is a payment made to the lessor...\n",
        encoding="utf-8",
    )
    (dk_dir / "technical_analyst_playbook.md").write_text(
        "# Technical Analysis\n\n## Reserve Classification\nSPE-PRMS defines...\n",
        encoding="utf-8",
    )
    return dk_dir


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "02_data_store.db"


_VALID_DK_DISCOVERY = json.dumps([
    {
        "content_excerpt": "Royalty is calculated as a percentage of gross production.",
        "suggested_dk_file": "fiscal_terms_playbook.md",
        "suggested_section": "Royalty",
        "confidence": 0.85,
    }
])

_LOW_CONFIDENCE_DISCOVERY = json.dumps([
    {
        "content_excerpt": "Some vague content.",
        "suggested_dk_file": "fiscal_terms_playbook.md",
        "suggested_section": "Royalty",
        "confidence": 0.3,   # below 0.5 threshold
    }
])


# ── scan_for_hidden_dk ────────────────────────────────────────────────────────

class TestScanForHiddenDK:
    def test_returns_discoveries(self, dk_root):
        llm = MockLLM({"royalty": _VALID_DK_DISCOVERY})
        detector = HiddenDKDetector()
        results = detector.scan_for_hidden_dk(
            file_path="management_presentation.pptx",
            dk_root=dk_root,
            main_llm=llm,
            text="Royalty is calculated as a percentage of gross production.",
        )
        assert len(results) == 1
        disc = results[0]
        assert isinstance(disc, DKDiscovery)
        assert disc.confidence == 0.85
        assert disc.requires_human_review is True
        assert disc.suggested_dk_file == "fiscal_terms_playbook.md"

    def test_filters_low_confidence(self, dk_root):
        llm = MockLLM({"royalty": _LOW_CONFIDENCE_DISCOVERY})
        detector = HiddenDKDetector()
        results = detector.scan_for_hidden_dk(
            file_path="doc.pdf",
            dk_root=dk_root,
            main_llm=llm,
            text="Royalty is calculated as a percentage of gross production.",
        )
        assert results == []   # 0.3 < 0.5 threshold

    def test_empty_text_returns_empty(self, dk_root):
        llm = MockLLM()
        results = HiddenDKDetector().scan_for_hidden_dk(
            file_path="doc.pdf",
            dk_root=dk_root,
            main_llm=llm,
            text="",
        )
        assert results == []

    def test_no_dk_files_returns_empty(self, tmp_path):
        empty_dk = tmp_path / "empty_dk"
        empty_dk.mkdir()
        llm = MockLLM()
        results = HiddenDKDetector().scan_for_hidden_dk(
            file_path="doc.pdf",
            dk_root=empty_dk,
            main_llm=llm,
            text="Some content.",
        )
        assert results == []

    def test_llm_failure_returns_empty(self, dk_root):
        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("LLM down")
        results = HiddenDKDetector().scan_for_hidden_dk(
            file_path="doc.pdf",
            dk_root=dk_root,
            main_llm=llm,
            text="Some content.",
        )
        assert results == []

    def test_bad_json_returns_empty(self, dk_root):
        llm = MockLLM({"royalty": "not-valid-json!!!"})
        results = HiddenDKDetector().scan_for_hidden_dk(
            file_path="doc.pdf",
            dk_root=dk_root,
            main_llm=llm,
            text="royalty content here",
        )
        assert results == []

    def test_empty_array_response_returns_empty(self, dk_root):
        llm = MockLLM({"royalty": "[]"})
        results = HiddenDKDetector().scan_for_hidden_dk(
            file_path="doc.pdf",
            dk_root=dk_root,
            main_llm=llm,
            text="royalty content here",
        )
        assert results == []

    def test_reads_file_when_text_not_provided(self, dk_root, tmp_path):
        doc = tmp_path / "some_doc.md"
        doc.write_text("royalty is calculated based on wellhead value", encoding="utf-8")
        llm = MockLLM({"royalty": _VALID_DK_DISCOVERY})
        results = HiddenDKDetector().scan_for_hidden_dk(
            file_path=str(doc),
            dk_root=dk_root,
            main_llm=llm,
            # text not provided → reads file
        )
        assert isinstance(results, list)

    def test_source_file_attributed_correctly(self, dk_root):
        llm = MockLLM({"royalty": _VALID_DK_DISCOVERY})
        results = HiddenDKDetector().scan_for_hidden_dk(
            file_path="/some/path/management_presentation.pdf",
            dk_root=dk_root,
            main_llm=llm,
            text="royalty calculation",
        )
        assert results[0].source_file == "/some/path/management_presentation.pdf"

    def test_content_excerpt_truncated_to_200(self, dk_root):
        long_excerpt = "x" * 300
        long_response = json.dumps([{
            "content_excerpt": long_excerpt,
            "suggested_dk_file": "fiscal_terms_playbook.md",
            "suggested_section": "Royalty",
            "confidence": 0.9,
        }])
        llm = MockLLM({"x": long_response})
        results = HiddenDKDetector().scan_for_hidden_dk(
            file_path="doc.pdf",
            dk_root=dk_root,
            main_llm=llm,
            text="x" * 10,
        )
        assert len(results[0].content_excerpt) <= 200


# ── check_contradictions ──────────────────────────────────────────────────────

class TestCheckContradictions:
    def test_returns_empty_when_no_db(self, tmp_path):
        detector = HiddenDKDetector()
        result = detector.check_contradictions(
            deal_id="d1",
            db_path=tmp_path / "nonexistent.db",
        )
        assert result == []

    def test_returns_empty_when_no_propositions(self, db_path):
        g = ConceptGraph(db_path)
        g._ensure_schema()
        result = HiddenDKDetector().check_contradictions("d1", db_path)
        assert result == []

    def test_returns_contradictions(self, db_path):
        g = ConceptGraph(db_path)
        g._ensure_schema()
        g.add_proposition("A", "prod", "5,000 BOE/d", source_doc="a.pdf", deal_id="d1")
        g.add_proposition("A", "prod", "1,000 BOE/d", source_doc="b.pdf", deal_id="d1")
        result = HiddenDKDetector().check_contradictions("d1", db_path)
        assert len(result) == 1
        assert result[0].severity == "CRITICAL"

    def test_filters_by_new_doc_id(self, db_path):
        g = ConceptGraph(db_path)
        g._ensure_schema()
        g.add_proposition("A", "prod", "5,000 BOE/d", source_doc="a.pdf", deal_id="d1")
        g.add_proposition("A", "prod", "1,000 BOE/d", source_doc="b.pdf", deal_id="d1")
        # Filter by a doc not in the contradiction
        result = HiddenDKDetector().check_contradictions("d1", db_path, new_doc_id="c.pdf")
        assert result == []

    def test_db_error_returns_empty(self, tmp_path):
        # Pass an invalid path type — should fail gracefully
        result = HiddenDKDetector().check_contradictions("d1", tmp_path / "bad" / "path.db")
        assert result == []


# ── _list_dk_files helper ─────────────────────────────────────────────────────

class TestListDkFiles:
    def test_lists_md_files(self, dk_root):
        files = _list_dk_files(dk_root)
        assert "fiscal_terms_playbook.md" in files
        assert "technical_analyst_playbook.md" in files

    def test_empty_dir_returns_empty(self, tmp_path):
        empty = tmp_path / "empty_dir"
        empty.mkdir()
        assert _list_dk_files(empty) == []

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        assert _list_dk_files(tmp_path / "ghost") == []


# ── _read_text helper ─────────────────────────────────────────────────────────

class TestReadText:
    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("hello world", encoding="utf-8")
        assert _read_text(f) == "hello world"

    def test_nonexistent_file_returns_empty(self, tmp_path):
        assert _read_text(tmp_path / "ghost.txt") == ""

    def test_truncates_long_files(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("x" * 10_000, encoding="utf-8")
        assert len(_read_text(f, max_chars=100)) == 100


# ── DKDiscovery dataclass ─────────────────────────────────────────────────────

class TestDKDiscoveryDataclass:
    def test_requires_human_review_default_true(self):
        d = DKDiscovery(
            source_file="doc.pdf",
            content_excerpt="content",
            suggested_dk_file="file.md",
            suggested_section="Section A",
            confidence=0.8,
        )
        assert d.requires_human_review is True

    def test_fields(self):
        d = DKDiscovery(
            source_file="x.pdf",
            content_excerpt="...",
            suggested_dk_file="dk.md",
            suggested_section="S",
            confidence=0.7,
        )
        assert d.source_file == "x.pdf"
        assert d.confidence == 0.7
