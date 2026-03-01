"""
aigis_agents.mesh — Agent Mesh Infrastructure

Provides the shared plumbing for the Aigis multi-agent mesh:

  ToolkitRegistry       — loads and queries toolkit.json
  DomainKnowledgeRouter — session-cached DK file loader
  MemoryManager         — per-agent JSON-backed persistent memory
  AuditLayer            — dual-LLM input/output auditing + preference detection
  AgentBase             — base class for all Aigis agents
  BuyerProfileManager   — persistent buyer profile + preference learning
  DealContextManager    — per-deal accumulating context markdown
  ConceptGraph          — SQLite-backed entity/proposition knowledge graph
  EntityExtractor       — LLM-driven entity + proposition extraction
  HiddenDKDetector      — hidden DK discovery + contradiction detection

Usage (for new agents):
    from aigis_agents.mesh import AgentBase

    class Agent06(AgentBase):
        AGENT_ID = "agent_06"
        DK_TAGS  = ["upstream_dd", "golden_questions"]

        def _run(self, deal_id, main_llm, dk_context, buyer_context,
                 deal_context, entity_context, patterns, **inputs):
            ...
            return {
                ...,
                "_deal_context_section": {
                    "section_name": "Agent 06 — Q&A Summary",
                    "content": "...",
                },
            }
"""

from aigis_agents.mesh.toolkit_registry import ToolkitRegistry
from aigis_agents.mesh.domain_knowledge import DomainKnowledgeRouter
from aigis_agents.mesh.memory_manager import MemoryManager
from aigis_agents.mesh.audit_layer import AuditLayer
from aigis_agents.mesh.agent_base import AgentBase
from aigis_agents.mesh.buyer_profile_manager import BuyerProfileManager, PreferenceSignal
from aigis_agents.mesh.deal_context import DealContextManager, DealContextSection
from aigis_agents.mesh.concept_graph import ConceptGraph, ConceptNode, ConceptEdge, Contradiction
from aigis_agents.mesh.entity_extractor import EntityExtractor, ExtractionResult
from aigis_agents.mesh.hidden_dk_detector import HiddenDKDetector, DKDiscovery

__all__ = [
    "ToolkitRegistry",
    "DomainKnowledgeRouter",
    "MemoryManager",
    "AuditLayer",
    "AgentBase",
    "BuyerProfileManager",
    "PreferenceSignal",
    "DealContextManager",
    "DealContextSection",
    "ConceptGraph",
    "ConceptNode",
    "ConceptEdge",
    "Contradiction",
    "EntityExtractor",
    "ExtractionResult",
    "HiddenDKDetector",
    "DKDiscovery",
]
