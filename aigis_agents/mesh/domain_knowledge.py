"""
DomainKnowledgeRouter — session-cached loader for domain_knowledge/ files.

Design:
  - Files are loaded from disk once per process and served from a class-level
    in-memory cache.  This means the first call to build_context_block() for a
    given set of tags triggers disk reads; subsequent calls within the same
    process are instant.
  - Pass refresh=True to force a reload from disk (e.g. if files have been
    updated during a long-running session).
  - The router resolves file paths relative to the repository root, which is
    two levels above the aigis_agents/ package directory.

Usage:
    router = DomainKnowledgeRouter()
    context = router.build_context_block(["financial", "oil_gas_101"])
    # context is a formatted string ready for LLM prompt injection
"""

from __future__ import annotations

import glob as _glob
from pathlib import Path
from typing import ClassVar


# ── Path constants ─────────────────────────────────────────────────────────────

# aigis_agents/mesh/domain_knowledge.py → parent → aigis_agents/ → parent → repo root
_REPO_ROOT = Path(__file__).parent.parent.parent
_DK_ROOT   = _REPO_ROOT / "domain_knowledge"

# ── Tag → file mapping ─────────────────────────────────────────────────────────
# Each tag resolves to one or more glob patterns relative to _DK_ROOT.
_TAG_MAP: dict[str, list[str]] = {
    "vdr_structure":   ["DD_Process/Aigis_DD_DomainKnowledge_PART4_VDR_Workflow_Agent_Mapping.md"],
    "checklist":       ["DD_Process/Aigis_DD_DomainKnowledge_PART1_Header_Taxonomy_Phases.md"],
    "upstream_dd":     ["upstream_vdr_playbook.md"],
    "financial":       ["financial_analyst_playbook.md", "fiscal_terms_playbook.md"],
    "technical":       ["technical_analyst_playbook.md"],
    "legal":           ["legal_analyst_playbook.md"],
    "esg":             ["esg_analyst_playbook.md"],
    "golden_questions":["golden_question_checklist.md"],
    "dd_process_full": ["DD_Process/Aigis_DD_DomainKnowledge_PART1_Header_Taxonomy_Phases.md",
                        "DD_Process/Aigis_DD_DomainKnowledge_PART2_Workstreams_Technical_Financial_Legal.md",
                        "DD_Process/Aigis_DD_DomainKnowledge_PART3_Workstreams_HSE_Operational_Strategic.md",
                        "DD_Process/Aigis_DD_DomainKnowledge_PART4_VDR_Workflow_Agent_Mapping.md",
                        "DD_Process/Aigis_DD_DomainKnowledge_PART5_Standards_Benchmarks_Glossary_Appendix.md"],
    "oil_gas_101":     ["Upstream Oil & Gas 101*.md"],
}


class DomainKnowledgeRouter:
    """Session-scoped singleton-style DK loader.

    The cache is a class variable so it persists for the full process lifetime
    regardless of how many DomainKnowledgeRouter instances are created.
    """

    _cache: ClassVar[dict[str, str]] = {}   # relative_path → content

    # ── Public API ─────────────────────────────────────────────────────────────

    def load(self, tags: list[str], refresh: bool = False) -> dict[str, str]:
        """Return {relative_path: content} for all files matching *tags*.

        Args:
            tags:    List of tag strings (see _TAG_MAP for valid values).
            refresh: If True, evict matching files from cache and re-read.
        Returns:
            Dict mapping relative file path → file content string.
        """
        paths = self._resolve_paths(tags)
        result: dict[str, str] = {}
        for rel in paths:
            if refresh and rel in self._cache:
                del self._cache[rel]
            if rel not in self._cache:
                abs_path = _DK_ROOT / rel
                if abs_path.exists():
                    self._cache[rel] = abs_path.read_text(encoding="utf-8")
                else:
                    # Warn but don't crash — a missing file gets an empty entry
                    self._cache[rel] = (
                        f"<!-- DK file not found: {rel} -->"
                    )
            result[rel] = self._cache[rel]
        return result

    def build_context_block(self, tags: list[str], refresh: bool = False) -> str:
        """Return a single formatted string ready for LLM prompt injection.

        Each file is wrapped in a header and horizontal rule so the LLM can
        clearly identify which source it is reading.

        Args:
            tags:    List of tag strings.
            refresh: If True, force reload from disk.
        Returns:
            Multi-section markdown string suitable for inclusion in a prompt.
        """
        files = self.load(tags, refresh=refresh)
        if not files:
            return ""

        sections: list[str] = []
        for rel_path, content in files.items():
            header = f"## DOMAIN KNOWLEDGE: {Path(rel_path).name}"
            sections.append(f"{header}\n\n{content}")

        return "\n\n---\n\n".join(sections)

    def available_tags(self) -> list[str]:
        """Return the list of all supported tag names."""
        return sorted(_TAG_MAP)

    def clear_cache(self) -> None:
        """Evict all entries from the session cache."""
        self._cache.clear()

    def cache_stats(self) -> dict[str, int]:
        """Return stats about the current cache state."""
        return {
            "cached_files": len(self._cache),
            "total_chars": sum(len(v) for v in self._cache.values()),
        }

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _resolve_paths(tags: list[str]) -> list[str]:
        """Expand tags to a de-duplicated ordered list of relative file paths."""
        seen: set[str] = set()
        ordered: list[str] = []
        for tag in tags:
            patterns = _TAG_MAP.get(tag, [])
            for pattern in patterns:
                # Support glob wildcards (e.g. "Upstream Oil & Gas 101*.md")
                if "*" in pattern or "?" in pattern:
                    abs_matches = _glob.glob(str(_DK_ROOT / pattern))
                    for abs_match in sorted(abs_matches):
                        rel = str(Path(abs_match).relative_to(_DK_ROOT)).replace("\\", "/")
                        if rel not in seen:
                            seen.add(rel)
                            ordered.append(rel)
                else:
                    rel = pattern.replace("\\", "/")
                    if rel not in seen:
                        seen.add(rel)
                        ordered.append(rel)
        return ordered
