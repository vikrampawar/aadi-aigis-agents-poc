"""Domain knowledge loader for Agent 04 — Finance Calculator."""

from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).parent


def load_primer() -> str:
    """Load the Agent 04 domain knowledge primer."""
    path = _HERE / "agent_04_domain_knowledge_primer.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def load_knowledge_bank() -> str:
    """Load the canonical formula and definition library."""
    path = _HERE / "agent_04_finance_knowledge_bank_v1.0.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def load_fiscal_playbook() -> str:
    """Load the fiscal terms playbook (regime-specific reference)."""
    path = _HERE / "fiscal_terms_playbook.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def load_financial_playbook() -> str:
    """Load the financial analyst playbook (DD framework reference)."""
    path = _HERE / "financial_analyst_playbook.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_full_context() -> str:
    """Concatenate all domain knowledge files for LLM system prompt."""
    sections = [
        ("## Agent 04 Domain Knowledge Primer", load_primer()),
        ("## Finance Knowledge Bank", load_knowledge_bank()),
        ("## Fiscal Terms Playbook", load_fiscal_playbook()),
        ("## Financial Analyst Playbook", load_financial_playbook()),
    ]
    parts = []
    for header, content in sections:
        if content:
            parts.append(f"{header}\n\n{content}")
    return "\n\n---\n\n".join(parts)
