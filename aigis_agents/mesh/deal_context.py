"""
DealContextManager — Per-deal accumulating markdown context.

Each deal maintains a deal_context.md file that accumulates findings from
every agent that processes it.  Unlike agent-local memory files, deal context
is shared read/write across all agents in a pipeline run.

Structure:
  aigis_agents/memory/{deal_id}/deal_context.md

Each agent owns a named section that it overwrites on each run.  A run log
(append-only) captures key flags and a brief summary per agent per run.

Usage:
    from aigis_agents.mesh.deal_context import DealContextManager, DealContextSection

    mgr = DealContextManager(deal_id="deal-001")
    print(mgr.load())

    mgr.update_section(DealContextSection(
        agent_id="agent_01",
        section_name="Agent 01 — VDR Inventory Summary",
        content="Coverage: 85% | Missing NTH: 3",
        updated_at="2026-03-01",
        run_id="r-abc",
    ))
    mgr.append_run_log("agent_01", "r-abc", flags=["Missing CPR"], summary="...")
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


# ── Path helpers ────────────────────────────────────────────────────────────────

# aigis_agents/mesh/deal_context.py → .parent.parent → aigis_agents/
_AGENTS_ROOT = Path(__file__).parent.parent
_MEMORY_ROOT = _AGENTS_ROOT / "memory"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Dataclasses ─────────────────────────────────────────────────────────────────

@dataclass
class DealContextSection:
    agent_id:     str
    section_name: str
    content:      str
    updated_at:   str
    run_id:       str


# ── Blank template ──────────────────────────────────────────────────────────────

_TEMPLATE = """\
# Deal Context — {deal_id}
*Deal ID: {deal_id} | Created: {date} | Last updated: {date}*

---

## Agent 01 — VDR Inventory Summary
*Not yet populated.*

---

## Agent 02 — Data Store Summary
*Not yet populated.*

---

## Agent 04 — Financial Analysis Summary
*Not yet populated.*

---

## Run Log
| Timestamp | Agent | Run ID | Key Flags | Summary |
|-----------|-------|--------|-----------|---------|
"""


# ── DealContextManager ──────────────────────────────────────────────────────────

class DealContextManager:
    """Read/write deal_context.md for a specific deal.

    Agents contribute named sections (via update_section) and append rows to
    the run log (via append_run_log).  The full file is available for LLM
    injection via load().
    """

    def __init__(
        self,
        deal_id: str,
        memory_root: str | Path | None = None,
    ) -> None:
        self._deal_id = deal_id
        root = Path(memory_root) if memory_root is not None else _MEMORY_ROOT
        self._path = root / deal_id / "deal_context.md"
        self._ensure_file_exists()

    # ── Public API ──────────────────────────────────────────────────────────────

    def load(self) -> str:
        """Return the full deal_context.md content for LLM injection."""
        try:
            return self._path.read_text(encoding="utf-8")
        except OSError:
            return (
                f"# Deal Context — {self._deal_id}\n\n"
                "*(No deal context available for this deal yet.)*\n"
            )

    def update_section(self, section: DealContextSection) -> None:
        """Create or replace the agent's named section in deal_context.md.

        The section heading format is:
            ## {section.section_name}
            *Updated: {section.updated_at} | Run: {section.run_id}*
            {section.content}

        If a section with that heading already exists it is replaced in-place.
        If not, it is inserted before the Run Log section.
        """
        text = self.load()

        heading   = f"## {section.section_name}"
        meta_line = f"*Updated: {section.updated_at} | Run: {section.run_id}*"
        new_block = f"{heading}\n{meta_line}\n{section.content}"

        # Match from the heading up to (but not including) the next ## or end
        pattern = re.compile(
            rf"## {re.escape(section.section_name)}.*?(?=\n## |\Z)",
            re.DOTALL,
        )
        if pattern.search(text):
            text = pattern.sub(new_block, text, count=1)
        else:
            # Insert before the Run Log section (with separator)
            run_log_re = re.compile(r"\n## Run Log\b", re.DOTALL)
            if run_log_re.search(text):
                text = run_log_re.sub(
                    f"\n\n---\n\n{new_block}\n\n---\n\n## Run Log",
                    text,
                    count=1,
                )
            else:
                text = text.rstrip() + f"\n\n---\n\n{new_block}\n"

        # Refresh "Last updated" in file header
        text = re.sub(
            r"\*Deal ID: [^|]+ \| Created: ([^|]+) \| Last updated: [^*]+\*",
            rf"*Deal ID: {self._deal_id} | Created: \1 | Last updated: {section.updated_at}*",
            text,
            count=1,
        )

        self._atomic_write(text)

    def append_run_log(
        self,
        agent_id: str,
        run_id:   str,
        flags:    list[str],
        summary:  str,
    ) -> None:
        """Append a row to the Run Log table at the bottom of deal_context.md."""
        text = self.load()
        ts        = _now_ts()[:19]                          # trim to seconds
        flags_str = "; ".join(flags[:3]) if flags else "—"
        safe_sum  = summary.replace("|", "/")[:120]
        row = f"| {ts} | {agent_id} | {run_id[:12]} | {flags_str} | {safe_sum} |"

        run_log_sep = "|-----------|-------|--------|-----------|---------|"
        if run_log_sep in text:
            # Append after the last existing row (i.e. append to end of file)
            text = text.rstrip() + "\n" + row + "\n"
        else:
            # No run log table yet — create it
            text = text.rstrip() + (
                "\n\n## Run Log\n"
                "| Timestamp | Agent | Run ID | Key Flags | Summary |\n"
                "|-----------|-------|--------|-----------|--------|\n"
                f"{row}\n"
            )

        self._atomic_write(text)

    def get_summary(self, max_chars: int = 3000) -> str:
        """Return content up to *max_chars* characters (with truncation note)."""
        text = self.load()
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n*(deal_context truncated for context limit)*\n"

    def get_section(self, agent_id: str, section_name: str) -> str | None:
        """Return the text of *section_name*, or None if absent / not yet populated."""
        text = self.load()
        pattern = re.compile(
            rf"## {re.escape(section_name)}.*?(?=\n## |\Z)",
            re.DOTALL,
        )
        m = pattern.search(text)
        if not m:
            return None
        content = m.group(0).strip()
        if "Not yet populated" in content:
            return None
        return content

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _ensure_file_exists(self) -> None:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(_TEMPLATE.format(deal_id=self._deal_id, date=_today()))

    def _atomic_write(self, content: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, self._path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
