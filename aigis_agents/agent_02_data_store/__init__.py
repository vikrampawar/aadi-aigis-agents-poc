"""
Agent 02 — VDR Financial & Operational Data Store.

Single source of truth for all numerical VDR data. Three operation modes:
  - ingest_vdr:   Full VDR scan and ingestion
  - ingest_file:  Single file ingestion
  - query:        Data retrieval (NL or SQL)
"""

from __future__ import annotations


__all__ = ["Agent02"]


def __getattr__(name: str):
    if name == "Agent02":
        from aigis_agents.agent_02_data_store.agent import Agent02
        return Agent02
    raise AttributeError(name)
