"""Tests for Agent02 database layer — schema, connections, CRUD helpers."""
import sqlite3
import uuid
import pytest
from aigis_agents.agent_02_data_store import db_manager as db


@pytest.mark.unit
class TestDBCreation:

    def test_ensure_db_creates_file(self, tmp_path, deal_id):
        db_path = db.ensure_db(deal_id, str(tmp_path))
        assert db_path.exists()
        assert db_path.suffix == ".db"

    def test_ensure_db_idempotent(self, tmp_path, deal_id):
        db.ensure_db(deal_id, str(tmp_path))
        db.ensure_db(deal_id, str(tmp_path))  # second call should not raise
        assert (tmp_path / deal_id / "02_data_store.db").exists()

    def test_get_connection_returns_sqlite_conn(self, tmp_path, deal_id):
        db.ensure_db(deal_id, str(tmp_path))
        conn = db.get_connection(deal_id, str(tmp_path))
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_all_required_tables_created(self, sqlite_conn):
        """All 13 core tables must exist after schema creation."""
        expected_tables = [
            "deals", "source_documents", "cases",
            "production_series", "reserve_estimates",
            "financial_series", "cost_benchmarks", "fiscal_terms",
            "scalar_datapoints", "excel_cells", "excel_sheets",
            "data_conflicts", "ingestion_log",
        ]
        cursor = sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        existing = {row[0] for row in cursor.fetchall()}
        for table in expected_tables:
            assert table in existing, f"Table '{table}' missing from schema"


@pytest.mark.unit
class TestDealUpsert:

    def test_upsert_deal_creates_row(self, sqlite_conn, deal_id):
        cursor = sqlite_conn.execute(
            "SELECT deal_id, deal_type FROM deals WHERE deal_id = ?", (deal_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == deal_id
        assert row[1] == "producing_asset"

    def test_upsert_deal_updates_existing(self, sqlite_conn, deal_id):
        db.upsert_deal(sqlite_conn, deal_id,
                       deal_name="Updated Name",
                       deal_type="exploration",
                       jurisdiction="UKCS")
        cursor = sqlite_conn.execute(
            "SELECT deal_type FROM deals WHERE deal_id = ?", (deal_id,)
        )
        row = cursor.fetchone()
        assert row[0] == "exploration"


@pytest.mark.unit
class TestSourceDocumentInsert:

    def test_insert_source_document(self, sqlite_conn, deal_id):
        doc_id = str(uuid.uuid4())
        db.insert_source_document(sqlite_conn, {
            "doc_id": doc_id,
            "deal_id": deal_id,
            "filename": "test_model.xlsx",
            "folder_path": "/vdr/financial",
            "file_type": "excel",
            "doc_category": "Financial/Financial Model",
            "doc_label": "financial_model",
            "ingest_timestamp": "2026-02-28T10:00:00Z",
            "ingest_run_id": doc_id,
            "case_name": "management_case",
            "status": "ingesting",
        })
        cursor = sqlite_conn.execute(
            "SELECT filename, file_type FROM source_documents WHERE doc_id = ?", (doc_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "test_model.xlsx"
        assert row[1] == "excel"
