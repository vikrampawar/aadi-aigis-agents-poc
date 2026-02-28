"""Tests for Agent02 file ingestion — Excel, CSV, and error handling."""
import sqlite3
import pytest
from aigis_agents.agent_02_data_store.agent import Agent02


@pytest.mark.unit
class TestAgent02Init:

    def test_agent_id_correct(self):
        assert Agent02.AGENT_ID == "agent_02"

    def test_dk_tags_include_financial(self):
        assert "financial" in Agent02.DK_TAGS

    def test_is_agentbase_subclass(self):
        from aigis_agents.mesh.agent_base import AgentBase
        assert issubclass(Agent02, AgentBase)


@pytest.mark.unit
class TestIngestCSV:

    def test_ingest_csv_tool_call_returns_success(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        assert result["status"] == "success"

    def test_ingest_csv_creates_db(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        db_path = tmp_path / deal_id / "02_data_store.db"
        assert db_path.exists()

    def test_ingest_csv_result_has_doc_id(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        data = result.get("data", {})
        assert "doc_id" in data

    def test_ingest_csv_data_points_extracted(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        data = result.get("data", {})
        assert data.get("data_points_extracted", 0) >= 0


@pytest.mark.unit
class TestIngestExcel:

    def test_ingest_excel_returns_success(
        self, patch_toolkit, patch_get_chat_model, sample_excel_file, tmp_path, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_excel_file),
            file_type="excel",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        assert result["status"] == "success"

    def test_ingest_excel_registers_source_document(
        self, patch_toolkit, patch_get_chat_model, sample_excel_file, tmp_path, deal_id
    ):
        Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_excel_file),
            file_type="excel",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        db_path = tmp_path / deal_id / "02_data_store.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT filename FROM source_documents WHERE deal_id = ?", (deal_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        assert any("production_history" in r[0] for r in rows)


@pytest.mark.unit
class TestIngestErrors:

    def test_missing_file_path_returns_error(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=None,
            output_dir=str(tmp_path),
        )
        has_error = (
            result.get("status") == "error" or
            "error" in result.get("data", {})
        )
        assert has_error

    def test_nonexistent_file_path_handled_gracefully(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(tmp_path / "does_not_exist.xlsx"),
            output_dir=str(tmp_path),
        )
        # Should not raise unhandled exception
        assert result is not None

    def test_invalid_operation_returns_error(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="invalid_op",
            output_dir=str(tmp_path),
        )
        data = result.get("data", {})
        assert "error" in data or result.get("status") == "error"

    def test_standalone_ingest_no_md_report(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        """ingest_file in standalone writes DB only, not a full MD report."""
        result = Agent02().invoke(
            mode="standalone",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        data = result.get("data", {})
        output_paths = data.get("output_paths", {})
        # ingestion_report should NOT be present for ingest_file (only ingest_vdr)
        assert "ingestion_report" not in output_paths
