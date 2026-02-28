"""Tests for AuditLayer — input/output auditing and JSONL logging."""
import json
import pytest
from aigis_agents.mesh.audit_layer import AuditLayer
from helpers import MockLLM, VALID_OUTPUT_AUDIT  # type: ignore[import]


@pytest.fixture()
def audit_layer(mock_llm):
    return AuditLayer(mock_llm)


@pytest.fixture()
def failing_audit_layer(strict_mock_llm):
    return AuditLayer(strict_mock_llm)


@pytest.mark.unit
class TestInputAudit:

    def test_valid_inputs_return_valid_true(self, audit_layer, patch_toolkit):
        result = audit_layer.check_inputs(
            "agent_02",
            {"operation": "ingest_file", "file_path": "/some/file.xlsx"},
        )
        assert result.get("valid") is True

    def test_invalid_inputs_return_valid_false(self, failing_audit_layer, patch_toolkit):
        result = failing_audit_layer.check_inputs("agent_02", {})
        assert result.get("valid") is False
        assert len(result.get("issues", [])) > 0

    def test_error_severity_sets_valid_false(self, patch_toolkit):
        llm = MockLLM(responses={
            "Input Quality Auditor": json.dumps({
                "valid": False,
                "confidence": "LOW",
                "issues": [{"severity": "ERROR", "field": "vdr_path", "message": "Missing"}],
            })
        })
        audit = AuditLayer(llm)
        result = audit.check_inputs("agent_01", {})
        assert result["valid"] is False

    def test_malformed_llm_response_falls_back_to_valid(self, patch_toolkit):
        """Transient LLM failures should NOT block runs."""
        llm = MockLLM(responses={"Input Quality Auditor": "THIS IS NOT JSON {{{"})
        audit = AuditLayer(llm)
        result = audit.check_inputs("agent_02", {"operation": "query"})
        assert result.get("valid") is True
        assert result.get("_audit_fallback") is True


@pytest.mark.unit
class TestOutputAudit:

    def test_valid_output_returns_confidence_label(self, audit_layer, patch_toolkit):
        result = audit_layer.check_outputs(
            "agent_02",
            {"operation": "ingest_file"},
            {"files_processed": 1, "data_points_added": 42},
        )
        assert result.get("confidence_label") in ("HIGH", "MEDIUM", "LOW")

    def test_malformed_output_audit_falls_back(self, patch_toolkit):
        llm = MockLLM(responses={"Output Quality Auditor": "broken json{"})
        audit = AuditLayer(llm)
        result = audit.check_outputs("agent_02", {}, {})
        assert result.get("confidence_label") is not None
        assert result.get("_audit_fallback") is True

    def test_improvement_suggestions_in_output(self, patch_toolkit):
        suggestion_response = json.dumps({
            "confidence_label": "MEDIUM",
            "confidence_score": 70,
            "citation_coverage": 0.60,
            "flags": [{"type": "low_coverage", "message": "Only 60% of values have citations"}],
            "improvement_suggestions": [
                {"type": "citation_improvement", "description": "Add source_page to all scalars"}
            ],
        })
        llm = MockLLM(responses={"Output Quality Auditor": suggestion_response})
        audit = AuditLayer(llm)
        result = audit.check_outputs("agent_02", {}, {"data": []})
        assert len(result.get("improvement_suggestions", [])) == 1


@pytest.mark.unit
class TestAuditLog:

    def test_log_creates_jsonl_file(self, audit_layer, patch_toolkit, tmp_path, deal_id):
        run_id = audit_layer.log(
            agent_id="agent_02",
            deal_id=deal_id,
            mode="standalone",
            inputs={"operation": "query"},
            input_audit={"valid": True, "issues": []},
            output_audit={"confidence_label": "HIGH", "flags": []},
            main_model="gpt-4.1",
            audit_model="gpt-4.1-mini",
            cost=None,
            output_dir=str(tmp_path),
        )
        log_path = tmp_path / deal_id / "_audit_log.jsonl"
        assert log_path.exists(), "Audit JSONL file should be created"
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) >= 1
        record = json.loads(lines[-1])
        assert record.get("run_id") == run_id
        assert record.get("agent") == "agent_02"

    def test_multiple_logs_appended(self, audit_layer, patch_toolkit, tmp_path, deal_id):
        for _ in range(3):
            audit_layer.log(
                agent_id="agent_02", deal_id=deal_id, mode="standalone",
                inputs={}, input_audit={"valid": True, "issues": []},
                output_audit={"confidence_label": "HIGH", "flags": []},
                main_model="gpt-4.1", audit_model="gpt-4.1-mini",
                cost=None, output_dir=str(tmp_path),
            )
        log_path = tmp_path / deal_id / "_audit_log.jsonl"
        lines = [ln for ln in log_path.read_text().strip().split("\n") if ln.strip()]
        assert len(lines) == 3
