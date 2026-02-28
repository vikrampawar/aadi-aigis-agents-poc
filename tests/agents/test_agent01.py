"""Tests for Agent 01 — VDR Inventory & Gap Analyst (MESH v2.0)."""
import pytest
from pathlib import Path
from aigis_agents.agent_01_vdr_inventory.agent import Agent01


@pytest.fixture()
def vdr_dir(tmp_path):
    """Create a minimal fake VDR folder structure."""
    vdr = tmp_path / "VDR"
    cats = {
        "01_Corporate": ["Corporate_Overview.pdf", "Share_Register.pdf"],
        "02_Legal": ["SPA_Draft_v1.pdf", "JOA_GoM_Block71.pdf"],
        "03_Financial": ["Financial_Model_v3.xlsx", "Audited_Accounts_2023.pdf"],
        "04_Technical": ["CPR_RPS_2024.pdf", "Production_History_2020_2024.xlsx"],
        "05_Operations": ["LOS_October_2024.xlsx", "Monthly_Report_Sep2024.pdf"],
    }
    for folder, files in cats.items():
        (vdr / folder).mkdir(parents=True)
        for fname in files:
            (vdr / folder / fname).write_text(f"Content of {fname}")
    return vdr


@pytest.mark.unit
class TestAgent01Init:

    def test_agent_id_correct(self):
        assert Agent01.AGENT_ID == "agent_01"

    def test_dk_tags_present(self):
        assert isinstance(Agent01.DK_TAGS, list)
        assert len(Agent01.DK_TAGS) > 0

    def test_agent_is_agentbase_subclass(self):
        from aigis_agents.mesh.agent_base import AgentBase
        assert issubclass(Agent01, AgentBase)


@pytest.mark.unit
class TestAgent01ToolCallMode:

    def test_invoke_tool_call_returns_success(
        self, patch_toolkit, patch_get_chat_model, vdr_dir, tmp_path, deal_id
    ):
        result = Agent01().invoke(
            mode="tool_call",
            deal_id=deal_id,
            vdr_path=str(vdr_dir),
            deal_type="producing_asset",
            jurisdiction="GoM",
            output_dir=str(tmp_path),
        )
        assert result["status"] == "success"
        assert result["agent"] == "agent_01"

    def test_invoke_tool_call_no_file_writes(
        self, patch_toolkit, patch_get_chat_model, vdr_dir, tmp_path, deal_id
    ):
        Agent01().invoke(
            mode="tool_call",
            deal_id=deal_id,
            vdr_path=str(vdr_dir),
            deal_type="producing_asset",
            jurisdiction="GoM",
            output_dir=str(tmp_path),
        )
        # In tool_call mode, no report files should be written
        output_dir = tmp_path / deal_id
        md_files = list(output_dir.glob("01_gap_analysis_report.md")) if output_dir.exists() else []
        assert len(md_files) == 0

    def test_invoke_result_has_data_key(
        self, patch_toolkit, patch_get_chat_model, vdr_dir, tmp_path, deal_id
    ):
        result = Agent01().invoke(
            mode="tool_call", deal_id=deal_id, vdr_path=str(vdr_dir),
            deal_type="producing_asset", jurisdiction="GoM", output_dir=str(tmp_path),
        )
        assert "data" in result


@pytest.mark.unit
class TestAgent01StandaloneMode:

    def test_invoke_standalone_runs_without_error(
        self, patch_toolkit, patch_get_chat_model, vdr_dir, tmp_path, deal_id
    ):
        result = Agent01().invoke(
            mode="standalone",
            deal_id=deal_id,
            vdr_path=str(vdr_dir),
            deal_type="producing_asset",
            jurisdiction="GoM",
            output_dir=str(tmp_path),
        )
        # Should not raise; status may vary
        assert result.get("status") in ("success", "error")


@pytest.mark.unit
class TestAgent01MissingVDRPath:

    def test_missing_vdr_path_returns_gracefully(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent01().invoke(
            mode="tool_call",
            deal_id=deal_id,
            vdr_path=None,
            output_dir=str(tmp_path),
        )
        # Either status=error or empty data; should not raise an exception
        assert result.get("status") in ("success", "error")

    def test_nonexistent_vdr_path_graceful(
        self, patch_toolkit, patch_get_chat_model, tmp_path, deal_id
    ):
        result = Agent01().invoke(
            mode="tool_call",
            deal_id=deal_id,
            vdr_path=str(tmp_path / "does_not_exist"),
            deal_type="producing_asset",
            jurisdiction="GoM",
            output_dir=str(tmp_path),
        )
        assert result.get("status") in ("success", "error")


@pytest.mark.unit
class TestAgent01AuditBlock:

    def test_result_includes_audit_block(
        self, patch_toolkit, patch_get_chat_model, vdr_dir, tmp_path, deal_id
    ):
        result = Agent01().invoke(
            mode="tool_call", deal_id=deal_id, vdr_path=str(vdr_dir),
            deal_type="producing_asset", jurisdiction="GoM", output_dir=str(tmp_path),
        )
        assert "audit" in result
        assert "output_confidence" in result["audit"]
        assert result["audit"]["output_confidence"] in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
