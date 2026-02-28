"""
aigis_agents.mesh — Agent Mesh Infrastructure

Provides the shared plumbing for the Aigis multi-agent mesh:

  ToolkitRegistry     — loads and queries toolkit.json
  DomainKnowledgeRouter — session-cached DK file loader
  MemoryManager       — per-agent JSON-backed persistent memory
  AuditLayer          — dual-LLM input/output auditing
  AgentBase           — base class for all Aigis agents

Usage (for new agents):
    from aigis_agents.mesh import AgentBase

    class Agent06(AgentBase):
        AGENT_ID = "agent_06"
        DK_TAGS  = ["upstream_dd", "golden_questions"]

        def _run(self, deal_id, main_llm, dk_context, patterns, **inputs):
            ...
            return {...}
"""

from aigis_agents.mesh.toolkit_registry import ToolkitRegistry
from aigis_agents.mesh.domain_knowledge import DomainKnowledgeRouter
from aigis_agents.mesh.memory_manager import MemoryManager
from aigis_agents.mesh.audit_layer import AuditLayer
from aigis_agents.mesh.agent_base import AgentBase

__all__ = [
    "ToolkitRegistry",
    "DomainKnowledgeRouter",
    "MemoryManager",
    "AuditLayer",
    "AgentBase",
]
