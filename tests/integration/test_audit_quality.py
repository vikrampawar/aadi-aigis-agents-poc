"""Tests for audit pass/fail behaviour under different output quality levels."""
import json
import pytest
from aigis_agents.mesh.agent_base import AgentBase
from helpers import MockLLM, VALID_OUTPUT_AUDIT, FAILING_INPUT_AUDIT  # type: ignore[import]


class QualityTestAgent(AgentBase):
    """Agent whose _run() output quality is configurable for testing."""
    AGENT_ID = "agent_02"
    DK_TAGS = []

    def __init__(self, output_override: dict | None = None):
        super().__init__()
        self._output_override = output_override or {}

    def _run(self, deal_id, main_llm, dk_context, patterns,
             mode="standalone", output_dir="./outputs", **inputs) -> dict:
        base = {"result": "test", "files_processed": 1}
        base.update(self._output_override)
        return base


@pytest.mark.integration
class TestAuditPassFail:

    def test_high_quality_output_passes_audit(
        self, patch_toolkit, tmp_path, deal_id, monkeypatch
    ):
        monkeypatch.setattr(
            "aigis_agents.mesh.agent_base.get_chat_model",
            lambda *a, **k: MockLLM(responses={
                "Input Quality Auditor": '{"valid": true, "issues": [], "confidence": "HIGH"}',
                "Output Quality Auditor": VALID_OUTPUT_AUDIT,
            }),
        )
        result = QualityTestAgent().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path)
        )
        assert result["status"] == "success"
        assert result["audit"]["output_confidence"] in ("HIGH", "MEDIUM")

    def test_low_quality_output_still_returns_result(
        self, patch_toolkit, tmp_path, deal_id, monkeypatch
    ):
        """Low confidence should not abort — just flag it in audit block."""
        low_quality_audit = json.dumps({
            "confidence_label": "LOW",
            "confidence_score": 35,
            "citation_coverage": 0.20,
            "flags": [{"type": "missing_citations", "message": "Most values lack sources"}],
            "improvement_suggestions": [
                {"type": "add_citations", "description": "Add source_page to all extracted values"}
            ],
        })
        monkeypatch.setattr(
            "aigis_agents.mesh.agent_base.get_chat_model",
            lambda *a, **k: MockLLM(responses={
                "Input Quality Auditor": '{"valid": true, "issues": [], "confidence": "HIGH"}',
                "Output Quality Auditor": low_quality_audit,
            }),
        )
        result = QualityTestAgent().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path)
        )
        assert result["status"] == "success"
        assert result["audit"]["output_confidence"] == "LOW"

    def test_low_quality_suggestions_queued_to_memory(
        self, patch_toolkit, tmp_path, deal_id, monkeypatch
    ):
        """Improvement suggestions from output audit go to MemoryManager."""
        queued = []

        import aigis_agents.mesh.agent_base as ab
        original_queue = ab._memory.queue_suggestion

        def capture_queue(suggestion):
            queued.append(suggestion)
            return original_queue(suggestion)

        monkeypatch.setattr(ab._memory, "queue_suggestion", capture_queue)

        suggestion_audit = json.dumps({
            "confidence_label": "MEDIUM",
            "confidence_score": 65,
            "citation_coverage": 0.50,
            "flags": [],
            "improvement_suggestions": [
                {"type": "add_citations", "description": "Add source_cell to Excel datapoints"}
            ],
        })
        monkeypatch.setattr(
            "aigis_agents.mesh.agent_base.get_chat_model",
            lambda *a, **k: MockLLM(responses={
                "Input Quality Auditor": '{"valid": true, "issues": [], "confidence": "HIGH"}',
                "Output Quality Auditor": suggestion_audit,
            }),
        )
        QualityTestAgent().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path)
        )
        assert len(queued) >= 1

    def test_error_severity_input_issue_blocks_run(
        self, patch_toolkit, tmp_path, deal_id, monkeypatch
    ):
        """ERROR-severity input issue must abort before _run() is called."""
        run_called = {"n": 0}

        class TrackingAgent(AgentBase):
            AGENT_ID = "agent_02"
            DK_TAGS = []
            def _run(self, *a, **k):
                run_called["n"] += 1
                return {}

        monkeypatch.setattr(
            "aigis_agents.mesh.agent_base.get_chat_model",
            lambda *a, **k: MockLLM(responses={"Input Quality Auditor": FAILING_INPUT_AUDIT}),
        )

        result = TrackingAgent().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path)
        )
        assert result["status"] == "error"
        assert result["error_type"] == "input_validation_failed"
        assert run_called["n"] == 0

    def test_audit_fallback_does_not_block_run(
        self, patch_toolkit, tmp_path, deal_id, monkeypatch
    ):
        """Broken LLM JSON in audit must not crash the agent run."""
        monkeypatch.setattr(
            "aigis_agents.mesh.agent_base.get_chat_model",
            lambda *a, **k: MockLLM(responses={
                "Input Quality Auditor": "NOT VALID JSON {{{",
                "Output Quality Auditor": "ALSO BROKEN",
            }),
        )
        result = QualityTestAgent().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path)
        )
        assert result["status"] == "success"

    def test_cost_key_stripped_from_data(
        self, patch_toolkit, tmp_path, deal_id, monkeypatch
    ):
        monkeypatch.setattr(
            "aigis_agents.mesh.agent_base.get_chat_model",
            lambda *a, **k: MockLLM(responses={
                "Input Quality Auditor": '{"valid": true, "issues": [], "confidence": "HIGH"}',
                "Output Quality Auditor": VALID_OUTPUT_AUDIT,
            }),
        )

        class CostAgent(AgentBase):
            AGENT_ID = "agent_02"
            DK_TAGS = []
            def _run(self, *a, **k):
                return {
                    "result": "ok",
                    "_cost": {"main_llm_usd": 0.05, "audit_llm_usd": 0.01, "total_usd": 0.06},
                }

        result = CostAgent().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path)
        )
        # _cost is popped from data before returning
        assert "_cost" not in result.get("data", {})
        assert result["status"] == "success"
