"""Shared fixtures for the Aigis agent mesh test suite."""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

import pytest

from helpers import (  # type: ignore[import]
    FAILING_INPUT_AUDIT,
    VALID_INPUT_AUDIT,
    VALID_OUTPUT_AUDIT,
    MockLLM,
    MockMessage,
)

__all__ = [
    "MockLLM",
    "MockMessage",
    "VALID_INPUT_AUDIT",
    "VALID_OUTPUT_AUDIT",
    "FAILING_INPUT_AUDIT",
]


# ── LLM fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_llm() -> MockLLM:
    return MockLLM(responses={
        "Input Quality Auditor": VALID_INPUT_AUDIT,
        "Output Quality Auditor": VALID_OUTPUT_AUDIT,
        # Agent01 novelty detector prompt always contains this key; return empty proposals.
        "add_to_checklist": "[]",
    })


@pytest.fixture()
def strict_mock_llm() -> MockLLM:
    """LLM that returns a failing input audit — for abort-path tests."""
    return MockLLM(responses={
        "Input Quality Auditor": FAILING_INPUT_AUDIT,
        "Output Quality Auditor": VALID_OUTPUT_AUDIT,
    })


# ── Deal ID fixture ───────────────────────────────────────────────────────────


@pytest.fixture()
def deal_id() -> str:
    return "test-deal-" + str(uuid.uuid4())[:8]


# ── Patch fixtures ────────────────────────────────────────────────────────────


@pytest.fixture()
def patch_get_chat_model(monkeypatch, mock_llm):
    """Replace get_chat_model with a factory returning mock_llm."""
    monkeypatch.setattr(
        "aigis_agents.mesh.agent_base.get_chat_model",
        lambda *args, **kwargs: mock_llm,
    )
    return mock_llm


@pytest.fixture()
def minimal_toolkit(tmp_path) -> Path:
    """Write a minimal toolkit.json to a temp dir; return its path."""
    toolkit = {
        "version": "test-1.0",
        "agents": {
            "agent_01": {
                "id": "agent_01",
                "name": "VDR Inventory",
                "description": "Enumerates and classifies all files in a VDR.",
                "status": "production",
                "agent_version": "2.0",
                "mesh_class": "aigis_agents.agent_01_vdr_inventory.agent.Agent01",
                "llm_defaults": {"main_model": "gpt-4.1", "audit_model": "gpt-4.1-mini"},
                "dependencies": {"domain_knowledge_tags": ["vdr_structure", "checklist"]},
                "output": {
                    "tool_call": {"schema": {"files": "list", "gaps": "list"}},
                    "standalone": {"files": ["01_vdr_inventory.json", "01_gap_analysis_report.md"]},
                },
            },
            "agent_02": {
                "id": "agent_02",
                "name": "VDR Financial & Operational Data Store",
                "description": "Ingests and stores all financial/operational data from VDR.",
                "status": "production",
                "agent_version": "1.0",
                "mesh_class": "aigis_agents.agent_02_data_store.agent.Agent02",
                "llm_defaults": {"main_model": "gpt-4.1", "audit_model": "gpt-4.1-mini"},
                "dependencies": {
                    "agents": ["agent_01", "agent_04"],
                    "domain_knowledge_tags": ["financial", "technical"],
                },
                "output": {
                    "tool_call": {"schema": {"data": "list", "conflicts": "dict"}},
                    "standalone": {"files": ["02_data_store.db", "02_ingestion_report.md"]},
                },
            },
            "agent_04": {
                "id": "agent_04",
                "name": "Upstream Finance Calculator",
                "description": "Computes NPV, IRR, netback, breakeven and other financial metrics.",
                "status": "production",
                "agent_version": "2.0",
                "mesh_class": "aigis_agents.agent_04_finance_calculator.agent.Agent04",
                "llm_defaults": {"main_model": "gpt-4.1", "audit_model": "gpt-4.1-mini"},
                "dependencies": {"domain_knowledge_tags": ["financial", "oil_gas_101"]},
                "output": {
                    "tool_call": {"schema": {"npv_10_usd": "float", "irr_pct": "float"}},
                    "standalone": {"files": ["04_financial_analysis.md", "04_results.json"]},
                },
            },
            "agent_99": {
                "id": "agent_99",
                "name": "Planned Test Agent",
                "description": "A planned agent for future use.",
                "status": "planned",
                "llm_defaults": {"main_model": "gpt-4.1", "audit_model": "gpt-4.1-mini"},
                "dependencies": {"domain_knowledge_tags": []},
            },
        },
    }
    toolkit_path = tmp_path / "toolkit.json"
    toolkit_path.write_text(json.dumps(toolkit, indent=2))
    return toolkit_path


@pytest.fixture()
def patch_toolkit(monkeypatch, minimal_toolkit, tmp_path):
    """Point ToolkitRegistry at the temp toolkit.json and redirect memory writes to tmp_path."""
    import aigis_agents.mesh.toolkit_registry as tr
    import aigis_agents.mesh.memory_manager as mm
    monkeypatch.setattr(tr, "_TOOLKIT_PATH", minimal_toolkit)
    monkeypatch.setattr(mm, "_AGENTS_ROOT", tmp_path)
    tr._load_raw.cache_clear()
    yield
    tr._load_raw.cache_clear()


# ── Database fixtures ─────────────────────────────────────────────────────────


@pytest.fixture()
def sqlite_conn(tmp_path, deal_id) -> sqlite3.Connection:
    """Create a fresh Agent02 SQLite DB and return an open connection."""
    from aigis_agents.agent_02_data_store import db_manager as db
    db.ensure_db(deal_id, str(tmp_path))
    conn = db.get_connection(deal_id, str(tmp_path))
    db.upsert_deal(conn, deal_id,
                   deal_name="Test Deal",
                   deal_type="producing_asset",
                   jurisdiction="GoM")
    yield conn
    conn.close()


# ── File fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_excel_file(tmp_path) -> Path:
    """Create a minimal production-data Excel file for ingestion tests."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Production"
    headers = ["Month", "Oil (bopd)", "Gas (Mcfd)", "Water (bwpd)"]
    ws.append(headers)
    monthly_data = [
        ("2024-01-01", 1200, 3600, 800),
        ("2024-02-01", 1180, 3540, 820),
        ("2024-03-01", 1160, 3480, 840),
        ("2024-04-01", 1140, 3420, 860),
    ]
    for row in monthly_data:
        ws.append(list(row))
    path = tmp_path / "production_history.xlsx"
    wb.save(path)
    return path


@pytest.fixture()
def sample_csv_file(tmp_path) -> Path:
    """Create a minimal production CSV file."""
    content = "period_start,product,value,unit\n"
    content += "2024-01-01,oil,1200,bopd\n"
    content += "2024-02-01,oil,1180,bopd\n"
    content += "2024-03-01,oil,1160,bopd\n"
    path = tmp_path / "production_data.csv"
    path.write_text(content, encoding="utf-8")
    return path
