"""
CLI entry point for Agent 04 — Upstream Finance Calculator.

Usage:
    # Full analysis
    PYTHONUTF8=1 python -m aigis_agents.agent_04_finance_calculator \\
        --inputs-json ./inputs/example_producing_asset_gom.json \\
        --output-dir ./outputs

    # Single metric mode
    PYTHONUTF8=1 python -m aigis_agents.agent_04_finance_calculator \\
        --inputs-json ./inputs/example.json --metric npv_10 --output-dir ./outputs

    # List all deals in registry
    PYTHONUTF8=1 python -m aigis_agents.agent_04_finance_calculator \\
        --list-deals --output-dir ./outputs

    # List available metric names
    PYTHONUTF8=1 python -m aigis_agents.agent_04_finance_calculator --list-metrics
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def _show_registry(output_dir: str) -> None:
    """Display the deal registry as a Rich table."""
    from aigis_agents.agent_04_finance_calculator.deal_registry import load_registry

    registry = load_registry(Path(output_dir))

    if not registry.deals:
        console.print("[yellow]No deals in registry yet. Run a full analysis first.[/yellow]")
        return

    table = Table(
        title="[bold cyan]Agent 04 — Finance Calculator[/bold cyan]",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Deal Name", style="bold white", min_width=16)
    table.add_column("Type", style="dim")
    table.add_column("Jur.", style="dim")
    table.add_column("NPV@10%", justify="right", style="green")
    table.add_column("IRR", justify="right", style="green")
    table.add_column("LOE/boe", justify="right")
    table.add_column("Cash BE", justify="right")
    table.add_column("Runs", justify="right", style="dim")
    table.add_column("Last Run", style="dim")

    for deal in registry.deals:
        latest = deal.runs[-1] if deal.runs else None
        m = latest.headline_metrics if latest else None

        def fmt_m(v, scale=1e6, unit="M", decimals=1):
            if v is None:
                return "—"
            return f"${v/scale:.{decimals}f}{unit}"

        def fmt_pct(v):
            return f"{v:.1f}%" if v is not None else "—"

        def fmt_boe(v):
            return f"${v:.1f}/boe" if v is not None else "—"

        last_run_date = deal.last_run_timestamp[:10] if deal.last_run_timestamp else "—"
        table.add_row(
            deal.deal_name,
            deal.deal_type,
            deal.jurisdiction,
            fmt_m(m.npv_10_usd if m else None),
            fmt_pct(m.irr_pct if m else None),
            fmt_boe(m.loe_per_boe if m else None),
            f"${m.cash_breakeven_usd_bbl:.1f}/bbl" if (m and m.cash_breakeven_usd_bbl) else "—",
            str(deal.run_count),
            last_run_date,
        )

    console.print(table)
    s = registry.agent_stats
    console.print(
        f"\n[dim]Agent Experience: {s.total_deals} deal(s) · "
        f"{s.total_runs} run(s) total"
        + (f" · Since: {s.first_run_timestamp[:10]}" if s.first_run_timestamp else "")
        + "[/dim]"
    )


def _show_metrics() -> None:
    """Display all available metric names."""
    from aigis_agents.agent_04_finance_calculator.calculator import METRIC_REGISTRY

    table = Table(
        title="[bold cyan]Agent 04 — Available Metrics[/bold cyan]",
        box=box.ROUNDED,
    )
    table.add_column("Metric Key", style="bold green", min_width=24)
    table.add_column("Description")

    for key, desc in sorted(METRIC_REGISTRY.items()):
        table.add_row(key, desc)

    console.print(table)
    console.print(
        "\n[dim]Use with --metric <key> for single-metric output mode.[/dim]"
    )


def _print_result_summary(result) -> None:
    """Print a summary of the analysis to console."""
    from rich.panel import Panel

    s = result.summary

    def _line(label: str, value) -> str:
        return f"  [bold]{label:<30}[/bold] {value}"

    lines = [
        _line("NPV @ 10%:", f"${(s.npv_10_usd or 0)/1e6:.1f}M" if s.npv_10_usd is not None else "N/A"),
        _line("IRR:", f"{s.irr_pct:.1f}%" if s.irr_pct is not None else "N/A"),
        _line("Payback Period:", f"{s.payback_years:.1f} years" if s.payback_years is not None else "N/A"),
        _line("MOIC:", f"{s.moic:.2f}×" if s.moic is not None else "N/A"),
        _line("Lifting Cost (LOE):", f"${s.loe_per_boe:.1f}/boe" if s.loe_per_boe is not None else "N/A"),
        _line("Netback:", f"${s.netback_usd_bbl:.1f}/bbl" if s.netback_usd_bbl is not None else "N/A"),
        _line("Cash Breakeven:", f"${s.cash_breakeven_usd_bbl:.1f}/bbl" if s.cash_breakeven_usd_bbl is not None else "N/A"),
    ]
    if s.full_cycle_breakeven_usd_bbl:
        lines.append(_line("Full-Cycle Breakeven:", f"${s.full_cycle_breakeven_usd_bbl:.1f}/bbl"))
    if s.ev_2p_usd_boe:
        lines.append(_line("EV/2P:", f"${s.ev_2p_usd_boe:.1f}/boe"))
    if s.government_take_pct:
        lines.append(_line("Government Take:", f"{s.government_take_pct:.1f}%"))
    if s.eur_mmboe:
        lines.append(_line("EUR:", f"{s.eur_mmboe:.2f} mmboe"))

    content = "\n".join(lines)

    # Flags
    if result.flags:
        flag_lines = []
        for flag in result.flags:
            flag_lines.append(f"  {flag.severity} {flag.message}")
        content += "\n\n[bold]Quality Flags:[/bold]\n" + "\n".join(flag_lines)

    console.print(Panel(
        content,
        title=f"[bold cyan]{result.deal_name} — Financial Analysis[/bold cyan]",
        border_style="cyan",
        expand=False,
    ))

    # Output paths
    if result.outputs:
        console.print("\n[bold]Output files:[/bold]")
        for name, path in result.outputs.items():
            console.print(f"  [green]✓[/green] {name}: [dim]{path}[/dim]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agent 04 — Upstream Finance Calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--inputs-json",
        metavar="PATH",
        help="Path to JSON file with FinancialInputs (see inputs/example_producing_asset_gom.json)",
    )
    parser.add_argument(
        "--metric",
        metavar="KEY",
        help="Compute a single metric only (use --list-metrics to see keys)",
    )
    parser.add_argument(
        "--output-dir",
        default="./outputs",
        metavar="DIR",
        help="Root output directory (default: ./outputs)",
    )
    parser.add_argument(
        "--list-deals",
        action="store_true",
        help="Show all deals in the registry and exit",
    )
    parser.add_argument(
        "--list-metrics",
        action="store_true",
        help="Show all available metric keys and exit",
    )
    parser.add_argument(
        "--no-sensitivity",
        action="store_true",
        help="Skip sensitivity analysis (faster for single-metric testing)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model key (reserved for future use; no LLM cost in Sprint 1)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # ── --list-deals ──────────────────────────────────────────────────────────
    if args.list_deals:
        _show_registry(args.output_dir)
        sys.exit(0)

    # ── --list-metrics ────────────────────────────────────────────────────────
    if args.list_metrics:
        _show_metrics()
        sys.exit(0)

    # ── Require --inputs-json for all other modes ─────────────────────────────
    if not args.inputs_json:
        parser.error("--inputs-json is required (unless --list-deals or --list-metrics)")

    inputs_path = Path(args.inputs_json)
    if not inputs_path.exists():
        console.print(f"[red]Error: inputs file not found: {inputs_path}[/red]")
        sys.exit(1)

    # ── Single metric mode ────────────────────────────────────────────────────
    if args.metric:
        from aigis_agents.agent_04_finance_calculator.agent import compute_single_metric

        console.print(f"[dim]Computing metric: {args.metric} ...[/dim]")
        result = compute_single_metric(args.metric, inputs_path, args.output_dir)

        table = Table(box=box.SIMPLE)
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        table.add_column("Unit")
        table.add_column("Confidence")
        val = f"{result.metric_result:,.4g}" if result.metric_result is not None else "N/A"
        if result.error:
            val = f"Error: {result.error}"
        table.add_row(result.metric_name, val, result.unit, result.confidence.value)
        console.print(table)

        if result.workings:
            console.print("\n[bold]Workings:[/bold]")
            for w in result.workings:
                console.print(f"  {w}")
        if result.caveats:
            console.print("\n[dim]Caveats:[/dim]")
            for c in result.caveats:
                console.print(f"  [dim]- {c}[/dim]")
        sys.exit(0)

    # ── Full analysis mode ────────────────────────────────────────────────────
    from aigis_agents.agent_04_finance_calculator.agent import finance_calculator_agent

    console.print(f"[bold cyan]Agent 04 — Finance Calculator[/bold cyan]")
    console.print(f"[dim]Inputs: {inputs_path}[/dim]")
    console.print(f"[dim]Output: {args.output_dir}[/dim]")
    console.print()

    result = finance_calculator_agent(
        inputs=inputs_path,
        output_dir=args.output_dir,
        model_key=args.model,
        run_sensitivity_analysis=not args.no_sensitivity,
    )

    if result.status == "error":
        console.print(f"[red]Error: {result.error_message}[/red]")
        sys.exit(1)

    _print_result_summary(result)

    if result.status == "partial":
        console.print(f"\n[yellow]Warning: partial result — {result.error_message}[/yellow]")
        sys.exit(2)


if __name__ == "__main__":
    main()
