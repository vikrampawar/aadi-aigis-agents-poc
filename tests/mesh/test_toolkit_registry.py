"""Tests for ToolkitRegistry — toolkit.json loading and agent resolution."""
import json
import pytest
from aigis_agents.mesh.toolkit_registry import ToolkitRegistry


@pytest.mark.unit
class TestToolkitRegistryLoad:

    def test_load_returns_dict(self, patch_toolkit):
        data = ToolkitRegistry.load()
        assert isinstance(data, dict)
        assert "agents" in data

    def test_get_existing_agent(self, patch_toolkit):
        entry = ToolkitRegistry.get("agent_02")
        assert entry["id"] == "agent_02"
        assert entry["status"] == "production"

    def test_get_missing_agent_raises_key_error(self, patch_toolkit):
        with pytest.raises(KeyError):
            ToolkitRegistry.get("agent_99_nonexistent")

    def test_list_agents_all(self, patch_toolkit):
        agents = ToolkitRegistry.list_agents()
        assert "agent_01" in agents
        assert "agent_02" in agents
        assert "agent_04" in agents

    def test_list_agents_production_only(self, patch_toolkit):
        prod = ToolkitRegistry.list_agents(status="production")
        assert "agent_01" in prod
        assert "agent_02" in prod
        assert "agent_04" in prod
        assert "agent_99" not in prod

    def test_list_agents_planned_only(self, patch_toolkit):
        planned = ToolkitRegistry.list_agents(status="planned")
        assert "agent_99" in planned
        assert "agent_01" not in planned

    def test_llm_defaults(self, patch_toolkit):
        defaults = ToolkitRegistry.llm_defaults("agent_02")
        assert defaults["main_model"] == "gpt-4.1"
        assert defaults["audit_model"] == "gpt-4.1-mini"

    def test_dk_tags(self, patch_toolkit):
        tags = ToolkitRegistry.dk_tags("agent_02")
        assert "financial" in tags
        assert "technical" in tags

    def test_is_production(self, patch_toolkit):
        assert ToolkitRegistry.is_production("agent_02") is True
        assert ToolkitRegistry.is_production("agent_99") is False

    def test_is_planned(self, patch_toolkit):
        assert ToolkitRegistry.is_planned("agent_99") is True
        assert ToolkitRegistry.is_planned("agent_02") is False

    def test_get_agent_class_resolves_agent02(self, patch_toolkit):
        """Critical: agent_02 must resolve to Agent02 class."""
        cls = ToolkitRegistry.get_agent_class("agent_02")
        assert cls is not None
        from aigis_agents.agent_02_data_store.agent import Agent02
        assert cls is Agent02

    def test_tool_call_schema(self, patch_toolkit):
        schema = ToolkitRegistry.tool_call_schema("agent_02")
        assert "data" in schema or "conflicts" in schema

    def test_reload_clears_cache(self, patch_toolkit, minimal_toolkit):
        """Reload reads fresh data from disk."""
        ToolkitRegistry.load()
        # Mutate the file
        data = json.loads(minimal_toolkit.read_text())
        data["_test_marker"] = "reload_test"
        minimal_toolkit.write_text(json.dumps(data))
        second = ToolkitRegistry.reload()
        assert second.get("_test_marker") == "reload_test"
