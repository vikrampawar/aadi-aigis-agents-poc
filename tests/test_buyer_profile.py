"""
Tests for BuyerProfileManager and AuditLayer.detect_preferences().

Coverage:
  - Profile file created with template on first access
  - load_as_context() returns markdown string
  - load_as_dict() returns section dict
  - update_section() replaces / appends section content
  - append_learning_log_entry() appends table row
  - apply_signal() writes preference + log entry
  - run_qa_wizard() processes answers into correct sections (via stdin mock)
  - detect_preferences() returns PreferenceSignal list from LLM response
  - detect_preferences() returns [] on LLM failure (non-blocking)
  - AgentBase injects buyer_context into _run() arguments
  - Step 9.5 prompts user only in standalone mode (not tool_call)
"""
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from aigis_agents.mesh.buyer_profile_manager import (
    BuyerProfileManager,
    PreferenceSignal,
    BUYER_QA_QUESTIONS,
)
from aigis_agents.mesh.audit_layer import AuditLayer


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def profile_path(tmp_path) -> Path:
    """Return a path inside tmp_path; file does not exist yet."""
    return tmp_path / "buyer_profile.md"


@pytest.fixture()
def manager(profile_path) -> BuyerProfileManager:
    return BuyerProfileManager(profile_path=profile_path)


# ── Creation / initialisation ─────────────────────────────────────────────────

class TestProfileCreation:
    def test_file_created_on_init(self, profile_path):
        BuyerProfileManager(profile_path=profile_path)
        assert profile_path.exists(), "Profile file should be created on instantiation"

    def test_template_content_present(self, profile_path):
        BuyerProfileManager(profile_path=profile_path)
        text = profile_path.read_text(encoding="utf-8")
        assert "# Buyer Profile" in text
        assert "## 1. Investment Thesis" in text
        assert "## 8. Learning Log" in text

    def test_does_not_overwrite_existing(self, profile_path):
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("# Custom Profile\n", encoding="utf-8")
        BuyerProfileManager(profile_path=profile_path)
        assert profile_path.read_text(encoding="utf-8") == "# Custom Profile\n"


# ── load_as_context ───────────────────────────────────────────────────────────

class TestLoadAsContext:
    def test_returns_string(self, manager):
        context = manager.load_as_context()
        assert isinstance(context, str)
        assert len(context) > 0

    def test_contains_sections(self, manager):
        context = manager.load_as_context()
        assert "Investment Thesis" in context
        assert "Financial Thresholds" in context

    def test_missing_file_returns_placeholder(self, tmp_path):
        mgr = BuyerProfileManager(profile_path=tmp_path / "missing.md")
        # Delete after creation to simulate missing
        (tmp_path / "missing.md").unlink()
        context = mgr.load_as_context()
        assert "Buyer Profile" in context


# ── load_as_dict ──────────────────────────────────────────────────────────────

class TestLoadAsDict:
    def test_returns_dict(self, manager):
        d = manager.load_as_dict()
        assert isinstance(d, dict)

    def test_section_keys_present(self, manager):
        d = manager.load_as_dict()
        keys = list(d.keys())
        assert any("Investment Thesis" in k for k in keys)
        assert any("Financial Thresholds" in k for k in keys)
        assert any("Learning Log" in k for k in keys)


# ── update_section ────────────────────────────────────────────────────────────

class TestUpdateSection:
    def test_replaces_existing_section(self, manager):
        manager.update_section("2. Financial Thresholds", "- min_irr_pct: 15%")
        text = manager.load_as_context()
        assert "min_irr_pct: 15%" in text

    def test_other_sections_preserved(self, manager):
        manager.update_section("2. Financial Thresholds", "- min_irr_pct: 15%")
        text = manager.load_as_context()
        assert "Investment Thesis" in text
        assert "Learning Log" in text

    def test_version_incremented(self, manager):
        manager.update_section("2. Financial Thresholds", "updated")
        text = manager.load_as_context()
        assert "Version: 2" in text

    def test_append_new_section(self, manager):
        manager.update_section("Custom Section", "custom content here")
        text = manager.load_as_context()
        assert "Custom Section" in text
        assert "custom content here" in text


# ── append_learning_log_entry ─────────────────────────────────────────────────

class TestAppendLearningLog:
    def test_row_appears_in_profile(self, manager):
        manager.append_learning_log_entry(
            date="2026-03-01",
            source="qa_wizard",
            preference="oil_price_deck = $65/bbl flat",
        )
        text = manager.load_as_context()
        assert "2026-03-01" in text
        assert "qa_wizard" in text
        assert "$65/bbl flat" in text

    def test_multiple_entries_all_present(self, manager):
        manager.append_learning_log_entry("2026-03-01", "wizard", "pref_a")
        manager.append_learning_log_entry("2026-03-02", "feedback", "pref_b")
        text = manager.load_as_context()
        assert "pref_a" in text
        assert "pref_b" in text


# ── apply_signal ──────────────────────────────────────────────────────────────

class TestApplySignal:
    def test_price_deck_written_to_preferences(self, manager):
        signal = PreferenceSignal(
            category="price_deck",
            key="oil_price_deck",
            value="$65/bbl flat",
            raw_text="use $65 flat for oil",
            confidence=0.95,
        )
        manager.apply_signal(signal)
        text = manager.load_as_context()
        assert "$65/bbl flat" in text

    def test_log_entry_appended(self, manager):
        signal = PreferenceSignal(
            category="financial_threshold",
            key="min_irr_pct",
            value="15%",
            raw_text="minimum IRR of 15%",
            confidence=0.90,
        )
        manager.apply_signal(signal)
        text = manager.load_as_context()
        assert "min_irr_pct" in text
        assert "15%" in text

    def test_signal_categories_all_map(self, manager):
        categories = ["price_deck", "financial_threshold", "operational", "strategic", "negotiation"]
        for cat in categories:
            signal = PreferenceSignal(
                category=cat, key=f"{cat}_key", value=f"test_{cat}",
                raw_text="test", confidence=0.8,
            )
            manager.apply_signal(signal)  # should not raise


# ── run_qa_wizard ─────────────────────────────────────────────────────────────

class TestRunQAWizard:
    def test_wizard_writes_answers_to_profile(self, manager):
        # 20 questions — provide answers for 2, skip the rest
        answers = ["Tamarind Energy — GoM shelf consolidator"] + [""] * 19
        stdin_data = "\n".join(answers) + "\n"

        with patch("builtins.input", side_effect=answers):
            manager.run_qa_wizard()

        text = manager.load_as_context()
        assert "Tamarind Energy" in text

    def test_wizard_appends_log_entry(self, manager):
        answers = [""] * 20  # skip all questions
        with patch("builtins.input", side_effect=answers):
            manager.run_qa_wizard()
        text = manager.load_as_context()
        assert "qa_wizard" in text

    def test_qa_questions_list_has_20_items(self):
        assert len(BUYER_QA_QUESTIONS) == 20

    def test_qa_questions_have_required_keys(self):
        for q in BUYER_QA_QUESTIONS:
            assert "section" in q
            assert "key" in q
            assert "question" in q


# ── detect_preferences (AuditLayer) ──────────────────────────────────────────

class TestDetectPreferences:
    def _make_audit_layer(self, llm_response: str) -> AuditLayer:
        from helpers import MockLLM
        mock = MockLLM(responses={"Preference Detector": llm_response})
        # detect_preferences() checks for "Preference Detector" substring not present,
        # so we use the default fallback; patch via a broader key
        mock2 = MockLLM(responses={"": llm_response})  # matches any prompt
        return AuditLayer(mock2)

    def test_returns_signal_list(self):
        signals_json = json.dumps([
            {"category": "price_deck", "key": "oil_price_deck",
             "value": "$65/bbl flat", "raw_text": "use $65 flat", "confidence": 0.95},
        ])
        audit = self._make_audit_layer(signals_json)
        signals = audit.detect_preferences({"price": 65}, {"recommendation": "bid $130mm"})
        assert isinstance(signals, list)
        assert len(signals) == 1
        assert signals[0].key == "oil_price_deck"
        assert signals[0].value == "$65/bbl flat"
        assert signals[0].confidence == 0.95

    def test_filters_low_confidence(self):
        signals_json = json.dumps([
            {"category": "price_deck", "key": "oil_price_deck",
             "value": "$60/bbl", "raw_text": "maybe $60?", "confidence": 0.3},
            {"category": "financial_threshold", "key": "min_irr_pct",
             "value": "15%", "raw_text": "need 15% IRR", "confidence": 0.9},
        ])
        audit = self._make_audit_layer(signals_json)
        signals = audit.detect_preferences({}, {})
        # Only the high-confidence signal (>= 0.5) should be returned
        assert len(signals) == 1
        assert signals[0].key == "min_irr_pct"

    def test_returns_empty_on_no_signals(self):
        audit = self._make_audit_layer("[]")
        signals = audit.detect_preferences({}, {})
        assert signals == []

    def test_non_blocking_on_llm_failure(self):
        """Should return [] if LLM raises, not propagate exception."""
        from helpers import MockLLM

        class FailingLLM:
            def invoke(self, messages):
                raise RuntimeError("LLM offline")

        audit = AuditLayer(FailingLLM())
        result = audit.detect_preferences({"input": "x"}, {"output": "y"})
        assert result == []

    def test_handles_malformed_json(self):
        audit = self._make_audit_layer("not valid json {{{{")
        signals = audit.detect_preferences({}, {})
        assert signals == []

    def test_handles_non_list_json(self):
        audit = self._make_audit_layer('{"error": "unexpected dict"}')
        signals = audit.detect_preferences({}, {})
        assert signals == []


# ── AgentBase buyer_context injection ────────────────────────────────────────

class TestAgentBaseBuyerContext:
    def test_buyer_context_passed_to_run(self, tmp_path, patch_toolkit, patch_get_chat_model):
        """_run() should receive buyer_context as a keyword argument."""
        from aigis_agents.mesh.agent_base import AgentBase

        received: dict = {}

        class ConcreteAgent(AgentBase):
            AGENT_ID = "agent_04"
            DK_TAGS  = []

            def _run(self, deal_id, main_llm, dk_context, buyer_context,
                     patterns, mode="standalone", output_dir="./outputs", **_):
                received["buyer_context"] = buyer_context
                return {"result": "ok"}

        # Point buyer profile to tmp_path so it uses a blank template
        from aigis_agents.mesh import buyer_profile_manager as bpm
        with patch.object(bpm, "_PROFILE_PATH", tmp_path / "buyer_profile.md"):
            # Reload the module-level singleton so it uses the patched path
            import aigis_agents.mesh.agent_base as ab
            ab._buyer_profile = bpm.BuyerProfileManager(tmp_path / "buyer_profile.md")
            agent = ConcreteAgent()
            agent._buyer_profile = bpm.BuyerProfileManager(tmp_path / "buyer_profile.md")

            agent.invoke(
                mode="standalone",
                deal_id="test-deal-001",
                output_dir=str(tmp_path),
            )

        assert "buyer_context" in received
        assert isinstance(received["buyer_context"], str)
        assert "Buyer Profile" in received["buyer_context"]

    def test_tool_call_mode_skips_preference_prompt(
        self, tmp_path, patch_toolkit, patch_get_chat_model
    ):
        """Step 9.5 should NOT call input() in tool_call mode."""
        from aigis_agents.mesh.agent_base import AgentBase
        import aigis_agents.mesh.buyer_profile_manager as bpm

        class ConcreteAgent(AgentBase):
            AGENT_ID = "agent_04"
            DK_TAGS  = []

            def _run(self, deal_id, main_llm, dk_context, buyer_context,
                     patterns, mode="standalone", output_dir="./outputs", **_):
                return {"result": "ok"}

        ab_mod = __import__("aigis_agents.mesh.agent_base", fromlist=["_buyer_profile"])
        ab_mod._buyer_profile = bpm.BuyerProfileManager(tmp_path / "buyer_profile.md")

        with patch("builtins.input") as mock_input:
            agent = ConcreteAgent()
            agent._buyer_profile = bpm.BuyerProfileManager(tmp_path / "buyer_profile.md")
            agent.invoke(
                mode="tool_call",
                deal_id="test-deal-001",
                output_dir=str(tmp_path),
            )
            mock_input.assert_not_called()
