"""
MemoryManager — JSON-backed persistent memory for Aigis agents.

Each agent gets three files under aigis_agents/{agent_id}/memory/:

  learned_patterns.json    — confirmed patterns accumulated across deals
  improvement_history.json — all suggestions ever filed + human review outcomes
  run_history.json         — performance log (one record per agent run)

A global cross-agent pending queue lives at:
  aigis_agents/memory/cross_agent_suggestions.json

Design:
  - Atomic writes: data is written to a temp file then renamed, so a crash
    mid-write can never corrupt the live file.
  - Graceful first-run: missing files are initialised with empty schemas.
  - Auto-apply eligibility: when approval_rate >= 0.80 AND n >= 10 reviewed
    suggestions, check_auto_apply_eligibility() returns True so the CLI can
    offer the toggle to the user.

Storage note: JSON is used for portability and zero infrastructure.  The
MemoryManager interface is designed so that swapping the backend to SQLite
(when agent count warrants it) is a single-class change with no impact on
callers.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Path helpers ───────────────────────────────────────────────────────────────

# aigis_agents/mesh/memory_manager.py → parent → aigis_agents/
_AGENTS_ROOT = Path(__file__).parent.parent

_AUTO_APPLY_MIN_REVIEWS    = 10
_AUTO_APPLY_MIN_RATE       = 0.80


def _agent_memory_dir(agent_id: str) -> Path:
    return _AGENTS_ROOT / agent_id / "memory"


def _global_memory_dir() -> Path:
    return _AGENTS_ROOT / "memory"


# ── Empty schemas ──────────────────────────────────────────────────────────────

def _empty_patterns() -> dict:
    return {"version": "1.0", "last_updated": _now(), "patterns": []}


def _empty_history() -> dict:
    return {
        "auto_apply_enabled": False,
        "auto_apply_threshold": None,
        "approval_stats": {
            "total_suggestions": 0,
            "approved_as_suggested": 0,
            "approved_with_modifications": 0,
            "rejected": 0,
            "pending": 0,
            "approval_rate": 0.0,
        },
        "suggestions": [],
    }


def _empty_run_history() -> dict:
    return {"runs": []}


def _empty_global_queue() -> dict:
    return {"pending_suggestions": []}


# ── Low-level helpers ──────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default_factory) -> dict:
    """Load JSON from *path*, returning default_factory() if missing or corrupt."""
    if not path.exists():
        return default_factory()
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default_factory()


def _save_json(path: Path, data: dict) -> None:
    """Atomically write *data* as JSON to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)   # atomic on POSIX and Windows
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── Temporal pattern weighting ──────────────────────────────────────────────────

_STALE_DAYS  = 365
_HIGH_DAYS   = 90
_HIGH_MIN_CONFIRMS = 2


def _pattern_weight(pattern: dict) -> str:
    """Classify a pattern as HIGH / MEDIUM / STALE based on recency.

    Gracefully handles missing date/confirmation fields — defaults to MEDIUM.
    """
    try:
        last_confirmed_str = pattern.get("last_confirmed_date") or pattern.get("added_date")
        if not last_confirmed_str:
            return "MEDIUM"
        last_confirmed = datetime.fromisoformat(last_confirmed_str.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - last_confirmed).days
        confirmations = pattern.get("confirmation_count", 1)
        if days >= _STALE_DAYS:
            return "STALE"
        if days < _HIGH_DAYS and confirmations >= _HIGH_MIN_CONFIRMS:
            return "HIGH"
        return "MEDIUM"
    except (ValueError, TypeError):
        return "MEDIUM"


# ── MemoryManager ──────────────────────────────────────────────────────────────

class MemoryManager:
    """Per-agent and cross-agent memory operations."""

    # ── Pattern management ────────────────────────────────────────────────────

    def load_patterns(
        self,
        agent_id: str,
        include_stale: bool = False,
    ) -> list[dict]:
        """Return confirmed learned patterns for *agent_id*, sorted by recency.

        Patterns are tagged with a temporal weight:
          HIGH   — confirmed < 90 days ago AND confirmation_count >= 2
          MEDIUM — confirmed < 365 days ago (or missing date fields)
          STALE  — confirmed >= 365 days ago

        STALE patterns are excluded by default (include_stale=False).
        Within the returned list, HIGH patterns appear before MEDIUM ones.
        """
        path = _agent_memory_dir(agent_id) / "learned_patterns.json"
        patterns = _load_json(path, _empty_patterns).get("patterns", [])

        _order = {"HIGH": 0, "MEDIUM": 1, "STALE": 2}
        weighted: list[tuple[dict, int]] = []
        for p in patterns:
            w = _pattern_weight(p)
            if w == "STALE" and not include_stale:
                continue
            weighted.append((p, _order[w]))

        weighted.sort(key=lambda x: x[1])
        return [p for p, _ in weighted]

    def save_pattern(self, agent_id: str, pattern: dict) -> None:
        """Append *pattern* to the agent's confirmed patterns list."""
        path = _agent_memory_dir(agent_id) / "learned_patterns.json"
        data = _load_json(path, _empty_patterns)
        # Deduplicate by pattern_id if present
        existing_ids = {p.get("pattern_id") for p in data["patterns"]}
        if pattern.get("pattern_id") in existing_ids:
            # Replace existing
            data["patterns"] = [
                pattern if p.get("pattern_id") == pattern.get("pattern_id") else p
                for p in data["patterns"]
            ]
        else:
            data["patterns"].append(pattern)
        data["last_updated"] = _now()
        _save_json(path, data)

    # ── Run logging ───────────────────────────────────────────────────────────

    def log_run(self, agent_id: str, run_record: dict) -> None:
        """Append *run_record* to the agent's run history."""
        path = _agent_memory_dir(agent_id) / "run_history.json"
        data = _load_json(path, _empty_run_history)
        data["runs"].append(run_record)
        _save_json(path, data)

    def get_run_history(self, agent_id: str) -> list[dict]:
        """Return the full run history for *agent_id*."""
        path = _agent_memory_dir(agent_id) / "run_history.json"
        return _load_json(path, _empty_run_history).get("runs", [])

    # ── Improvement suggestion lifecycle ──────────────────────────────────────

    def queue_suggestion(self, suggestion: dict) -> str:
        """File an improvement suggestion for human review.

        Assigns a unique suggestion_id and appends to:
          - The target agent's improvement_history.json
          - The global cross_agent_suggestions.json (pending queue)

        Returns the assigned suggestion_id.
        """
        suggestion_id = suggestion.get("suggestion_id") or f"s-{uuid.uuid4().hex[:8]}"
        to_agent = suggestion.get("to_agent", "unknown")

        record = {
            "suggestion_id": suggestion_id,
            "from_agent":     suggestion.get("from_agent", "unknown"),
            "to_agent":       to_agent,
            "deal_id":        suggestion.get("deal_id"),
            "run_id":         suggestion.get("run_id"),
            "submitted_date": _now(),
            "suggestion":     suggestion.get("suggestion", ""),
            "audit_confidence": suggestion.get("confidence", 0.0),
            "status":         "pending",
            "reviewed_by":    None,
            "review_date":    None,
            "review_notes":   None,
        }

        # Append to target agent's improvement_history.json
        self._append_suggestion_to_agent(to_agent, record)

        # Append to global pending queue
        self._append_to_global_queue(record)

        return suggestion_id

    def get_pending(self, agent_id: str | None = None) -> list[dict]:
        """Return all pending suggestions, optionally filtered by target agent."""
        if agent_id:
            path = _agent_memory_dir(agent_id) / "improvement_history.json"
            data = _load_json(path, _empty_history)
            return [s for s in data["suggestions"] if s["status"] == "pending"]
        # Global queue
        path = _global_memory_dir() / "cross_agent_suggestions.json"
        data = _load_json(path, _empty_global_queue)
        return data.get("pending_suggestions", [])

    def approve(
        self,
        suggestion_id: str,
        reviewed_by: str = "human",
        notes: str = "",
        modified: bool = False,
    ) -> None:
        """Mark *suggestion_id* as approved (as suggested or with modifications)."""
        status = "approved_with_modifications" if modified else "approved_as_suggested"
        self._resolve_suggestion(suggestion_id, status, reviewed_by, notes)

    def reject(
        self,
        suggestion_id: str,
        reviewed_by: str = "human",
        notes: str = "",
    ) -> None:
        """Mark *suggestion_id* as rejected."""
        self._resolve_suggestion(suggestion_id, "rejected", reviewed_by, notes)

    # ── Approval stats & auto-apply ───────────────────────────────────────────

    def get_approval_stats(self, agent_id: str) -> dict:
        """Return the approval_stats dict for *agent_id*."""
        path = _agent_memory_dir(agent_id) / "improvement_history.json"
        data = _load_json(path, _empty_history)
        return data.get("approval_stats", _empty_history()["approval_stats"])

    def check_auto_apply_eligibility(self, agent_id: str) -> bool:
        """Return True if auto-apply could be enabled (but isn't yet).

        Eligibility requires:
          - auto_apply_enabled is False (not already on)
          - approval_rate >= 0.80
          - total reviewed suggestions >= 10
        """
        path = _agent_memory_dir(agent_id) / "improvement_history.json"
        data = _load_json(path, _empty_history)
        if data.get("auto_apply_enabled"):
            return False
        stats = data.get("approval_stats", {})
        reviewed = (
            stats.get("approved_as_suggested", 0)
            + stats.get("approved_with_modifications", 0)
            + stats.get("rejected", 0)
        )
        rate = stats.get("approval_rate", 0.0)
        return reviewed >= _AUTO_APPLY_MIN_REVIEWS and rate >= _AUTO_APPLY_MIN_RATE

    def enable_auto_apply(self, agent_id: str, threshold: float) -> None:
        """Enable auto-apply for *agent_id* above *threshold* confidence."""
        path = _agent_memory_dir(agent_id) / "improvement_history.json"
        data = _load_json(path, _empty_history)
        data["auto_apply_enabled"]  = True
        data["auto_apply_threshold"] = threshold
        _save_json(path, data)

    def disable_auto_apply(self, agent_id: str) -> None:
        """Disable auto-apply for *agent_id*."""
        path = _agent_memory_dir(agent_id) / "improvement_history.json"
        data = _load_json(path, _empty_history)
        data["auto_apply_enabled"]  = False
        data["auto_apply_threshold"] = None
        _save_json(path, data)

    def is_auto_apply_enabled(self, agent_id: str) -> tuple[bool, float | None]:
        """Return (enabled, threshold) for *agent_id*."""
        path = _agent_memory_dir(agent_id) / "improvement_history.json"
        data = _load_json(path, _empty_history)
        return data.get("auto_apply_enabled", False), data.get("auto_apply_threshold")

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _append_suggestion_to_agent(self, agent_id: str, record: dict) -> None:
        path = _agent_memory_dir(agent_id) / "improvement_history.json"
        data = _load_json(path, _empty_history)
        data["suggestions"].append(record)
        self._recompute_stats(data)
        _save_json(path, data)

    def _append_to_global_queue(self, record: dict) -> None:
        path = _global_memory_dir() / "cross_agent_suggestions.json"
        data = _load_json(path, _empty_global_queue)
        data.setdefault("pending_suggestions", []).append(record)
        _save_json(path, data)

    def _resolve_suggestion(
        self,
        suggestion_id: str,
        status: str,
        reviewed_by: str,
        notes: str,
    ) -> None:
        """Set the status of *suggestion_id* in both agent history and global queue."""
        review_ts = _now()

        # Update agent's improvement_history.json
        resolved_agent: str | None = None
        for agent_dir in _AGENTS_ROOT.iterdir():
            hist_path = agent_dir / "memory" / "improvement_history.json"
            if not hist_path.exists():
                continue
            data = _load_json(hist_path, _empty_history)
            changed = False
            for s in data["suggestions"]:
                if s["suggestion_id"] == suggestion_id:
                    s["status"]      = status
                    s["reviewed_by"] = reviewed_by
                    s["review_date"] = review_ts
                    s["review_notes"] = notes
                    changed = True
                    resolved_agent = agent_dir.name
            if changed:
                self._recompute_stats(data)
                _save_json(hist_path, data)

        # Remove from global pending queue
        global_path = _global_memory_dir() / "cross_agent_suggestions.json"
        if global_path.exists():
            gdata = _load_json(global_path, _empty_global_queue)
            gdata["pending_suggestions"] = [
                s for s in gdata.get("pending_suggestions", [])
                if s["suggestion_id"] != suggestion_id
            ]
            _save_json(global_path, gdata)

        if resolved_agent is None:
            raise KeyError(f"Suggestion '{suggestion_id}' not found in any agent's history.")

    @staticmethod
    def _recompute_stats(data: dict) -> None:
        """Recalculate approval_stats in-place from the suggestions list."""
        suggestions = data.get("suggestions", [])
        approved    = sum(1 for s in suggestions if s["status"] == "approved_as_suggested")
        modified    = sum(1 for s in suggestions if s["status"] == "approved_with_modifications")
        rejected    = sum(1 for s in suggestions if s["status"] == "rejected")
        auto_applied = sum(1 for s in suggestions if s["status"] == "auto_applied")
        pending     = sum(1 for s in suggestions if s["status"] == "pending")
        total       = len(suggestions)
        reviewed    = approved + modified + rejected + auto_applied
        rate        = (approved + auto_applied) / reviewed if reviewed else 0.0

        data["approval_stats"] = {
            "total_suggestions":             total,
            "approved_as_suggested":         approved,
            "approved_with_modifications":   modified,
            "rejected":                      rejected,
            "auto_applied":                  auto_applied,
            "pending":                       pending,
            "approval_rate":                 round(rate, 4),
        }
