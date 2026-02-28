"""Aigis Agents — architecture-agnostic AI agents for upstream O&G M&A due diligence."""

from __future__ import annotations


def __getattr__(name: str):
    """Lazy imports — avoids loading all deps at package import time."""
    if name == "vdr_inventory_agent":
        from aigis_agents.agent_01_vdr_inventory.agent import vdr_inventory_agent
        return vdr_inventory_agent
    raise AttributeError(f"module 'aigis_agents' has no attribute {name!r}")


__all__ = ["vdr_inventory_agent"]
