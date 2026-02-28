"""Tests for Agent02 query mode — direct SQL and natural language queries."""
import sqlite3
import uuid
import pytest
from aigis_agents.agent_02_data_store.agent import Agent02
from aigis_agents.agent_02_data_store import db_manager as db


@pytest.fixture()
def db_with_data(tmp_path, deal_id, mock_llm):
    """Pre-seeded DB with scalar_datapoints rows."""
    db.ensure_db(deal_id, str(tmp_path))
    conn = db.get_connection(deal_id, str(tmp_path))
    db.upsert_deal(conn, deal_id, deal_name="TestDeal",
                   deal_type="producing_asset", jurisdiction="GoM")

    doc_id = str(uuid.uuid4())
    db.insert_source_document(conn, {
        "doc_id": doc_id, "deal_id": deal_id, "filename": "production.csv",
        "folder_path": "/vdr", "file_type": "csv", "doc_category": "Production",
        "doc_label": "production", "ingest_timestamp": "2026-02-28T10:00:00Z",
        "ingest_run_id": doc_id, "case_name": "management_case", "status": "complete",
    })

    # Insert scalar datapoints
    for metric, value, unit in [
        ("npv_10_usd", 45_000_000, "USD"),
        ("irr_pct", 28.5, "%"),
        ("2p_reserves_mmboe", 12.4, "MMboe"),
    ]:
        conn.execute(
            "INSERT INTO scalar_datapoints "
            "(id, deal_id, doc_id, case_name, category, metric_name, metric_key, value, unit, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), deal_id, doc_id, "management_case",
             "financial", metric, metric, value, unit, "HIGH")
        )
    conn.commit()
    conn.close()
    return tmp_path


@pytest.mark.unit
class TestQueryDirectSQL:

    def test_direct_sql_query_returns_rows(
        self, patch_toolkit, patch_get_chat_model, db_with_data, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            query_sql=f"SELECT metric_name, value, unit FROM scalar_datapoints WHERE deal_id = '{deal_id}'",
            output_dir=str(db_with_data),
        )
        data = result.get("data", {})
        rows = data.get("data", [])
        assert len(rows) >= 3

    def test_direct_sql_returns_npv(
        self, patch_toolkit, patch_get_chat_model, db_with_data, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            query_sql=(
                f"SELECT metric_key, value FROM scalar_datapoints "
                f"WHERE deal_id = '{deal_id}' AND metric_key = 'npv_10_usd'"
            ),
            output_dir=str(db_with_data),
        )
        data = result.get("data", {})
        rows = data.get("data", [])
        assert len(rows) == 1
        assert rows[0].get("metric_key") == "npv_10_usd"
        assert rows[0].get("value") == 45_000_000


@pytest.mark.unit
class TestQuerySQLSecurity:

    def test_drop_table_blocked(
        self, patch_toolkit, patch_get_chat_model, db_with_data, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            query_sql="DROP TABLE scalar_datapoints",
            output_dir=str(db_with_data),
        )
        data = result.get("data", {})
        assert "error" in str(data).lower() or result.get("status") == "error"

    def test_delete_blocked(
        self, patch_toolkit, patch_get_chat_model, db_with_data, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            query_sql=f"DELETE FROM scalar_datapoints WHERE deal_id = '{deal_id}'",
            output_dir=str(db_with_data),
        )
        data = result.get("data", {})
        assert "error" in str(data).lower() or result.get("status") == "error"


@pytest.mark.unit
class TestQueryNaturalLanguage:

    def test_nl_query_invokes_llm(
        self, patch_toolkit, patch_get_chat_model, db_with_data, deal_id, mock_llm
    ):
        # The mock LLM will get the NL query text; return valid SQL
        mock_llm._responses["What is"] = (
            f"SELECT metric_name, value FROM scalar_datapoints "
            f"WHERE deal_id = '{deal_id}'"
        )
        Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            query_text="What is the NPV10?",
            output_dir=str(db_with_data),
        )
        assert mock_llm.call_count >= 1


@pytest.mark.unit
class TestQueryResultMetadata:

    def test_result_includes_data_key(
        self, patch_toolkit, patch_get_chat_model, db_with_data, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            query_sql=f"SELECT * FROM scalar_datapoints WHERE deal_id = '{deal_id}'",
            output_dir=str(db_with_data),
        )
        data = result.get("data", {})
        assert "data" in data or "cases_present" in data

    def test_empty_query_returns_without_crashing(
        self, patch_toolkit, patch_get_chat_model, db_with_data, deal_id
    ):
        """With neither query_text nor query_sql, should return gracefully."""
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            output_dir=str(db_with_data),
        )
        assert result.get("status") in ("success", "error")
