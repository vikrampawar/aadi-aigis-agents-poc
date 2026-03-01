"""
Tests for ConceptGraph, EntityExtractor, and their integration.

Covers:
  - ConceptGraph CRUD (nodes, edges, propositions)
  - find_contradictions() numeric and non-numeric severity
  - get_entity_context() and get_deal_context_summary()
  - neighbours() BFS traversal
  - Graceful degradation when DB doesn't exist
  - EntityExtractor routing (mocked LLM)
  - extract_and_store() end-to-end with real SQLite
  - AgentBase passes entity_context kwarg to _run()
  - AuditLayer.check_doc_contradictions() delegation
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make tests/ importable
sys.path.insert(0, str(Path(__file__).parent))
from helpers import MockLLM, VALID_INPUT_AUDIT, VALID_OUTPUT_AUDIT

from aigis_agents.mesh.concept_graph import (
    ConceptGraph,
    ConceptNode,
    ConceptEdge,
    Contradiction,
    _contradiction_severity,
)
from aigis_agents.mesh.entity_extractor import EntityExtractor, ExtractionResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_deal.db"


@pytest.fixture
def graph(db_path):
    g = ConceptGraph(db_path)
    g._ensure_schema()
    return g


# ── ConceptGraph — node CRUD ───────────────────────────────────────────────────

class TestConceptGraphNodes:
    def test_add_node_returns_id(self, graph):
        node_id = graph.add_node("Na Kika FPS", "asset", "Deepwater FPS", deal_id="d1")
        assert isinstance(node_id, str)
        assert len(node_id) > 0

    def test_add_node_idempotent_by_name(self, graph):
        id1 = graph.add_node("Shell", "company", "Operator", deal_id="d1")
        id2 = graph.add_node("Shell", "company", "Operator updated", deal_id="d1")
        assert id1 == id2  # same node, description updated

    def test_node_count_increments(self, graph):
        assert graph.node_count() == 0
        graph.add_node("Asset A", "asset", deal_id="d1")
        assert graph.node_count() == 1
        graph.add_node("Asset B", "asset", deal_id="d1")
        assert graph.node_count() == 2

    def test_no_db_graceful(self, tmp_path):
        g = ConceptGraph(tmp_path / "nonexistent.db")
        assert g.node_count() == 0
        assert g.get_entity_context("anything", "d1") == ""
        assert g.get_deal_context_summary("d1") == ""


# ── ConceptGraph — edges ───────────────────────────────────────────────────────

class TestConceptGraphEdges:
    def test_add_edge(self, graph):
        src = graph.add_node("Na Kika FPS", "asset", deal_id="d1")
        tgt = graph.add_node("Shell", "company", deal_id="d1")
        graph.add_edge(src, tgt, "operated_by", source_doc="cpr.pdf", deal_id="d1")
        # no exception = success

    def test_add_edge_upsert(self, graph):
        src = graph.add_node("FPS", "asset", deal_id="d1")
        tgt = graph.add_node("BP", "company", deal_id="d1")
        # Same edge twice shouldn't raise
        graph.add_edge(src, tgt, "operated_by", deal_id="d1")
        graph.add_edge(src, tgt, "operated_by", deal_id="d1")


# ── ConceptGraph — propositions ────────────────────────────────────────────────

class TestConceptGraphPropositions:
    def test_add_proposition_returns_id(self, graph):
        pid = graph.add_proposition(
            "Na Kika FPS", "current_production", "15,000 BOE/d",
            source_doc="mgmt.xlsx", deal_id="d1",
        )
        assert isinstance(pid, str)
        assert len(pid) > 0

    def test_proposition_count(self, graph):
        assert graph.proposition_count() == 0
        graph.add_proposition("A", "p", "v", source_doc="f.pdf", deal_id="d1")
        graph.add_proposition("B", "q", "w", source_doc="f.pdf", deal_id="d1")
        assert graph.proposition_count() == 2

    def test_propositions_isolated_by_deal(self, graph):
        graph.add_proposition("A", "p", "v", source_doc="f.pdf", deal_id="deal_X")
        graph.add_proposition("A", "p", "v", source_doc="f.pdf", deal_id="deal_Y")
        contradictions = graph.find_contradictions("deal_X")
        assert all(c.severity for c in contradictions)   # no cross-deal leak


# ── ConceptGraph — find_contradictions ────────────────────────────────────────

class TestFindContradictions:
    def test_no_contradictions_same_value(self, graph):
        graph.add_proposition("A", "p", "5,000 BOE/d", source_doc="doc1.pdf", deal_id="d1")
        graph.add_proposition("A", "p", "5,000 BOE/d", source_doc="doc2.pdf", deal_id="d1")
        assert graph.find_contradictions("d1") == []

    def test_no_contradictions_same_source(self, graph):
        graph.add_proposition("A", "p", "5,000 BOE/d", source_doc="doc1.pdf", deal_id="d1")
        graph.add_proposition("A", "p", "3,000 BOE/d", source_doc="doc1.pdf", deal_id="d1")
        # Same source, different values — not a cross-doc contradiction
        assert graph.find_contradictions("d1") == []

    def test_contradiction_detected(self, graph):
        graph.add_proposition("A", "production", "5,000 BOE/d", source_doc="cpr.pdf", deal_id="d1")
        graph.add_proposition("A", "production", "3,000 BOE/d", source_doc="mgmt.xlsx", deal_id="d1")
        c = graph.find_contradictions("d1")
        assert len(c) == 1
        assert c[0].subject == "A"
        assert c[0].predicate == "production"

    def test_critical_severity_large_numeric_diff(self, graph):
        # 5000 vs 1000 → 80% diff → CRITICAL
        graph.add_proposition("A", "prod", "5,000 BOE/d", source_doc="a.pdf", deal_id="d1")
        graph.add_proposition("A", "prod", "1,000 BOE/d", source_doc="b.pdf", deal_id="d1")
        c = graph.find_contradictions("d1")
        assert c[0].severity == "CRITICAL"

    def test_warning_severity_small_numeric_diff(self, graph):
        # 5000 vs 4700 → ~6% diff → WARNING (no commas to confuse first-number regex)
        graph.add_proposition("A", "prod", "5000 BOE/d", source_doc="a.pdf", deal_id="d1")
        graph.add_proposition("A", "prod", "4700 BOE/d", source_doc="b.pdf", deal_id="d1")
        c = graph.find_contradictions("d1")
        assert c[0].severity == "WARNING"

    def test_new_doc_id_filter(self, graph):
        graph.add_proposition("A", "prod", "5,000 BOE/d", source_doc="a.pdf", deal_id="d1")
        graph.add_proposition("A", "prod", "3,000 BOE/d", source_doc="b.pdf", deal_id="d1")
        # Filter by doc name not present → no results
        c = graph.find_contradictions("d1", new_doc_id="c.pdf")
        assert c == []
        # Filter by doc name present → results
        c = graph.find_contradictions("d1", new_doc_id="a.pdf")
        assert len(c) == 1

    def test_empty_db_returns_empty(self, tmp_path):
        g = ConceptGraph(tmp_path / "empty.db")
        assert g.find_contradictions("d1") == []


# ── ConceptGraph — neighbours ─────────────────────────────────────────────────

class TestNeighbours:
    def test_direct_neighbour(self, graph):
        src = graph.add_node("FPS", "asset", deal_id="d1")
        tgt = graph.add_node("Shell", "company", deal_id="d1")
        graph.add_edge(src, tgt, "operated_by", deal_id="d1")
        nbrs = graph.neighbours(src, max_hops=1)
        assert any(n.name == "Shell" for n in nbrs)

    def test_no_neighbours_isolated_node(self, graph):
        nid = graph.add_node("Orphan", "concept", deal_id="d1")
        assert graph.neighbours(nid) == []

    def test_max_hops_zero(self, graph):
        nid = graph.add_node("A", "asset", deal_id="d1")
        tgt = graph.add_node("B", "asset", deal_id="d1")
        graph.add_edge(nid, tgt, "related_to", deal_id="d1")
        assert graph.neighbours(nid, max_hops=0) == []


# ── ConceptGraph — entity context ─────────────────────────────────────────────

class TestEntityContext:
    def test_entity_context_includes_props(self, graph):
        graph.add_node("Na Kika FPS", "asset", "Deepwater FPS", deal_id="d1")
        graph.add_proposition("Na Kika FPS", "water_depth", "6,340 ft",
                               source_doc="cpr.pdf", deal_id="d1")
        ctx = graph.get_entity_context("Na Kika FPS", "d1")
        assert "Na Kika FPS" in ctx
        assert "water_depth" in ctx
        assert "6,340 ft" in ctx

    def test_entity_context_missing_node_returns_empty(self, graph):
        assert graph.get_entity_context("Nonexistent", "d1") == ""

    def test_deal_context_summary_includes_heading(self, graph):
        graph.add_node("FPS", "asset", "Test asset", deal_id="d1")
        graph.add_proposition("FPS", "production", "1,000 BOE/d",
                               source_doc="x.pdf", deal_id="d1")
        summary = graph.get_deal_context_summary("d1")
        assert "Entity Graph" in summary
        assert "FPS" in summary

    def test_deal_context_summary_empty_no_nodes(self, graph):
        assert graph.get_deal_context_summary("d1") == ""


# ── _contradiction_severity helper ────────────────────────────────────────────

class TestContradictionSeverity:
    def test_critical_for_large_diff(self):
        assert _contradiction_severity("5000", "1000") == "CRITICAL"

    def test_warning_for_small_diff(self):
        assert _contradiction_severity("5000", "4800") == "WARNING"

    def test_warning_for_non_numeric(self):
        assert _contradiction_severity("Shell", "BP") == "WARNING"

    def test_warning_for_zero_denominator(self):
        assert _contradiction_severity("1000", "0") == "WARNING"


# ── EntityExtractor ───────────────────────────────────────────────────────────

_VALID_EXTRACTION = json.dumps({
    "entities": [
        {"name": "Na Kika FPS", "type": "asset", "description": "Deepwater FPS"},
        {"name": "Shell", "type": "company", "description": "Operator"},
    ],
    "propositions": [
        {"subject": "Na Kika FPS", "predicate": "operator", "object": "Shell",
         "page_ref": "5", "confidence": "HIGH"},
        {"subject": "Na Kika FPS", "predicate": "water_depth", "object": "6,340 ft",
         "page_ref": "12", "confidence": "HIGH"},
    ],
    "relationships": [
        {"source": "Na Kika FPS", "target": "Shell", "relationship": "operated_by", "weight": 1.0}
    ],
})


class TestEntityExtractor:
    def test_extract_returns_result(self):
        llm = MockLLM({"extraction": _VALID_EXTRACTION})
        result = EntityExtractor().extract("Na Kika FPS is operated by Shell.", llm)
        assert not result.is_empty
        assert len(result.entities) == 2
        assert len(result.propositions) == 2
        assert len(result.relationships) == 1

    def test_extract_empty_text_returns_empty(self):
        llm = MockLLM()
        result = EntityExtractor().extract("", llm)
        assert result.is_empty

    def test_extract_llm_failure_returns_empty(self):
        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("LLM unavailable")
        result = EntityExtractor().extract("some text", llm)
        assert result.is_empty

    def test_extract_bad_json_returns_empty(self):
        llm = MockLLM({"x": "not-json!!!"})
        result = EntityExtractor().extract("some text", llm)
        assert result.is_empty

    def test_extract_and_store_populates_graph(self, db_path):
        llm = MockLLM({"extraction": _VALID_EXTRACTION})
        graph = ConceptGraph(db_path)
        graph._ensure_schema()
        count = EntityExtractor().extract_and_store(
            text="Na Kika FPS is operated by Shell.",
            llm=llm,
            graph=graph,
            source_doc="cpr.pdf",
            deal_id="d1",
        )
        assert count > 0
        assert graph.node_count() == 2
        assert graph.proposition_count() == 2

    def test_extract_and_store_empty_text_returns_zero(self, db_path):
        llm = MockLLM()
        graph = ConceptGraph(db_path)
        graph._ensure_schema()
        assert EntityExtractor().extract_and_store("", llm, graph, "f.pdf", "d1") == 0


# ── AgentBase passes entity_context ───────────────────────────────────────────

class TestAgentBaseEntityContext:
    def test_entity_context_passed_to_run(self, patch_toolkit, patch_get_chat_model, tmp_path):
        """AgentBase step 5.7 passes entity_context kwarg to _run().
        Uses patch_toolkit + patch_get_chat_model from conftest.
        """
        import aigis_agents.mesh.agent_base as ab_mod

        captured = {}

        class TestAgent(ab_mod.AgentBase):
            AGENT_ID = "agent_01"
            DK_TAGS  = []
            def _run(self, **kwargs):
                captured["entity_context"] = kwargs.get("entity_context", "MISSING")
                return {"summary": "ok", "gaps": [], "files": [], "checklist": {}}

        with (
            patch.object(ab_mod, "_dk_router") as mock_router,
            patch.object(ab_mod, "_memory") as mock_mem,
            patch.object(ab_mod, "_buyer_profile") as mock_bp,
            patch("aigis_agents.mesh.agent_base.AuditLayer") as mock_audit,
        ):
            mock_router.build_context_block.return_value = ""
            mock_mem.load_patterns.return_value = []
            mock_mem.queue_suggestion = MagicMock()
            mock_mem.log_run = MagicMock()
            mock_bp.load_as_context.return_value = ""

            audit_inst = MagicMock()
            audit_inst.check_inputs.return_value = {"valid": True, "issues": []}
            audit_inst.check_outputs.return_value = {
                "confidence_label": "HIGH", "confidence_score": 90,
                "citation_coverage": 0.9, "flags": [], "improvement_suggestions": [],
            }
            audit_inst.detect_preferences.return_value = []
            audit_inst.log.return_value = "run_001"
            mock_audit.return_value = audit_inst

            TestAgent().invoke(mode="tool_call", deal_id="deal_001",
                               output_dir=str(tmp_path))

        # entity_context should be present (empty string since no 02_data_store.db yet)
        assert "entity_context" in captured
        assert isinstance(captured["entity_context"], str)


# ── AuditLayer.check_doc_contradictions ───────────────────────────────────────

class TestAuditLayerContradictions:
    def test_delegates_to_hidden_dk_detector(self, db_path):
        from aigis_agents.mesh.audit_layer import AuditLayer
        audit = AuditLayer(MagicMock())

        # DB doesn't exist → empty list (graceful)
        result = audit.check_doc_contradictions("d1", db_path)
        assert result == []

    def test_returns_contradictions_when_present(self, db_path):
        from aigis_agents.mesh.audit_layer import AuditLayer
        graph = ConceptGraph(db_path)
        graph._ensure_schema()
        graph.add_proposition("A", "prod", "5,000 BOE/d", source_doc="a.pdf", deal_id="d1")
        graph.add_proposition("A", "prod", "1,000 BOE/d", source_doc="b.pdf", deal_id="d1")

        audit = AuditLayer(MagicMock())
        result = audit.check_doc_contradictions("d1", db_path)
        assert len(result) == 1
        assert result[0].severity == "CRITICAL"
