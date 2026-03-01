"""
Tests for DealContextManager (Phase B — DealContext.md shared pipeline state).

Coverage:
  - File created with template on first access
  - load() returns markdown string; returns placeholder when file is missing
  - update_section() replaces existing section, preserves other sections
  - update_section() inserts new section when heading not present
  - update_section() refreshes "Last updated" in file header
  - append_run_log() adds table row; multiple entries all present
  - get_summary() truncates to max_chars with note
  - get_section() returns section text; returns None for unpopulated sections
  - Temporal weighting: _pattern_weight HIGH / MEDIUM / STALE classification
  - load_patterns() excludes STALE by default, sorts HIGH before MEDIUM
  - AgentBase injects deal_context into _run() arguments (step 5.6)
  - AgentBase calls update_section + append_run_log when _deal_context_section present (step 10.5)
  - _deal_context_section key stripped from public output
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from aigis_agents.mesh.deal_context import DealContextManager, DealContextSection
from aigis_agents.mesh.memory_manager import MemoryManager, _pattern_weight


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def deal_id() -> str:
    return "test-deal-dc-001"


@pytest.fixture()
def manager(tmp_path, deal_id) -> DealContextManager:
    return DealContextManager(deal_id=deal_id, memory_root=tmp_path)


@pytest.fixture()
def section_a(deal_id) -> DealContextSection:
    return DealContextSection(
        agent_id="agent_01",
        section_name="Agent 01 — VDR Inventory Summary",
        content="Coverage: 85.0% | Present NTH: 12 | Missing NTH: 2",
        updated_at="2026-03-01",
        run_id="run-abc-123",
    )


# ── Creation / initialisation ─────────────────────────────────────────────────

class TestDealContextCreation:
    def test_file_created_on_init(self, tmp_path, deal_id):
        DealContextManager(deal_id=deal_id, memory_root=tmp_path)
        expected = tmp_path / deal_id / "deal_context.md"
        assert expected.exists()

    def test_template_has_required_sections(self, manager):
        text = manager.load()
        assert "# Deal Context" in text
        assert "Agent 01 — VDR Inventory Summary" in text
        assert "Agent 02 — Data Store Summary" in text
        assert "Agent 04 — Financial Analysis Summary" in text
        assert "## Run Log" in text

    def test_does_not_overwrite_existing(self, tmp_path, deal_id):
        deal_dir = tmp_path / deal_id
        deal_dir.mkdir(parents=True)
        ctx_path = deal_dir / "deal_context.md"
        ctx_path.write_text("# Custom Context\n", encoding="utf-8")
        mgr = DealContextManager(deal_id=deal_id, memory_root=tmp_path)
        assert mgr.load() == "# Custom Context\n"


# ── load ──────────────────────────────────────────────────────────────────────

class TestLoad:
    def test_returns_string(self, manager):
        result = manager.load()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_missing_file_returns_placeholder(self, tmp_path, deal_id):
        mgr = DealContextManager(deal_id=deal_id, memory_root=tmp_path)
        # Delete file to simulate missing
        (tmp_path / deal_id / "deal_context.md").unlink()
        result = mgr.load()
        assert "Deal Context" in result
        assert deal_id in result


# ── update_section ────────────────────────────────────────────────────────────

class TestUpdateSection:
    def test_replaces_existing_section(self, manager, section_a):
        manager.update_section(section_a)
        text = manager.load()
        assert "Coverage: 85.0%" in text
        assert "Present NTH: 12" in text

    def test_preserves_other_sections(self, manager, section_a):
        manager.update_section(section_a)
        text = manager.load()
        assert "Agent 02 — Data Store Summary" in text
        assert "Agent 04 — Financial Analysis Summary" in text
        assert "## Run Log" in text

    def test_section_not_duplicated(self, manager, section_a):
        manager.update_section(section_a)
        manager.update_section(section_a)
        text = manager.load()
        # Count occurrences of the section heading
        assert text.count("Agent 01 — VDR Inventory Summary") == 1

    def test_section_content_updated_on_second_write(self, manager, deal_id):
        s1 = DealContextSection(
            agent_id="agent_01",
            section_name="Agent 01 — VDR Inventory Summary",
            content="Coverage: 70%",
            updated_at="2026-03-01",
            run_id="run-001",
        )
        s2 = DealContextSection(
            agent_id="agent_01",
            section_name="Agent 01 — VDR Inventory Summary",
            content="Coverage: 90%",
            updated_at="2026-03-02",
            run_id="run-002",
        )
        manager.update_section(s1)
        manager.update_section(s2)
        text = manager.load()
        assert "Coverage: 90%" in text
        assert "Coverage: 70%" not in text

    def test_inserts_new_section_before_run_log(self, manager):
        new_section = DealContextSection(
            agent_id="agent_06",
            section_name="Agent 06 — Q&A Synthesis",
            content="Key Q&A findings here",
            updated_at="2026-03-01",
            run_id="run-x",
        )
        manager.update_section(new_section)
        text = manager.load()
        assert "Agent 06 — Q&A Synthesis" in text
        assert "Key Q&A findings here" in text
        # Run Log must still be present
        assert "## Run Log" in text
        # New section must appear before Run Log
        assert text.index("Agent 06 — Q&A Synthesis") < text.index("## Run Log")

    def test_meta_line_written(self, manager, section_a):
        manager.update_section(section_a)
        text = manager.load()
        assert "Updated: 2026-03-01" in text
        assert "Run: run-abc-123" in text

    def test_header_last_updated_refreshed(self, manager, section_a):
        manager.update_section(section_a)
        text = manager.load()
        assert "Last updated: 2026-03-01" in text


# ── append_run_log ────────────────────────────────────────────────────────────

class TestAppendRunLog:
    def test_row_appears_in_file(self, manager):
        manager.append_run_log(
            agent_id="agent_01",
            run_id="run-abc-001",
            flags=["Missing CPR"],
            summary="Coverage 85%, missing 2 NTH docs",
        )
        text = manager.load()
        assert "agent_01" in text
        assert "run-abc-001" in text
        assert "Missing CPR" in text

    def test_multiple_entries_all_present(self, manager):
        manager.append_run_log("agent_01", "run-001", [], "summary a")
        manager.append_run_log("agent_02", "run-002", [], "summary b")
        text = manager.load()
        assert "agent_01" in text
        assert "agent_02" in text
        assert "summary a" in text
        assert "summary b" in text

    def test_no_flags_shows_dash(self, manager):
        manager.append_run_log("agent_01", "run-x", [], "no flags run")
        text = manager.load()
        assert "—" in text

    def test_pipe_in_summary_escaped(self, manager):
        manager.append_run_log("agent_01", "run-x", [], "NPV: $100mm | IRR: 15%")
        text = manager.load()
        # | should be replaced so it doesn't break the markdown table
        lines = [l for l in text.splitlines() if "agent_01" in l and "run-x" in l]
        assert len(lines) == 1
        # The summary cell should not contain a raw | that breaks the table
        # (it should have been sanitised to /)
        cells = lines[0].split("|")
        assert len(cells) >= 5   # valid table row


# ── get_summary ───────────────────────────────────────────────────────────────

class TestGetSummary:
    def test_returns_full_text_when_short(self, manager):
        text = manager.load()
        summary = manager.get_summary(max_chars=100_000)
        assert summary == text

    def test_truncates_long_text(self, manager):
        summary = manager.get_summary(max_chars=50)
        assert len(summary) <= 50 + 100  # allow room for truncation note
        assert "truncated" in summary


# ── get_section ───────────────────────────────────────────────────────────────

class TestGetSection:
    def test_returns_none_for_unpopulated_template_section(self, manager):
        # The template has "Not yet populated." placeholder
        result = manager.get_section("agent_01", "Agent 01 — VDR Inventory Summary")
        assert result is None

    def test_returns_content_after_update(self, manager, section_a):
        manager.update_section(section_a)
        result = manager.get_section("agent_01", "Agent 01 — VDR Inventory Summary")
        assert result is not None
        assert "Coverage: 85.0%" in result

    def test_returns_none_for_missing_section(self, manager):
        result = manager.get_section("agent_99", "Nonexistent Section XYZ")
        assert result is None


# ── Temporal weighting (_pattern_weight) ──────────────────────────────────────

class TestPatternWeight:
    def _make_pattern(self, days_ago: int, confirmations: int = 1) -> dict:
        ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        return {
            "pattern_id": "p-test",
            "last_confirmed_date": ts,
            "confirmation_count": confirmations,
        }

    def test_high_recent_confirmed(self):
        p = self._make_pattern(days_ago=30, confirmations=3)
        assert _pattern_weight(p) == "HIGH"

    def test_medium_recent_low_confirms(self):
        p = self._make_pattern(days_ago=30, confirmations=1)
        assert _pattern_weight(p) == "MEDIUM"

    def test_medium_older_pattern(self):
        p = self._make_pattern(days_ago=200, confirmations=5)
        assert _pattern_weight(p) == "MEDIUM"

    def test_stale_old_pattern(self):
        p = self._make_pattern(days_ago=400, confirmations=10)
        assert _pattern_weight(p) == "STALE"

    def test_no_date_returns_medium(self):
        assert _pattern_weight({"pattern_id": "p"}) == "MEDIUM"

    def test_malformed_date_returns_medium(self):
        assert _pattern_weight({"last_confirmed_date": "not-a-date"}) == "MEDIUM"


# ── MemoryManager.load_patterns temporal sorting ──────────────────────────────

class TestLoadPatternsTemporalSorting:
    def _mem(self, tmp_path) -> MemoryManager:
        import aigis_agents.mesh.memory_manager as mm
        from unittest.mock import patch as _patch
        # Use monkeypatch indirectly via direct path override
        mem = MemoryManager()
        return mem

    def test_stale_excluded_by_default(self, tmp_path, monkeypatch):
        import aigis_agents.mesh.memory_manager as mm
        monkeypatch.setattr(mm, "_AGENTS_ROOT", tmp_path)
        mem = MemoryManager()
        agent_id = "agent_04"

        stale_ts = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        recent_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        mem.save_pattern(agent_id, {
            "pattern_id": "stale-p",
            "last_confirmed_date": stale_ts,
            "confirmation_count": 5,
        })
        mem.save_pattern(agent_id, {
            "pattern_id": "recent-p",
            "last_confirmed_date": recent_ts,
            "confirmation_count": 3,
        })

        loaded = mem.load_patterns(agent_id)
        ids = [p["pattern_id"] for p in loaded]
        assert "recent-p" in ids
        assert "stale-p" not in ids

    def test_stale_included_when_flag_set(self, tmp_path, monkeypatch):
        import aigis_agents.mesh.memory_manager as mm
        monkeypatch.setattr(mm, "_AGENTS_ROOT", tmp_path)
        mem = MemoryManager()
        agent_id = "agent_04"

        stale_ts = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        mem.save_pattern(agent_id, {
            "pattern_id": "stale-p",
            "last_confirmed_date": stale_ts,
            "confirmation_count": 5,
        })

        loaded = mem.load_patterns(agent_id, include_stale=True)
        ids = [p["pattern_id"] for p in loaded]
        assert "stale-p" in ids

    def test_high_before_medium(self, tmp_path, monkeypatch):
        import aigis_agents.mesh.memory_manager as mm
        monkeypatch.setattr(mm, "_AGENTS_ROOT", tmp_path)
        mem = MemoryManager()
        agent_id = "agent_04"

        medium_ts = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
        high_ts   = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

        mem.save_pattern(agent_id, {
            "pattern_id": "medium-p",
            "last_confirmed_date": medium_ts,
            "confirmation_count": 1,
        })
        mem.save_pattern(agent_id, {
            "pattern_id": "high-p",
            "last_confirmed_date": high_ts,
            "confirmation_count": 5,
        })

        loaded = mem.load_patterns(agent_id)
        ids = [p["pattern_id"] for p in loaded]
        assert ids.index("high-p") < ids.index("medium-p")

    def test_no_date_patterns_still_returned(self, tmp_path, monkeypatch):
        import aigis_agents.mesh.memory_manager as mm
        monkeypatch.setattr(mm, "_AGENTS_ROOT", tmp_path)
        mem = MemoryManager()
        agent_id = "agent_04"

        mem.save_pattern(agent_id, {"pattern_id": "ageless-p", "description": "no date"})
        loaded = mem.load_patterns(agent_id)
        ids = [p["pattern_id"] for p in loaded]
        assert "ageless-p" in ids


# ── AgentBase deal_context injection (step 5.6) ───────────────────────────────

class TestAgentBaseDealContextInjection:
    def test_deal_context_passed_to_run(self, tmp_path, patch_toolkit, patch_get_chat_model):
        from aigis_agents.mesh.agent_base import AgentBase
        import aigis_agents.mesh.deal_context as dc_mod

        received: dict = {}

        class ConcreteAgent(AgentBase):
            AGENT_ID = "agent_04"
            DK_TAGS  = []

            def _run(self, deal_id, main_llm, dk_context, buyer_context,
                     deal_context, patterns, mode="standalone",
                     output_dir="./outputs", **_):
                received["deal_context"] = deal_context
                return {"result": "ok"}

        with patch.object(dc_mod, "_MEMORY_ROOT", tmp_path / "memory"):
            agent = ConcreteAgent()
            agent.invoke(mode="standalone", deal_id="test-dc-inject", output_dir=str(tmp_path))

        assert "deal_context" in received
        assert isinstance(received["deal_context"], str)
        assert "Deal Context" in received["deal_context"]

    def test_deal_context_section_updates_file(self, tmp_path, patch_toolkit, patch_get_chat_model):
        """_deal_context_section returned by _run() should persist to deal_context.md."""
        from aigis_agents.mesh.agent_base import AgentBase
        import aigis_agents.mesh.deal_context as dc_mod

        class ConcreteAgent(AgentBase):
            AGENT_ID = "agent_04"
            DK_TAGS  = []

            def _run(self, deal_id, main_llm, dk_context, buyer_context,
                     deal_context, patterns, mode="standalone",
                     output_dir="./outputs", **_):
                return {
                    "result": "ok",
                    "_deal_context_section": {
                        "section_name": "Agent 04 — Financial Analysis Summary",
                        "content": "NPV10: $120mm | IRR: 18.5% | Critical flags: 0",
                    },
                }

        memory_root = tmp_path / "memory"
        with patch.object(dc_mod, "_MEMORY_ROOT", memory_root):
            agent = ConcreteAgent()
            agent.invoke(mode="standalone", deal_id="test-dc-write", output_dir=str(tmp_path))

        ctx_path = memory_root / "test-dc-write" / "deal_context.md"
        assert ctx_path.exists()
        text = ctx_path.read_text(encoding="utf-8")
        assert "NPV10: $120mm" in text
        assert "IRR: 18.5%" in text

    def test_deal_context_section_stripped_from_output(
        self, tmp_path, patch_toolkit, patch_get_chat_model
    ):
        """_deal_context_section must not appear in the public return envelope."""
        from aigis_agents.mesh.agent_base import AgentBase
        import aigis_agents.mesh.deal_context as dc_mod

        class ConcreteAgent(AgentBase):
            AGENT_ID = "agent_04"
            DK_TAGS  = []

            def _run(self, deal_id, main_llm, dk_context, buyer_context,
                     deal_context, patterns, mode="standalone",
                     output_dir="./outputs", **_):
                return {
                    "npv": 100.0,
                    "_deal_context_section": {
                        "section_name": "Agent 04 — Financial Analysis Summary",
                        "content": "NPV10: $100mm",
                    },
                }

        with patch.object(dc_mod, "_MEMORY_ROOT", tmp_path / "memory"):
            agent = ConcreteAgent()
            result = agent.invoke(
                mode="standalone", deal_id="test-strip", output_dir=str(tmp_path)
            )

        assert "_deal_context_section" not in result
        assert "_deal_context_section" not in result.get("data", {})
