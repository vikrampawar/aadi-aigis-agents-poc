"""Tests for AgentBase pipeline — envelope, error paths, call_agent."""
import pytest
from aigis_agents.mesh.agent_base import AgentBase
from helpers import MockLLM, FAILING_INPUT_AUDIT  # type: ignore[import]


class MinimalAgent(AgentBase):
    """Concrete test subclass with no-op _run."""
    AGENT_ID = "agent_02"  # use a real registered agent_id
    DK_TAGS = []

    def _run(self, deal_id, main_llm, dk_context, patterns,
             mode="standalone", output_dir="./outputs", **inputs) -> dict:
        return {"test_result": "ok", "inputs_echo": inputs}


@pytest.mark.unit
class TestAgentBaseEnvelope:

    def test_invoke_returns_success_status(self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id):
        agent = MinimalAgent()
        result = agent.invoke(mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path))
        assert result["status"] == "success"

    def test_invoke_includes_agent_id(self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id):
        result = MinimalAgent().invoke(mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path))
        assert result["agent"] == "agent_02"

    def test_invoke_includes_deal_id(self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id):
        result = MinimalAgent().invoke(mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path))
        assert result["deal_id"] == deal_id

    def test_invoke_includes_audit_block(self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id):
        result = MinimalAgent().invoke(mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path))
        assert "audit" in result
        assert "output_confidence" in result["audit"]

    def test_invoke_data_contains_run_output(self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id):
        result = MinimalAgent().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path), custom_kwarg="hello"
        )
        assert result["data"]["test_result"] == "ok"
        assert result["data"]["inputs_echo"].get("custom_kwarg") == "hello"

    def test_invoke_includes_run_metadata(self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id):
        result = MinimalAgent().invoke(mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path))
        assert "run_metadata" in result
        assert "duration_s" in result["run_metadata"]
        assert result["run_metadata"]["mode"] == "tool_call"

    def test_agent_id_required(self):
        with pytest.raises((ValueError, AttributeError)):
            class NoIdAgent(AgentBase):
                def _run(self, *a, **k):
                    return {}
            NoIdAgent()

    def test_execution_error_returns_error_envelope(self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id):
        class FailingAgent(AgentBase):
            AGENT_ID = "agent_02"
            DK_TAGS = []
            def _run(self, *a, **k):
                raise RuntimeError("Test failure")

        result = FailingAgent().invoke(mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path))
        assert result["status"] == "error"
        assert result["error_type"] == "execution_error"
        assert "Test failure" in result["message"]

    def test_input_validation_failure_aborts_before_run(self, patch_toolkit, tmp_path, deal_id, monkeypatch):
        """If input audit fails, _run() should never be called."""
        run_called = {"called": False}

        class TrackingAgent(AgentBase):
            AGENT_ID = "agent_02"
            DK_TAGS = []
            def _run(self, *a, **k):
                run_called["called"] = True
                return {}

        monkeypatch.setattr(
            "aigis_agents.mesh.agent_base.get_chat_model",
            lambda *a, **k: MockLLM(responses={"Input Quality Auditor": FAILING_INPUT_AUDIT}),
        )

        result = TrackingAgent().invoke(mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path))
        assert result["status"] == "error"
        assert result["error_type"] == "input_validation_failed"
        assert run_called["called"] is False
