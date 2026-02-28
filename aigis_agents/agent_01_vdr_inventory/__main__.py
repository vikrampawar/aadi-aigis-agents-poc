"""
CLI entry point for Agent 01.

Usage:
  python -m aigis_agents.agent_01_vdr_inventory --help
  python -m aigis_agents.agent_01_vdr_inventory \\
    --deal-id 00000000-0000-0000-0000-c005a1000001 \\
    --deal-type producing_asset \\
    --jurisdiction GoM \\
    --vdr-path /path/to/corsair_vdr \\
    --output-dir ./outputs \\
    --deal-name "Project Corsair" \\
    --buyer "Aigis Analytics"

  # Show all deals in the registry:
  python -m aigis_agents.agent_01_vdr_inventory --list-deals --output-dir ./outputs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(force_terminal=True, highlight=False)


def _show_registry(output_dir: str) -> None:
    """Display the deal registry as a Rich table and exit."""
    from aigis_agents.agent_01_vdr_inventory.deal_registry import load_registry

    registry = load_registry(Path(output_dir))

    if not registry.deals:
        console.print(
            "\n[bold blue]Aigis Agent 01 — Deal Registry[/bold blue]\n"
            "[yellow]No deals recorded yet. Run the agent on a VDR to populate the registry.[/yellow]\n"
            f"Registry path: [dim]{Path(output_dir) / 'deals_registry.json'}[/dim]\n"
        )
        return

    table = Table(
        title=f"Aigis Agent 01 — Deal Registry  ({len(registry.deals)} deal(s) · {registry.agent_stats.total_runs} run(s))",
        border_style="blue",
        show_lines=False,
    )
    table.add_column("Deal Name", style="bold cyan", min_width=18)
    table.add_column("Type", style="dim")
    table.add_column("Jur.", style="dim", justify="center")
    table.add_column("Runs", justify="right")
    table.add_column("Last Run", justify="center")
    table.add_column("NTH  P / P / M", justify="center", style="bold")

    for deal in registry.deals:
        last_run = deal.runs[-1] if deal.runs else None
        nth_str = (
            f"{last_run.nth_present} / {last_run.nth_partial} / {last_run.nth_missing}"
            if last_run else "—"
        )
        # Colour the NTH score by severity
        if last_run and last_run.nth_missing > 0:
            nth_str = f"[red]{nth_str}[/red]"
        elif last_run and last_run.nth_partial > 0:
            nth_str = f"[yellow]{nth_str}[/yellow]"
        else:
            nth_str = f"[green]{nth_str}[/green]"

        table.add_row(
            deal.deal_name,
            deal.deal_type,
            deal.jurisdiction,
            str(deal.run_count),
            deal.last_run_timestamp[:10],
            nth_str,
        )

    console.print()
    console.print(table)

    stats = registry.agent_stats
    since = stats.first_run_timestamp[:10] if stats.first_run_timestamp else "—"
    console.print(
        f"\n[bold]Agent Experience:[/bold]  "
        f"{stats.total_deals} deal(s) reviewed  ·  "
        f"{stats.total_files_reviewed:,} files processed  ·  "
        f"{stats.total_runs} run(s) total  ·  "
        f"Since: {since}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aigis Agent 01 — VDR Document Inventory & Gap Analyst",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--deal-id",      default=None,   help="Unique deal identifier")
    parser.add_argument("--deal-type",    default=None,
                        choices=["producing_asset", "exploration", "development", "corporate"],
                        help="Transaction type")
    parser.add_argument("--jurisdiction", default=None,
                        choices=["GoM", "UKCS", "Norway", "International"],
                        help="Asset jurisdiction")
    parser.add_argument("--vdr-path",     default=None,   help="Path to local VDR folder")
    parser.add_argument("--vdr-csv",      default=None,   help="Path to VDR platform export CSV/XLSX")
    parser.add_argument("--use-db",       action="store_true", default=True,
                        help="Query aigis-poc PostgreSQL DB (default: True)")
    parser.add_argument("--no-db",        action="store_true",
                        help="Disable DB query")
    parser.add_argument("--model",        default="gpt-4o-mini", help="LLM model key")
    parser.add_argument("--output-dir",   default=".", help="Output directory")
    parser.add_argument("--checklist",    default="v1.0", help="Checklist version")
    parser.add_argument("--deal-name",    default=None, help="Deal name for report headers")
    parser.add_argument("--buyer",        default=None, help="Buyer name for DRL cover")
    parser.add_argument("--round",        type=int, default=1, help="DRL round number")
    parser.add_argument("--list-deals",   action="store_true",
                        help="Show all deals in the registry and exit (no run performed)")
    args = parser.parse_args()

    # ── Registry view — no run needed ────────────────────────────────────────
    if args.list_deals:
        _show_registry(args.output_dir)
        sys.exit(0)

    # ── Validate required args for a normal run ───────────────────────────────
    missing = [f for f, v in [("--deal-id", args.deal_id), ("--deal-type", args.deal_type),
                               ("--jurisdiction", args.jurisdiction)] if v is None]
    if missing:
        parser.error(f"{', '.join(missing)} are required for a normal run (or use --list-deals).")

    if not args.vdr_path and not args.vdr_csv and (args.no_db or not args.use_db):
        console.print("[red]Error: at least one of --vdr-path, --vdr-csv, or --use-db is required.[/red]")
        sys.exit(1)

    console.print(Panel(
        f"[bold blue]Aigis Agent 01 — VDR Document Inventory & Gap Analyst[/bold blue]\n\n"
        f"Deal:         {args.deal_name or args.deal_id}\n"
        f"Deal Type:    {args.deal_type}\n"
        f"Jurisdiction: {args.jurisdiction}\n"
        f"VDR Path:     {args.vdr_path or 'N/A'}\n"
        f"VDR CSV:      {args.vdr_csv or 'N/A'}\n"
        f"Use DB:       {not args.no_db}\n"
        f"Model:        {args.model}\n"
        f"Checklist:    {args.checklist}\n"
        f"Output Dir:   {args.output_dir}",
        title="Aigis Analytics",
        border_style="blue",
    ))

    from aigis_agents.agent_01_vdr_inventory.agent import vdr_inventory_agent

    with console.status("[bold green]Running VDR inventory and gap analysis...[/bold green]"):
        result = vdr_inventory_agent(
            deal_id=args.deal_id,
            deal_type=args.deal_type,
            jurisdiction=args.jurisdiction,
            vdr_path=args.vdr_path,
            vdr_export_csv=args.vdr_csv,
            use_db=not args.no_db,
            model_key=args.model,
            output_dir=args.output_dir,
            checklist_version=args.checklist,
            deal_name=args.deal_name,
            buyer_name=args.buyer,
            round_number=args.round,
        )

    if result["status"] == "error":
        console.print(f"\n[red bold]Error:[/red bold] {result.get('error', 'Unknown error')}")
        sys.exit(1)

    # ── Gap Delta Summary (re-runs only) ─────────────────────────────────────
    gap_delta = result.get("gap_delta")
    if gap_delta:
        filled = len(gap_delta.get("gaps_filled", []))
        opened = len(gap_delta.get("gaps_opened", []))
        outstanding = len(gap_delta.get("still_missing_nth", [])) + len(gap_delta.get("still_partial_nth", []))
        days = gap_delta.get("days_between_runs", 0)
        console.print(
            f"\n[bold cyan]Gap Tracker[/bold cyan] (vs run {days} day(s) ago):  "
            f"[green]{filled} filled[/green]  |  "
            f"[red]{opened} regression(s)[/red]  |  "
            f"[yellow]{outstanding} NTH still outstanding[/yellow]"
        )

    # ── Results Summary ──────────────────────────────────────────────────────
    findings = result.get("findings") or {}
    s_nth_miss = findings.get("missing_nth", 0)
    s_nth_part = findings.get("partial_nth", 0)
    s_gth_miss = findings.get("missing_gth", 0)

    table = Table(title="Gap Analysis Results", border_style="blue")
    table.add_column("Tier", style="bold")
    table.add_column("[OK] Present", style="green")
    table.add_column("[~~] Partial", style="yellow")
    table.add_column("[!!] Missing", style="red")

    table.add_row(
        "Need to Have",
        str(findings.get("present_nth", 0)),
        str(findings.get("partial_nth", 0)),
        str(findings.get("missing_nth", 0)),
    )
    table.add_row(
        "Good to Have",
        str(findings.get("present_gth", 0)),
        str(findings.get("partial_gth", 0)),
        str(findings.get("missing_gth", 0)),
    )
    console.print(table)

    # Status callout
    if s_nth_miss > 0:
        console.print(f"\n[red bold][!!] {s_nth_miss} critical (Need to Have) document(s) MISSING[/red bold]")
    elif s_nth_part > 0:
        console.print(f"\n[yellow bold][~~] {s_nth_part} Need-to-Have item(s) partially covered -- follow up required[/yellow bold]")
    else:
        console.print("\n[green bold][OK] All Need-to-Have items present[/green bold]")

    novel_count = findings.get("novel_count", 0)
    if novel_count > 0:
        console.print(
            f"[cyan][*] {novel_count} novel document pattern(s) proposed for checklist addition.[/cyan]\n"
            f"   Review with: python -m aigis_agents.agent_01_vdr_inventory.accept_proposals"
        )

    # Output paths
    outputs = result.get("outputs", {})
    console.print("\n[bold]Output Files:[/bold]")
    console.print(f"  Inventory JSON:    {outputs.get('inventory_json', 'N/A')}")
    console.print(f"  Gap Report (MD):   {outputs.get('gap_report_md', 'N/A')}")
    console.print(f"  Data Request List: {outputs.get('drl_docx', 'N/A')}")

    cost = result.get("cost_usd", 0.0)
    if cost > 0:
        console.print(f"\n[dim]LLM cost: ~${cost:.4f}[/dim]")


if __name__ == "__main__":
    main()
