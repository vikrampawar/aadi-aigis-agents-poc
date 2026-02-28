"""Tests for consistency checker — cross-source conflict detection."""
import uuid
import pytest
from aigis_agents.agent_02_data_store import db_manager as db
from aigis_agents.agent_02_data_store import consistency_checker


@pytest.fixture()
def conn_with_conflict(sqlite_conn, deal_id):
    """Insert two conflicting reserve_estimates rows from different docs.

    Uses reserve_estimates (no UNIQUE constraint beyond PK) so both rows
    coexist and the consistency checker can compare them.
    30% discrepancy: 1000 vs 1300 → CRITICAL.
    """
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())

    for doc_id, value in [(doc_a, 1000.0), (doc_b, 1300.0)]:
        db.insert_source_document(sqlite_conn, {
            "doc_id": doc_id, "deal_id": deal_id, "filename": f"doc_{doc_id[:4]}.pdf",
            "folder_path": "/vdr", "file_type": "pdf", "doc_category": "Reserves/CPR",
            "doc_label": "CPR", "ingest_timestamp": "2026-02-28T10:00:00Z",
            "ingest_run_id": doc_id, "case_name": "management_case", "status": "complete",
        })
        sqlite_conn.execute(
            "INSERT INTO reserve_estimates "
            "(id, deal_id, doc_id, case_name, entity_name, reserve_class, product, "
            " value, unit, confidence) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), deal_id, doc_id, "management_case", "Field A",
             "2P", "oil", value, "MMboe", "HIGH"),
        )
    sqlite_conn.commit()
    return sqlite_conn, doc_a, doc_b


@pytest.mark.unit
class TestConsistencyChecker:

    def test_run_returns_severity_dict(self, sqlite_conn, deal_id):
        result = consistency_checker.run_consistency_check(sqlite_conn, deal_id, [])
        assert isinstance(result, dict)
        for key in ("critical", "warning", "info", "total"):
            assert key in result

    def test_no_conflicts_when_single_source(self, sqlite_conn, deal_id):
        result = consistency_checker.run_consistency_check(sqlite_conn, deal_id, [])
        assert result["total"] == 0

    def test_detects_critical_conflict(self, conn_with_conflict, deal_id):
        sqlite_conn, doc_a, doc_b = conn_with_conflict
        result = consistency_checker.run_consistency_check(
            sqlite_conn, deal_id, [doc_a, doc_b]
        )
        assert result["critical"] >= 1, "30% discrepancy should be CRITICAL"
        assert result["total"] >= 1

    def test_critical_conflict_written_to_data_conflicts(self, conn_with_conflict, deal_id):
        sqlite_conn, doc_a, doc_b = conn_with_conflict
        consistency_checker.run_consistency_check(sqlite_conn, deal_id, [doc_a, doc_b])
        cursor = sqlite_conn.execute(
            "SELECT severity FROM data_conflicts WHERE deal_id = ?", (deal_id,)
        )
        rows = cursor.fetchall()
        assert any(r[0] == "CRITICAL" for r in rows)

    def test_conflict_below_threshold_is_info(self, sqlite_conn, deal_id):
        """3% discrepancy — below WARNING threshold (5%) — should be INFO or absent."""
        doc_a, doc_b = str(uuid.uuid4()), str(uuid.uuid4())
        for doc_id, value in [(doc_a, 1000.0), (doc_b, 1030.0)]:  # 3% diff
            db.insert_source_document(sqlite_conn, {
                "doc_id": doc_id, "deal_id": deal_id, "filename": f"d{doc_id[:4]}.xlsx",
                "folder_path": "/vdr", "file_type": "excel", "doc_category": "Production",
                "doc_label": "production", "ingest_timestamp": "2026-02-28T10:00:00Z",
                "ingest_run_id": doc_id, "case_name": "cpr_base_case", "status": "complete",
            })
            sqlite_conn.execute(
                "INSERT INTO production_series "
                "(id, deal_id, doc_id, case_name, entity_name, period_type, period_start, period_end, "
                " product, value, unit, confidence) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), deal_id, doc_id, "cpr_base_case", "Field B",
                 "monthly", "2024-02-01", "2024-02-28", "oil", value, "bopd", "HIGH"),
            )
        sqlite_conn.commit()
        result = consistency_checker.run_consistency_check(sqlite_conn, deal_id, [doc_a, doc_b])
        if result["total"] > 0:
            assert result["critical"] == 0

    def test_total_equals_sum_of_severities(self, conn_with_conflict, deal_id):
        sqlite_conn, doc_a, doc_b = conn_with_conflict
        result = consistency_checker.run_consistency_check(sqlite_conn, deal_id, [doc_a, doc_b])
        assert result["total"] == result["critical"] + result["warning"] + result["info"]
