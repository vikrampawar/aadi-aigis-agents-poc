"""Tests for MemoryManager — pattern storage, suggestion lifecycle, auto-apply.

API notes (corrected from spec):
  - approve(suggestion_id, reviewed_by, notes, modified) — no agent_id param
  - reject(suggestion_id, reviewed_by, notes)            — no agent_id param
  - is_auto_apply_enabled(agent_id) → tuple[bool, float | None]
  - queue_suggestion needs "to_agent" field to be found via get_pending(agent_id)
  - No _load_history() — use get_approval_stats(agent_id) instead
"""
import pytest
import aigis_agents.mesh.memory_manager as mm_module
from aigis_agents.mesh.memory_manager import MemoryManager


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    """MemoryManager with paths redirected to tmp_path."""
    monkeypatch.setattr(mm_module, "_AGENTS_ROOT", tmp_path)
    return MemoryManager()


@pytest.fixture()
def agent_id():
    return "agent_02"


@pytest.mark.unit
class TestPatterns:

    def test_load_patterns_empty_on_first_run(self, mem, agent_id):
        patterns = mem.load_patterns(agent_id)
        assert isinstance(patterns, list)
        assert patterns == []

    def test_save_and_load_pattern(self, mem, agent_id):
        pattern = {
            "pattern_id": "p001",
            "category": "classification",
            "description": "Quarterly LOS always has 4 tabs",
            "confidence": 0.95,
        }
        mem.save_pattern(agent_id, pattern)
        loaded = mem.load_patterns(agent_id)
        assert any(p["pattern_id"] == "p001" for p in loaded)

    def test_save_duplicate_pattern_deduplicated(self, mem, agent_id):
        pattern = {"pattern_id": "p_dup", "description": "test"}
        mem.save_pattern(agent_id, pattern)
        mem.save_pattern(agent_id, pattern)
        loaded = mem.load_patterns(agent_id)
        ids = [p["pattern_id"] for p in loaded]
        assert ids.count("p_dup") == 1


@pytest.mark.unit
class TestRunHistory:

    def test_log_run_creates_record(self, mem, agent_id):
        mem.log_run(agent_id, {
            "run_id": "r001",
            "deal_id": "d001",
            "mode": "standalone",
            "timestamp": "2026-02-28T10:00:00Z",
            "audit_score": 0.9,
            "duration_s": 12.3,
        })
        history = mem.get_run_history(agent_id)
        assert isinstance(history, list)
        assert any(r["run_id"] == "r001" for r in history)


@pytest.mark.unit
class TestSuggestionLifecycle:

    def test_queue_suggestion_returns_id(self, mem, agent_id):
        suggestion = {
            "from_agent": agent_id,
            "to_agent": agent_id,
            "deal_id": "d001",
            "type": "classification_improvement",
            "description": "Add 'Lean LOS' as a checklist subtype",
        }
        sid = mem.queue_suggestion(suggestion)
        assert isinstance(sid, str) and len(sid) > 0

    def test_get_pending_includes_queued(self, mem, agent_id):
        suggestion = {
            "from_agent": agent_id,
            "to_agent": agent_id,
            "deal_id": "d001",
            "type": "test",
            "description": "Test suggestion",
        }
        sid = mem.queue_suggestion(suggestion)
        pending = mem.get_pending(agent_id)
        assert any(s.get("suggestion_id") == sid for s in pending)

    def test_approve_moves_from_pending(self, mem, agent_id):
        suggestion = {
            "from_agent": agent_id,
            "to_agent": agent_id,
            "type": "test",
            "description": "Approve me",
        }
        sid = mem.queue_suggestion(suggestion)
        mem.approve(sid)
        pending = mem.get_pending(agent_id)
        assert not any(s.get("suggestion_id") == sid for s in pending)

    def test_reject_removes_from_pending(self, mem, agent_id):
        suggestion = {
            "from_agent": agent_id,
            "to_agent": agent_id,
            "type": "test",
            "description": "Reject me",
        }
        sid = mem.queue_suggestion(suggestion)
        mem.reject(sid, notes="Not relevant")
        pending = mem.get_pending(agent_id)
        assert not any(s.get("suggestion_id") == sid for s in pending)

    def test_approval_stats_updated_on_approve(self, mem, agent_id):
        for i in range(3):
            sid = mem.queue_suggestion({
                "from_agent": agent_id,
                "to_agent": agent_id,
                "type": "t",
                "description": f"s{i}",
            })
            mem.approve(sid)
        stats = mem.get_approval_stats(agent_id)
        assert stats["approved_as_suggested"] >= 3


@pytest.mark.unit
class TestAutoApply:

    def test_auto_apply_not_eligible_below_threshold(self, mem, agent_id):
        # Only 2 approvals — below min 10
        for i in range(2):
            sid = mem.queue_suggestion({
                "from_agent": agent_id,
                "to_agent": agent_id,
                "type": "t",
                "description": f"s{i}",
            })
            mem.approve(sid)
        assert mem.check_auto_apply_eligibility(agent_id) is False

    def test_enable_disable_auto_apply(self, mem, agent_id):
        mem.enable_auto_apply(agent_id, threshold=0.85)
        enabled, threshold = mem.is_auto_apply_enabled(agent_id)
        assert enabled is True
        mem.disable_auto_apply(agent_id)
        enabled2, _ = mem.is_auto_apply_enabled(agent_id)
        assert enabled2 is False
