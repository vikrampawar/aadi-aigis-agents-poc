"""
CLI tool for reviewing and accepting/rejecting self-learning checklist proposals.

Usage:
  python -m aigis_agents.agent_01_vdr_inventory.accept_proposals
  python -m aigis_agents.agent_01_vdr_inventory.accept_proposals --checklist v1.0
  python -m aigis_agents.agent_01_vdr_inventory.accept_proposals --accept-all
  python -m aigis_agents.agent_01_vdr_inventory.accept_proposals --reject-all
"""

from __future__ import annotations

import argparse
import sys

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt

from aigis_agents.agent_01_vdr_inventory.checklist_manager import (
    PENDING_PATH,
    finalise_accepted_proposals,
    load_pending_proposals,
)
from aigis_agents.agent_01_vdr_inventory.models import ChecklistProposal

console = Console()


def _display_proposal(p: ChecklistProposal, index: int, total: int) -> None:
    """Pretty-print a single proposal for review."""
    examples = "\n  ".join(p.filenames[:5])
    content = (
        f"[bold cyan]Proposal {index}/{total}[/bold cyan]\n\n"
        f"[bold]Suggested Category:[/bold]  {p.suggested_category}\n"
        f"[bold]Suggested Item:[/bold]     {p.suggested_item_description}\n"
        f"[bold]Tier:[/bold]               [yellow]{p.suggested_tier.value}[/yellow]\n"
        f"[bold]Deal Types:[/bold]         {', '.join(dt.value for dt in p.applicable_deal_types)}\n"
        f"[bold]From Deal:[/bold]          {p.deal_id}\n"
        f"[bold]Run Date:[/bold]           {p.run_timestamp[:10]}\n\n"
        f"[bold]File Examples:[/bold]\n  {examples}\n\n"
        f"[bold]Folder:[/bold]             {p.folder_path or '(root)'}\n\n"
        f"[bold]Reasoning:[/bold]\n  {p.reasoning}"
    )
    console.print(Panel(content, title="📋 Checklist Evolution Proposal", border_style="blue"))


def interactive_review(pending: list[ChecklistProposal], checklist_version: str) -> tuple[list[str], list[str]]:
    """Interactive Y/N review of pending proposals. Returns (accepted_ids, rejected_ids)."""
    accepted_ids: list[str] = []
    rejected_ids: list[str] = []

    console.print(f"\n[bold blue]Aigis Checklist Evolution Review[/bold blue]")
    console.print(f"Found [yellow]{len(pending)}[/yellow] pending proposal(s) for checklist [cyan]{checklist_version}[/cyan]\n")

    for i, p in enumerate(pending, 1):
        _display_proposal(p, i, len(pending))
        decision = Confirm.ask(
            f"  [bold]Add '{p.suggested_item_description}' to the gold-standard checklist?[/bold]",
            default=False,
        )
        if decision:
            accepted_ids.append(p.proposal_id)
            console.print(f"  [green]✅ Accepted — will be added to {checklist_version}[/green]\n")
        else:
            rejected_ids.append(p.proposal_id)
            console.print(f"  [red]❌ Rejected — archived to rejected_proposals.json[/red]\n")

    return accepted_ids, rejected_ids


def summary_table(accepted: list[str], rejected: list[str], new_version: str) -> None:
    """Print a summary table after review."""
    table = Table(title="Review Summary", border_style="blue")
    table.add_column("Outcome", style="bold")
    table.add_column("Count")
    table.add_row("[green]Accepted[/green]", str(len(accepted)))
    table.add_row("[red]Rejected[/red]", str(len(rejected)))
    console.print(table)
    if accepted:
        console.print(
            f"\n[green bold]✅ Checklist updated to version [cyan]{new_version}[/cyan][/green bold]\n"
            f"New items will be active on next run of vdr_inventory_agent().\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review and accept/reject Aigis self-learning checklist proposals"
    )
    parser.add_argument(
        "--checklist", default="v1.0", help="Checklist version to update (default: v1.0)"
    )
    parser.add_argument(
        "--accept-all", action="store_true", help="Accept all pending proposals without prompting"
    )
    parser.add_argument(
        "--reject-all", action="store_true", help="Reject all pending proposals without prompting"
    )
    args = parser.parse_args()

    pending = load_pending_proposals()

    if not pending:
        console.print(
            f"\n[bold blue]No pending proposals found.[/bold blue]\n"
            f"Proposals accumulate at: [cyan]{PENDING_PATH}[/cyan]\n"
            "Run vdr_inventory_agent() on a new VDR to generate proposals.\n"
        )
        sys.exit(0)

    if args.accept_all:
        accepted_ids = [p.proposal_id for p in pending]
        rejected_ids = []
        console.print(f"[yellow]--accept-all: accepting all {len(accepted_ids)} proposals[/yellow]")
    elif args.reject_all:
        accepted_ids = []
        rejected_ids = [p.proposal_id for p in pending]
        console.print(f"[yellow]--reject-all: rejecting all {len(rejected_ids)} proposals[/yellow]")
    else:
        accepted_ids, rejected_ids = interactive_review(pending, args.checklist)

    if accepted_ids:
        new_version = finalise_accepted_proposals(accepted_ids, current_version=args.checklist)
    else:
        new_version = args.checklist
        # Still mark rejected ones
        from aigis_agents.agent_01_vdr_inventory.checklist_manager import reject_proposal
        to_reject = [p for p in pending if p.proposal_id in rejected_ids]
        for p in to_reject:
            reject_proposal(p)

    summary_table(accepted_ids, rejected_ids, new_version)


if __name__ == "__main__":
    main()
