"""
ToolkitRegistry — loads aigis_agents/toolkit.json and resolves agent modules.

The registry is the single source of truth for:
  - Which agents exist (including planned ones)
  - Their input/output schemas
  - Their LLM defaults
  - Their domain knowledge tags

The JSON is loaded once per process and cached.  Agents that have been migrated
to AgentBase will have a `mesh_class` field set; legacy agents are accessed via
their `invoke_fn` function instead.
"""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable


# toolkit.json lives one directory above this file's parent (aigis_agents/)
_TOOLKIT_PATH = Path(__file__).parent.parent / "toolkit.json"


@lru_cache(maxsize=1)
def _load_raw() -> dict[str, Any]:
    """Load and cache toolkit.json.  Raises FileNotFoundError if missing."""
    if not _TOOLKIT_PATH.exists():
        raise FileNotFoundError(
            f"toolkit.json not found at {_TOOLKIT_PATH}. "
            "Run the mesh initialisation step to create it."
        )
    with _TOOLKIT_PATH.open(encoding="utf-8") as f:
        return json.load(f)


class ToolkitRegistry:
    """Thin wrapper around toolkit.json with convenience accessors."""

    # ── Loading ───────────────────────────────────────────────────────────────

    @staticmethod
    def load() -> dict[str, Any]:
        """Return the full toolkit dict (cached)."""
        return _load_raw()

    @staticmethod
    def reload() -> dict[str, Any]:
        """Force a reload from disk (useful in long-running processes)."""
        _load_raw.cache_clear()
        return _load_raw()

    # ── Agent lookup ──────────────────────────────────────────────────────────

    @staticmethod
    def get(agent_id: str) -> dict[str, Any]:
        """Return the registry entry for *agent_id*.

        Raises KeyError if the agent is not registered.
        """
        agents = _load_raw()["agents"]
        if agent_id not in agents:
            raise KeyError(
                f"Agent '{agent_id}' not found in toolkit.json. "
                f"Registered agents: {', '.join(sorted(agents))}"
            )
        return agents[agent_id]

    @staticmethod
    def list_agents(status: str | None = None) -> list[str]:
        """Return all agent IDs, optionally filtered by status."""
        agents = _load_raw()["agents"]
        if status is None:
            return sorted(agents)
        return sorted(k for k, v in agents.items() if v.get("status") == status)

    @staticmethod
    def llm_defaults(agent_id: str) -> dict[str, str]:
        """Return {'main_model': ..., 'audit_model': ...} for *agent_id*."""
        return ToolkitRegistry.get(agent_id)["llm_defaults"]

    @staticmethod
    def dk_tags(agent_id: str) -> list[str]:
        """Return the domain_knowledge_tags list for *agent_id*."""
        return ToolkitRegistry.get(agent_id).get("dependencies", {}).get(
            "domain_knowledge_tags", []
        )

    # ── Agent class / function resolution ────────────────────────────────────

    @staticmethod
    def get_agent_class(agent_id: str) -> type | None:
        """Return the AgentBase subclass for *agent_id*, or None if not migrated.

        Checks the `mesh_class` field first (post-migration agents), then falls
        back to None.  Callers should use `get_invoke_fn` for legacy agents.
        """
        entry = ToolkitRegistry.get(agent_id)
        class_path: str | None = entry.get("mesh_class")
        if not class_path:
            return None
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    @staticmethod
    def get_invoke_fn(agent_id: str) -> Callable | None:
        """Return the legacy invoke function for *agent_id*, or None.

        Used for agents that have not yet been migrated to AgentBase.
        """
        entry = ToolkitRegistry.get(agent_id)
        module_path: str | None = entry.get("module_path")
        invoke_fn: str | None = entry.get("invoke_fn")
        if not module_path or not invoke_fn:
            return None
        module = importlib.import_module(module_path)
        return getattr(module, invoke_fn, None)

    @staticmethod
    def is_production(agent_id: str) -> bool:
        return ToolkitRegistry.get(agent_id).get("status") == "production"

    @staticmethod
    def is_planned(agent_id: str) -> bool:
        return ToolkitRegistry.get(agent_id).get("status") == "planned"

    # ── Schema helpers ────────────────────────────────────────────────────────

    @staticmethod
    def tool_call_schema(agent_id: str) -> dict[str, str]:
        """Return the tool_call output schema dict for *agent_id*."""
        return (
            ToolkitRegistry.get(agent_id)
            .get("output", {})
            .get("tool_call", {})
            .get("schema", {})
        )

    @staticmethod
    def standalone_files(agent_id: str) -> list[str]:
        """Return the list of output files for standalone mode."""
        return (
            ToolkitRegistry.get(agent_id)
            .get("output", {})
            .get("standalone", {})
            .get("files", [])
        )
