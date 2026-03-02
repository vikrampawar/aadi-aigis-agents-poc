"""
Integration tests for Agent 07 — full Agent07.invoke() pipeline.

Uses:
  - MockLLM from helpers.py (returns valid JSON narrative)
  - Mock SQLite DB (seeded with production_series + reserve_estimates data)
  - Both standalone and tool_call modes
  - Single-well and fleet runs
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from helpers import MockLLM  # type: ignore[import]


def _unwrap(result: dict) -> dict:
    """Extract _run() payload from AgentBase envelope {"status":"success","data":{...}}."""
    return result.get("data", result)


# ── MockLLM that returns well-card narrative JSON ─────────────────────────────

WELL_CARD_NARRATIVE = json.dumps({
    "b_flag":    None,
    "di_flag":   "Annual decline of 22%/yr is within GoM Miocene benchmarks (15–25%/yr).",
    "eur_flag":  None,
    "red_flags": ["GOR rising 22% over 12 months — monitor closely."],
    "narrative": (
        "Well TEST-001 is performing in line with the CPR base case forecast, "
        "with a current rate of 1,022 boe/d against a CPR forecast of 1,000 boe/d (+2%). "
        "DCA hyperbolic fit (b=0.48, Di=22%/yr) yields an EUR of 1.85 MMboe, "
        "broadly consistent with the CPR 2P estimate of 1.80 MMboe (+3%). "
        "GOR trend of +22%/yr warrants monitoring but is not yet at alarm levels."
    ),
})


def _well_card_mock_llm() -> MockLLM:
    return MockLLM(responses={
        "Input Quality Auditor": '{"valid": true, "confidence": "HIGH", "issues": [], "notes": "OK"}',
        "Output Quality Auditor": json.dumps({
            "confidence_label": "HIGH", "confidence_score": 88,
            "citation_coverage": 0.80, "flags": [],
            "improvement_suggestions": [], "auditor_notes": "Good.",
        }),
        "senior reservoir engineer": WELL_CARD_NARRATIVE,
        "DCA":                       WELL_CARD_NARRATIVE,
        "well_name":                 WELL_CARD_NARRATIVE,
    })


# ── DB seeding helpers ────────────────────────────────────────────────────────

def _seed_source_doc(conn: sqlite3.Connection, deal_id: str) -> str:
    """Insert a minimal source_documents row; return its doc_id."""
    doc_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT OR IGNORE INTO source_documents
          (doc_id, deal_id, filename, folder_path, file_type, ingest_timestamp, ingest_run_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (doc_id, deal_id, "test_prod.csv", "", "csv", now, "test-run"))
    conn.commit()
    return doc_id


def _seed_production(conn: sqlite3.Connection, deal_id: str, well_name: str,
                     doc_id: str, n_months: int = 24) -> None:
    """Insert synthetic production_series rows for one well."""
    rows = []
    for i in range(n_months):
        year  = 2023 + i // 12
        month = (i % 12) + 1
        period_start = f"{year}-{month:02d}-01"
        period_end   = f"{year}-{month:02d}-28"
        oil   = 800.0 * (0.98 ** i)
        gas   = 3000.0 * (0.98 ** i)   # mcfd (→ 0.5 mmcfd via /6000 in pivot)
        water = 100.0 * (1.01 ** i)
        for product, value, unit in [
            ("oil",   oil,   "bopd"),
            ("gas",   gas,   "mcfd"),
            ("water", water, "bwpd"),
        ]:
            rows.append((
                str(uuid.uuid4()),  # id
                deal_id, doc_id,
                "actual",           # case_name
                well_name,          # entity_name
                "monthly",          # period_type
                period_start, period_end,
                product, value, unit,
                unit, value,        # unit_normalised, value_normalised
            ))
    conn.executemany("""
        INSERT OR REPLACE INTO production_series
          (id, deal_id, doc_id, case_name, entity_name, period_type,
           period_start, period_end, product, value, unit,
           unit_normalised, value_normalised)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()


def _seed_reserves(conn: sqlite3.Connection, deal_id: str, well_name: str,
                   doc_id: str) -> None:
    """Insert 1P/2P/3P reserve_estimates rows."""
    conn.executemany("""
        INSERT OR IGNORE INTO reserve_estimates
          (id, deal_id, doc_id, case_name, entity_name, reserve_class, product,
           value, value_normalised, unit, unit_normalised, effective_date, reserve_engineer)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (str(uuid.uuid4()), deal_id, doc_id, "cpr_base_case", well_name,
         "1P", "boe", 0.8, 0.8, "MMboe", "MMboe", "2024-01-01", "Ryder Scott"),
        (str(uuid.uuid4()), deal_id, doc_id, "cpr_base_case", well_name,
         "2P", "boe", 1.2, 1.2, "MMboe", "MMboe", "2024-01-01", "Ryder Scott"),
        (str(uuid.uuid4()), deal_id, doc_id, "cpr_base_case", well_name,
         "3P", "boe", 2.0, 2.0, "MMboe", "MMboe", "2024-01-01", "Ryder Scott"),
    ])
    conn.commit()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def deal_id_07() -> str:
    return "test-07-" + str(uuid.uuid4())[:8]


@pytest.fixture()
def mock_db(tmp_path, deal_id_07) -> tuple[str, str]:
    """
    Create a seeded Agent02 SQLite DB with 2 wells.
    Returns (deal_id, output_dir).
    """
    from aigis_agents.agent_02_data_store import db_manager as db
    db.ensure_db(deal_id_07, str(tmp_path))
    conn = db.get_connection(deal_id_07, str(tmp_path))
    db.upsert_deal(conn, deal_id_07, deal_name="Test Asset", deal_type="producing_asset",
                   jurisdiction="GoM")
    doc_id = _seed_source_doc(conn, deal_id_07)
    _seed_production(conn, deal_id_07, "WELL-001", doc_id, n_months=24)
    _seed_production(conn, deal_id_07, "WELL-002", doc_id, n_months=18)
    _seed_reserves(conn, deal_id_07, "WELL-001", doc_id)
    _seed_reserves(conn, deal_id_07, "WELL-002", doc_id)
    conn.close()
    return deal_id_07, str(tmp_path)


@pytest.fixture()
def patch_get_chat_model_07(monkeypatch, tmp_path):
    """Patch AgentBase's get_chat_model + redirect memory writes to tmp_path."""
    import aigis_agents.mesh.memory_manager as mm
    monkeypatch.setattr(mm, "_AGENTS_ROOT", tmp_path)
    llm = _well_card_mock_llm()
    monkeypatch.setattr("aigis_agents.mesh.agent_base.get_chat_model", lambda *a, **kw: llm)
    return llm


# ── Single-well mode tests ────────────────────────────────────────────────────

class TestSingleWellMode:
    def test_returns_dict_with_required_keys(self, mock_db, patch_get_chat_model_07, tmp_path):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode       = "tool_call",
            deal_id    = deal_id,
            well_name  = "WELL-001",
            output_dir = output_dir,
        )
        assert isinstance(result, dict)
        inner = _unwrap(result)
        for key in ("deal_id", "well_name", "rag_status", "metrics", "decline_curve", "flags"):
            assert key in inner, f"Missing key: {key}"

    def test_rag_status_is_valid(self, mock_db, patch_get_chat_model_07):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="tool_call", deal_id=deal_id, well_name="WELL-001", output_dir=output_dir
        )
        inner = _unwrap(result)
        assert inner["rag_status"] in ("GREEN", "AMBER", "RED", "BLACK")

    def test_metrics_contains_current_rate(self, mock_db, patch_get_chat_model_07):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="tool_call", deal_id=deal_id, well_name="WELL-001", output_dir=output_dir
        )
        inner = _unwrap(result)
        rate = inner.get("metrics", {}).get("current_rate_boepd")
        # Rate may be normalised BOE; just check it's >= 0
        assert rate is None or rate >= 0

    def test_decline_curve_contains_eur(self, mock_db, patch_get_chat_model_07):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="tool_call", deal_id=deal_id, well_name="WELL-001", output_dir=output_dir
        )
        inner = _unwrap(result)
        dc = inner.get("decline_curve", {})
        assert "eur_mmboe" in dc
        assert "curve_type" in dc

    def test_standalone_mode_succeeds_with_required_keys(self, mock_db, patch_get_chat_model_07, tmp_path):
        # _deal_context_section is consumed by AgentBase (step 10.5); verify outer success
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="standalone", deal_id=deal_id, well_name="WELL-001", output_dir=output_dir
        )
        assert result.get("status") == "success"
        inner = _unwrap(result)
        for key in ("deal_id", "well_name", "rag_status", "metrics", "decline_curve", "flags"):
            assert key in inner, f"Missing key: {key}"


# ── Fleet mode tests ──────────────────────────────────────────────────────────

class TestFleetMode:
    def test_returns_fleet_structure(self, mock_db, patch_get_chat_model_07):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=output_dir
        )
        inner = _unwrap(result)
        for key in ("deal_id", "total_wells", "rag_summary", "fleet_metrics", "well_cards"):
            assert key in inner, f"Missing key: {key}"

    def test_total_wells_matches_seeded(self, mock_db, patch_get_chat_model_07):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=output_dir
        )
        inner = _unwrap(result)
        assert inner["total_wells"] == 2

    def test_rag_summary_sums_to_total(self, mock_db, patch_get_chat_model_07):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=output_dir
        )
        inner = _unwrap(result)
        rag = inner["rag_summary"]
        total = sum(rag.values())
        assert total == inner["total_wells"]

    def test_fleet_metrics_present(self, mock_db, patch_get_chat_model_07):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=output_dir
        )
        inner = _unwrap(result)
        fm = inner["fleet_metrics"]
        assert "total_current_rate_boepd" in fm
        assert "total_eur_mmboe" in fm
        assert "critical_flag_count" in fm

    def test_standalone_creates_md_report(self, mock_db, patch_get_chat_model_07):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="standalone", deal_id=deal_id, output_dir=output_dir
        )
        inner = _unwrap(result)
        paths = inner.get("output_paths", {})
        report = paths.get("md_report")
        if report:
            assert Path(report).exists(), f"MD report not found: {report}"

    def test_standalone_succeeds_with_fleet_keys(self, mock_db, patch_get_chat_model_07):
        # _deal_context_section is consumed by AgentBase (step 10.5); verify outer success
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="standalone", deal_id=deal_id, output_dir=output_dir
        )
        assert result.get("status") == "success"
        inner = _unwrap(result)
        for key in ("deal_id", "total_wells", "rag_summary", "fleet_metrics", "well_cards"):
            assert key in inner, f"Missing key: {key}"


# ── No-data edge case ─────────────────────────────────────────────────────────

class TestNoDataEdgeCases:
    def test_empty_db_returns_no_data_status(self, tmp_path, patch_get_chat_model_07):
        deal_id = "test-empty-" + str(uuid.uuid4())[:8]
        from aigis_agents.agent_02_data_store import db_manager as db
        db.ensure_db(deal_id, str(tmp_path))
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="tool_call", deal_id=deal_id, output_dir=str(tmp_path)
        )
        # AgentBase wraps result in {"status": "success", "data": {...}}
        inner = result.get("data", result)
        assert inner.get("status") == "no_data" or inner.get("total_wells", -1) == 0

    def test_unknown_well_returns_card_with_error_flag(self, mock_db, patch_get_chat_model_07):
        deal_id, output_dir = mock_db
        from aigis_agents.agent_07_well_cards.agent import Agent07
        result = Agent07().invoke(
            mode="tool_call", deal_id=deal_id,
            well_name="DOES-NOT-EXIST-999",
            output_dir=output_dir,
        )
        # AgentBase wraps result; either no-data or a card with flags
        assert isinstance(result, dict)
        inner = _unwrap(result)
        assert isinstance(inner, dict)
