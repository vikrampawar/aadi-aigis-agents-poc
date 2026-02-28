"""
CLI entry point for Agent 02 — VDR Financial & Operational Data Store.

Usage examples:
    # Ingest full VDR
    python -m aigis_agents.agent_02_data_store \\
        --deal-id <uuid> --operation ingest_vdr \\
        --vdr-path /path/to/vdr --deal-type producing_asset --jurisdiction GoM

    # Ingest single file
    python -m aigis_agents.agent_02_data_store \\
        --deal-id <uuid> --operation ingest_file \\
        --file-path /path/to/Financial_Model.xlsx --case-name management_case

    # Natural language query
    python -m aigis_agents.agent_02_data_store \\
        --deal-id <uuid> --operation query \\
        --query "Average oil production 2024"

    # Direct SQL query
    python -m aigis_agents.agent_02_data_store \\
        --deal-id <uuid> --operation query \\
        --sql "SELECT metric_name, value, unit FROM scalar_datapoints WHERE deal_id = ?"

    # Scenario re-run
    python -m aigis_agents.agent_02_data_store \\
        --deal-id <uuid> --operation query --query "NPV10 and IRR" \\
        --scenario '{"oil_price_usd_bbl": 65, "loe_per_boe": 18}'

    # List ingested data summary
    python -m aigis_agents.agent_02_data_store \\
        --deal-id <uuid> --list-data
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m aigis_agents.agent_02_data_store",
        description="Agent 02 — VDR Financial & Operational Data Store",
    )

    # Required
    parser.add_argument("--deal-id", required=False, default=None,
                        help="Deal UUID. Auto-generated if not provided.")

    # Operation mode
    parser.add_argument("--operation", choices=["ingest_vdr", "ingest_file", "query"],
                        default="ingest_vdr")

    # ingest_vdr options
    parser.add_argument("--vdr-path", default=None, help="Root directory of the VDR")
    parser.add_argument("--deal-type", default="producing_asset",
                        choices=["producing_asset", "exploration", "development", "corporate"])
    parser.add_argument("--jurisdiction", default="GoM",
                        choices=["GoM", "UKCS", "Norway", "International"])
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-ingest already-ingested files")
    parser.add_argument("--file-filter", nargs="*", default=None,
                        help="Limit to these document categories")

    # ingest_file options
    parser.add_argument("--file-path", default=None, help="Path to the file to ingest")
    parser.add_argument("--file-type", default=None, choices=["excel", "pdf", "csv"],
                        help="Override auto-detected file type")
    parser.add_argument("--case-name", default=None,
                        help="Case tag for ingested data (e.g., management_case)")
    parser.add_argument("--source-doc-hint", default=None,
                        help="Document type hint (e.g., CPR, LOS, financial_model)")
    parser.add_argument("--sheet-names", nargs="*", default=None,
                        help="Excel sheets to ingest (default: all)")
    parser.add_argument("--no-consistency-check", action="store_true",
                        help="Skip post-ingestion consistency check")

    # query options
    parser.add_argument("--query", default=None, help="Natural language query")
    parser.add_argument("--sql", default=None, help="Direct SQL query")
    parser.add_argument("--data-type", default=None,
                        choices=["production", "financials", "reserves", "costs", "fiscal", "cells"])
    parser.add_argument("--period-start", default=None, help="ISO date filter (YYYY-MM-DD)")
    parser.add_argument("--period-end", default=None, help="ISO date filter (YYYY-MM-DD)")
    parser.add_argument("--scenario", default=None,
                        help="JSON dict of assumption overrides for scenario re-evaluation")
    parser.add_argument("--no-metadata", action="store_true",
                        help="Exclude source/confidence metadata from query results")

    # General options
    parser.add_argument("--output-dir", default="./outputs", help="Output directory")
    parser.add_argument("--main-model", default=None, help="Override main LLM model")
    parser.add_argument("--list-data", action="store_true",
                        help="Show data summary for the deal (shorthand for --operation query)")
    parser.add_argument("--sync-db", action="store_true",
                        help="Sync SQLite to PostgreSQL after operation")
    parser.add_argument("--pg-dsn", default=None, help="PostgreSQL connection string")
    parser.add_argument("--format", default="table", choices=["table", "json"],
                        help="Output format for query results")

    args = parser.parse_args()

    deal_id = args.deal_id or str(uuid.uuid4())

    # Build inputs dict for Agent02.invoke()
    inputs: dict = {
        "operation":             args.operation,
        "deal_type":             args.deal_type,
        "jurisdiction":          args.jurisdiction,
        "vdr_path":              args.vdr_path,
        "overwrite":             args.overwrite,
        "file_filter":           args.file_filter,
        "file_path":             args.file_path,
        "file_type":             args.file_type,
        "case_name":             args.case_name,
        "source_doc_hint":       args.source_doc_hint,
        "sheet_names":           args.sheet_names,
        "run_consistency_check": not args.no_consistency_check,
        "query_text":            args.query,
        "query_sql":             args.sql,
        "data_type":             args.data_type,
        "period_start":          args.period_start,
        "period_end":            args.period_end,
        "include_metadata":      not args.no_metadata,
        "scenario":              json.loads(args.scenario) if args.scenario else None,
        "pg_sync":               args.sync_db,
        "pg_dsn":                args.pg_dsn,
    }

    # --list-data shorthand
    if args.list_data:
        inputs["operation"] = "query"
        inputs["query_text"] = "Summarise all ingested data for this deal"

    from aigis_agents.agent_02_data_store.agent import Agent02

    agent = Agent02()
    result = agent.invoke(
        mode="standalone",
        deal_id=deal_id,
        main_model=args.main_model,
        output_dir=args.output_dir,
        **inputs,
    )

    # Print output
    if args.format == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        _print_table(result, args.operation)

    # Exit with error code if agent reported errors
    if result.get("status") == "error":
        sys.exit(1)


def _print_table(result: dict, operation: str) -> None:
    """Pretty-print result in a human-friendly format."""
    data = result.get("data", result)
    status = result.get("status", "unknown")

    print(f"\n{'='*60}")
    print(f"  Agent 02 — {operation}")
    print(f"  Deal ID : {result.get('deal_id', '?')}")
    print(f"  Status  : {status}")
    print(f"{'='*60}")

    if status == "error":
        print(f"\n[ERROR] {result.get('message', '')}")
        return

    if isinstance(data, dict):
        for k, v in data.items():
            if k in ("errors", "output_paths"):
                continue
            if isinstance(v, (list, dict)):
                print(f"  {k}: {json.dumps(v, default=str)[:120]}")
            else:
                print(f"  {k}: {v}")

        # Print query data as a simple table
        rows = data.get("data", [])
        if rows and isinstance(rows, list) and isinstance(rows[0], dict):
            cols = list(rows[0].keys())
            col_widths = [max(len(str(r.get(c, ""))) for r in rows + [{}]) for c in cols]
            col_widths = [max(w, len(c)) for w, c in zip(col_widths, cols)]
            header = " | ".join(c.ljust(w) for c, w in zip(cols, col_widths))
            print("\n" + header)
            print("-" * len(header))
            for row in rows[:50]:
                print(" | ".join(str(row.get(c, "")).ljust(w) for c, w in zip(cols, col_widths)))
            if len(rows) > 50:
                print(f"... ({len(rows) - 50} more rows)")

        # Print errors
        errors = data.get("errors", [])
        if errors:
            print("\n[Errors]")
            for e in errors[:10]:
                print(f"  - {e}")

    print()


if __name__ == "__main__":
    main()
