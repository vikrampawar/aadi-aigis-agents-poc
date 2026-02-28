"""
review_memory — CLI for reviewing improvement suggestions and managing auto-apply.

Usage:
    # List all pending suggestions across all agents
    python -m aigis_agents.mesh.review_memory --list

    # List pending for a specific agent
    python -m aigis_agents.mesh.review_memory --list --agent agent_01

    # Review a specific suggestion interactively
    python -m aigis_agents.mesh.review_memory --review s001abcd

    # Show approval statistics + auto-apply eligibility for all agents
    python -m aigis_agents.mesh.review_memory --stats

    # Show stats for a specific agent
    python -m aigis_agents.mesh.review_memory --stats --agent agent_01

    # Enable auto-apply above a confidence threshold
    python -m aigis_agents.mesh.review_memory --enable-auto-apply agent_01 --threshold 0.85

    # Disable auto-apply
    python -m aigis_agents.mesh.review_memory --disable-auto-apply agent_01
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from typing import Any

from aigis_agents.mesh.memory_manager import MemoryManager
from aigis_agents.mesh.toolkit_registry import ToolkitRegistry

_mm = MemoryManager()

# ── Terminal colour helpers (no external deps) ─────────────────────────────────

_USE_COLOUR = sys.stdout.isatty()

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text

def _bold(t: str)   -> str: return _c(t, "1")
def _green(t: str)  -> str: return _c(t, "32")
def _yellow(t: str) -> str: return _c(t, "33")
def _red(t: str)    -> str: return _c(t, "31")
def _cyan(t: str)   -> str: return _c(t, "36")
def _dim(t: str)    -> str: return _c(t, "2")


# ── Listing ────────────────────────────────────────────────────────────────────

def cmd_list(agent_id: str | None) -> None:
    """Print all pending suggestions, optionally filtered by agent."""
    pending = _mm.get_pending(agent_id)

    if not pending:
        scope = f"agent {agent_id}" if agent_id else "all agents"
        print(_green(f"  No pending suggestions for {scope}."))
        return

    scope_label = f" ({agent_id})" if agent_id else ""
    print(_bold(f"\n  Pending improvement suggestions{scope_label}: {len(pending)}\n"))
    print(f"  {'ID':<14}  {'From':<12}  {'To':<12}  {'Deal':<12}  {'Confidence':>10}  Suggestion")
    print("  " + "─" * 90)

    for s in pending:
        sid        = _cyan(s.get("suggestion_id", "?")[:12])
        from_a     = s.get("from_agent", "?")[:10]
        to_a       = s.get("to_agent",   "?")[:10]
        deal       = (s.get("deal_id") or "—")[:10]
        conf       = s.get("audit_confidence", 0.0)
        conf_str   = _yellow(f"{conf:.0%}") if conf >= 0.7 else _dim(f"{conf:.0%}")
        suggestion = (s.get("suggestion") or "")[:60].replace("\n", " ")
        print(f"  {sid:<14}  {from_a:<12}  {to_a:<12}  {deal:<12}  {conf_str:>10}  {suggestion}")

    print()
    print(_dim("  Run --review <suggestion_id> to review one interactively.\n"))


# ── Interactive review ─────────────────────────────────────────────────────────

def cmd_review(suggestion_id: str) -> None:
    """Interactively review a single pending suggestion."""
    # Find it in the global pending queue
    all_pending = _mm.get_pending()
    match = next((s for s in all_pending if s.get("suggestion_id") == suggestion_id), None)

    if match is None:
        print(_red(f"\n  Suggestion '{suggestion_id}' not found in the pending queue.\n"))
        sys.exit(1)

    _print_suggestion(match)

    print(_bold("\n  Action:"))
    print("    [A] Approve as suggested")
    print("    [M] Approve with modifications")
    print("    [R] Reject")
    print("    [S] Skip (leave pending)")
    print()

    while True:
        choice = input("  Choice [A/M/R/S]: ").strip().upper()
        if choice in ("A", "M", "R", "S"):
            break
        print("  Please enter A, M, R, or S.")

    if choice == "S":
        print(_dim("  Skipped.\n"))
        return

    notes = input("  Review notes (optional, press Enter to skip): ").strip()
    reviewer = input("  Reviewer name (optional, press Enter for 'human'): ").strip() or "human"

    if choice == "A":
        _mm.approve(suggestion_id, reviewed_by=reviewer, notes=notes, modified=False)
        print(_green(f"\n  Approved as suggested. (ID: {suggestion_id})\n"))
    elif choice == "M":
        _mm.approve(suggestion_id, reviewed_by=reviewer, notes=notes, modified=True)
        print(_green(f"\n  Approved with modifications. (ID: {suggestion_id})\n"))
    elif choice == "R":
        _mm.reject(suggestion_id, reviewed_by=reviewer, notes=notes)
        print(_red(f"\n  Rejected. (ID: {suggestion_id})\n"))


def _print_suggestion(s: dict[str, Any]) -> None:
    """Pretty-print a suggestion record."""
    print()
    print("  " + "═" * 70)
    print(f"  {_bold('Suggestion ID:')} {_cyan(s.get('suggestion_id', '?'))}")
    print(f"  {_bold('From Agent:')}    {s.get('from_agent', '?')}")
    print(f"  {_bold('To Agent:')}      {s.get('to_agent', '?')}")
    print(f"  {_bold('Deal ID:')}       {s.get('deal_id') or '—'}")
    print(f"  {_bold('Run ID:')}        {s.get('run_id') or '—'}")
    print(f"  {_bold('Submitted:')}     {s.get('submitted_date', '?')}")
    conf = s.get("audit_confidence", 0.0)
    conf_colour = _yellow if conf >= 0.7 else _red
    print(f"  {_bold('Confidence:')}    {conf_colour(f'{conf:.0%}')}")
    print()
    print(f"  {_bold('Suggestion:')}")
    for line in textwrap.wrap(s.get("suggestion", ""), width=70):
        print(f"    {line}")
    print("  " + "═" * 70)


# ── Stats ──────────────────────────────────────────────────────────────────────

def cmd_stats(agent_id: str | None) -> None:
    """Print approval statistics and auto-apply eligibility."""
    agents = [agent_id] if agent_id else ToolkitRegistry.list_agents()

    print(_bold("\n  Improvement suggestion statistics\n"))
    print(f"  {'Agent':<20}  {'Total':>6}  {'Approved':>9}  {'Modified':>9}  {'Rejected':>8}  {'Pending':>8}  {'Rate':>7}  {'Auto-apply'}")
    print("  " + "─" * 95)

    for aid in agents:
        try:
            stats = _mm.get_approval_stats(aid)
        except Exception:
            continue

        total    = stats.get("total_suggestions", 0)
        approved = stats.get("approved_as_suggested", 0)
        modified = stats.get("approved_with_modifications", 0)
        rejected = stats.get("rejected", 0)
        pending  = stats.get("pending", 0)
        rate     = stats.get("approval_rate", 0.0)

        rate_str  = _green(f"{rate:.0%}") if rate >= 0.8 else _yellow(f"{rate:.0%}") if rate >= 0.6 else _red(f"{rate:.0%}")

        enabled, threshold = _mm.is_auto_apply_enabled(aid)
        if enabled:
            auto_str = _green(f"ON ≥{threshold:.0%}" if threshold else "ON")
        elif _mm.check_auto_apply_eligibility(aid):
            auto_str = _yellow("Eligible")
        else:
            auto_str = _dim("Off")

        print(f"  {aid:<20}  {total:>6}  {approved:>9}  {modified:>9}  {rejected:>8}  {pending:>8}  {rate_str:>7}  {auto_str}")

    print()

    # Highlight eligible agents
    eligible = [a for a in agents if _mm.check_auto_apply_eligibility(a)]
    if eligible:
        print(_yellow("  Auto-apply eligible (approval rate ≥ 80%, ≥ 10 reviews):"))
        for a in eligible:
            stats = _mm.get_approval_stats(a)
            rate  = stats.get("approval_rate", 0.0)
            print(f"    {a}: {rate:.0%} approval rate")
        print()
        print(_dim("  Run --enable-auto-apply <agent_id> --threshold 0.85 to enable.\n"))


# ── Auto-apply management ──────────────────────────────────────────────────────

def cmd_enable_auto_apply(agent_id: str, threshold: float) -> None:
    """Enable auto-apply for an agent above a confidence threshold."""
    if not 0.0 < threshold <= 1.0:
        print(_red("  Threshold must be between 0.01 and 1.00.\n"))
        sys.exit(1)

    # Verify eligibility (warn but don't block)
    if not _mm.check_auto_apply_eligibility(agent_id):
        stats = _mm.get_approval_stats(agent_id)
        rate  = stats.get("approval_rate", 0.0)
        total = stats.get("total_suggestions", 0)
        print(_yellow(
            f"\n  Warning: {agent_id} has not yet reached the eligibility threshold "
            f"({rate:.0%} approval rate, {total} total suggestions).\n"
            f"  Proceeding anyway as instructed.\n"
        ))

    _mm.enable_auto_apply(agent_id, threshold)
    print(_green(f"\n  Auto-apply enabled for {agent_id} at threshold ≥ {threshold:.0%}.\n"))

    print(_dim(
        "  Future improvement suggestions with audit_confidence >= threshold will be\n"
        "  automatically applied and logged with status 'auto_applied'.\n"
        "  Run --disable-auto-apply to revert.\n"
    ))


def cmd_disable_auto_apply(agent_id: str) -> None:
    """Disable auto-apply for an agent."""
    _mm.disable_auto_apply(agent_id)
    print(_green(f"\n  Auto-apply disabled for {agent_id}.\n"))


# ── Arg parsing + dispatch ─────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m aigis_agents.mesh.review_memory",
        description="Review improvement suggestions and manage auto-apply for Aigis agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python -m aigis_agents.mesh.review_memory --list
          python -m aigis_agents.mesh.review_memory --list --agent agent_01
          python -m aigis_agents.mesh.review_memory --review s001abcd
          python -m aigis_agents.mesh.review_memory --stats
          python -m aigis_agents.mesh.review_memory --enable-auto-apply agent_01 --threshold 0.85
          python -m aigis_agents.mesh.review_memory --disable-auto-apply agent_01
        """),
    )

    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--list",   action="store_true", help="List pending suggestions")
    group.add_argument("--review", metavar="SUGGESTION_ID",  help="Review a suggestion interactively")
    group.add_argument("--stats",  action="store_true", help="Show approval statistics")
    group.add_argument("--enable-auto-apply",  metavar="AGENT_ID", help="Enable auto-apply for an agent")
    group.add_argument("--disable-auto-apply", metavar="AGENT_ID", help="Disable auto-apply for an agent")

    p.add_argument("--agent",     metavar="AGENT_ID", help="Filter by agent (used with --list or --stats)")
    p.add_argument("--threshold", type=float, default=0.85,
                   help="Confidence threshold for auto-apply (default: 0.85, used with --enable-auto-apply)")
    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args   = parser.parse_args(argv)

    if args.list:
        cmd_list(args.agent)

    elif args.review:
        cmd_review(args.review)

    elif args.stats:
        cmd_stats(args.agent)

    elif args.enable_auto_apply:
        cmd_enable_auto_apply(args.enable_auto_apply, args.threshold)

    elif args.disable_auto_apply:
        cmd_disable_auto_apply(args.disable_auto_apply)


if __name__ == "__main__":
    main()
