"""
Shared test helpers — MockLLM, canned audit responses, and constants.

Import these directly in tests that need to instantiate MockLLM outside
of a fixture (e.g. inline LLM override in a specific test).

    from helpers import MockLLM, VALID_INPUT_AUDIT, FAILING_INPUT_AUDIT
"""
from __future__ import annotations

import json


# ── Mock LLM ─────────────────────────────────────────────────────────────────


class MockMessage:
    """Mimics a LangChain AIMessage."""
    def __init__(self, content: str):
        self.content = content


class MockLLM:
    """Predictable LLM that returns canned responses based on prompt keywords."""

    def __init__(self, responses: dict[str, str] | None = None):
        self._responses = responses or {}
        self.call_count = 0
        self.last_prompt = None

    def invoke(self, messages) -> MockMessage:
        self.call_count += 1
        prompt_text = str(messages)
        self.last_prompt = prompt_text
        for keyword, response in self._responses.items():
            if keyword in prompt_text:
                return MockMessage(response)
        # Default: valid input audit response
        return MockMessage(VALID_INPUT_AUDIT)

    def __call__(self, *args, **kwargs):
        return self.invoke(args[0] if args else [])


# ── Canned audit responses ────────────────────────────────────────────────────

VALID_INPUT_AUDIT = '{"valid": true, "confidence": "HIGH", "issues": [], "notes": "OK"}'

VALID_OUTPUT_AUDIT = json.dumps({
    "confidence_label": "HIGH",
    "confidence_score": 92,
    "citation_coverage": 0.85,
    "flags": [],
    "improvement_suggestions": [],
    "auditor_notes": "Output quality is good.",
})

FAILING_INPUT_AUDIT = json.dumps({
    "valid": False,
    "confidence": "LOW",
    "issues": [{"severity": "ERROR", "field": "vdr_path", "message": "vdr_path is required"}],
    "notes": "Missing required field.",
})
