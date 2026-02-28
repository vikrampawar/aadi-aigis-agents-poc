"""Agent 01 — VDR Document Inventory & Gap Analyst."""

from __future__ import annotations


def __getattr__(name: str):
    if name == "vdr_inventory_agent":
        from aigis_agents.agent_01_vdr_inventory.agent import vdr_inventory_agent
        return vdr_inventory_agent
    raise AttributeError(f"module has no attribute {name!r}")


__all__ = ["vdr_inventory_agent"]
