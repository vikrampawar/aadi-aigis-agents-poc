"""
Optional PostgreSQL sync for Agent 02 — VDR Financial & Operational Data Store.

Syncs the per-deal SQLite DB to the shared PostgreSQL instance
(schema: deal_{deal_id_short}) for cross-deal analytics.

Only runs when pg_sync=True is explicitly passed or --sync-db CLI flag is used.
"""

from __future__ import annotations

import sqlite3
from typing import Any


# Tables to sync (in dependency order)
_SYNC_TABLES = [
    "deals",
    "source_documents",
    "cases",
    "production_series",
    "reserve_estimates",
    "financial_series",
    "cost_benchmarks",
    "fiscal_terms",
    "scalar_datapoints",
    "excel_cells",
    "excel_sheets",
    "data_conflicts",
    "scenario_runs",
    "ingestion_log",
]

# Default PostgreSQL connection string (localhost dev)
DEFAULT_PG_DSN = "postgresql://aigis:aigis@localhost:5433/aigis"


# ── Public API ─────────────────────────────────────────────────────────────────

def sync_to_postgres(
    sqlite_conn: sqlite3.Connection,
    deal_id: str,
    pg_dsn: str = DEFAULT_PG_DSN,
    tables: list[str] | None = None,
) -> dict[str, Any]:
    """
    Sync all deal data from SQLite → PostgreSQL.

    Args:
        sqlite_conn: Open SQLite connection with the deal data.
        deal_id:     Deal UUID (used to construct PG schema name).
        pg_dsn:      PostgreSQL DSN string.
        tables:      Specific tables to sync (default: all _SYNC_TABLES).

    Returns:
        {"synced_tables": [...], "rows_synced": N, "errors": [...]}
    """
    result: dict[str, Any] = {"synced_tables": [], "rows_synced": 0, "errors": []}
    target_tables = tables or _SYNC_TABLES
    schema = _schema_name(deal_id)

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        result["errors"].append("psycopg2 not installed — run: pip install psycopg2-binary")
        return result

    try:
        pg_conn = psycopg2.connect(pg_dsn)
        pg_conn.autocommit = False
    except Exception as e:
        result["errors"].append(f"PostgreSQL connection failed: {e}")
        return result

    try:
        with pg_conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

        for table in target_tables:
            try:
                rows_synced = _sync_table(sqlite_conn, pg_conn, schema, table, deal_id)
                result["synced_tables"].append(table)
                result["rows_synced"] += rows_synced
            except Exception as e:
                result["errors"].append(f"Table {table}: {e}")

        pg_conn.commit()
    except Exception as e:
        pg_conn.rollback()
        result["errors"].append(f"Sync failed: {e}")
    finally:
        pg_conn.close()

    return result


# ── Per-table sync ─────────────────────────────────────────────────────────────

def _sync_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn: Any,
    schema: str,
    table: str,
    deal_id: str,
) -> int:
    """Sync one table from SQLite → PostgreSQL using UPSERT."""
    import psycopg2.extras

    # Read from SQLite
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table} WHERE deal_id = ? LIMIT 100000", (deal_id,))
    col_names = [d[0] for d in cursor.description]
    rows = cursor.fetchall()

    if not rows:
        return 0

    # Ensure table exists in PostgreSQL
    _ensure_pg_table(pg_conn, schema, table, col_names)

    # UPSERT into PostgreSQL
    qualified = f"{schema}.{table}"
    cols_str  = ", ".join(col_names)
    vals_tmpl = ", ".join(["%s"] * len(col_names))
    conflict_col = "id"  # all tables have an id PK

    upsert_sql = (
        f"INSERT INTO {qualified} ({cols_str}) VALUES ({vals_tmpl}) "
        f"ON CONFLICT ({conflict_col}) DO UPDATE SET "
        + ", ".join(f"{c} = EXCLUDED.{c}" for c in col_names if c != conflict_col)
    )

    with pg_conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, upsert_sql, rows, page_size=500)

    return len(rows)


def _ensure_pg_table(pg_conn: Any, schema: str, table: str, col_names: list[str]) -> None:
    """
    Create the table in PostgreSQL if it does not exist.
    Uses TEXT for all columns as a safe universal fallback — PG can cast on read.
    """
    cols_ddl = ",\n  ".join(f"{col} TEXT" for col in col_names)
    qualified = f"{schema}.{table}"
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {qualified} (
      {cols_ddl},
      PRIMARY KEY (id)
    );
    """
    with pg_conn.cursor() as cur:
        cur.execute(ddl)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _schema_name(deal_id: str) -> str:
    """Return a safe PG schema name for a deal ID."""
    short = deal_id.replace("-", "")[:16]
    return f"deal_{short}"
