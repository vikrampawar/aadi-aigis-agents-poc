"""Integration tests — cross-agent calls and full pipeline flows."""
import json
import pytest
from aigis_agents.agent_02_data_store.agent import Agent02


@pytest.mark.integration
class TestAgent02CallsAgent04:

    def test_scenario_query_does_not_crash(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        """Agent02 query with scenario dict should run without exception."""
        Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            query_text="What is the NPV at $65 oil?",
            scenario={"oil_price_usd_bbl": 65.0, "loe_per_boe": 18.0},
            output_dir=str(tmp_path),
        )
        assert result.get("status") in ("success", "error")


@pytest.mark.integration
class TestFullIngestQueryPipeline:

    def test_ingest_then_query_returns_data(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        # Step 1: Ingest
        ingest_result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        assert ingest_result["status"] == "success"
        doc_id = ingest_result.get("data", {}).get("doc_id")
        assert doc_id is not None

        # Step 2: Query
        query_result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            query_sql=(
                f"SELECT filename FROM source_documents WHERE deal_id = '{deal_id}'"
            ),
            output_dir=str(tmp_path),
        )
        data = query_result.get("data", {})
        rows = data.get("data", [])
        assert len(rows) >= 1

    def test_ingest_excel_then_query_cells(
        self, patch_toolkit, patch_get_chat_model, sample_excel_file, tmp_path, deal_id
    ):
        Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_excel_file),
            file_type="excel",
            case_name="cpr_base_case",
            output_dir=str(tmp_path),
        )
        result = Agent02().invoke(
            mode="tool_call",
            deal_id=deal_id,
            operation="query",
            query_sql=f"SELECT COUNT(*) as c FROM excel_cells WHERE deal_id = '{deal_id}'",
            output_dir=str(tmp_path),
        )
        assert result.get("status") == "success"


@pytest.mark.integration
class TestAuditLogIntegrity:

    def test_audit_log_created_after_invoke(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        Agent02().invoke(
            mode="standalone",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        audit_log = tmp_path / deal_id / "_audit_log.jsonl"
        assert audit_log.exists()

    def test_audit_log_is_valid_jsonl(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        Agent02().invoke(
            mode="standalone",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        audit_log = tmp_path / deal_id / "_audit_log.jsonl"
        for line in audit_log.read_text().strip().split("\n"):
            if line.strip():
                record = json.loads(line)
                assert "run_id" in record
                assert "agent" in record
                assert "timestamp" in record

    def test_audit_log_accumulates_across_invocations(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        for _ in range(3):
            Agent02().invoke(
                mode="standalone",
                deal_id=deal_id,
                operation="ingest_file",
                file_path=str(sample_csv_file),
                file_type="csv",
                case_name="management_case",
                output_dir=str(tmp_path),
            )
        audit_log = tmp_path / deal_id / "_audit_log.jsonl"
        lines = [ln for ln in audit_log.read_text().strip().split("\n") if ln.strip()]
        assert len(lines) >= 3


@pytest.mark.integration
class TestCallAgentDirect:

    def test_call_agent_resolves_and_invokes(
        self, patch_toolkit, patch_get_chat_model, sample_csv_file, tmp_path, deal_id
    ):
        """AgentBase.call_agent() must resolve the class and invoke in tool_call mode."""
        agent02 = Agent02()
        result = agent02.call_agent(
            "agent_02",
            deal_id=deal_id,
            operation="ingest_file",
            file_path=str(sample_csv_file),
            file_type="csv",
            case_name="management_case",
            output_dir=str(tmp_path),
        )
        assert result.get("status") == "success"
        assert result.get("run_metadata", {}).get("mode") == "tool_call"
