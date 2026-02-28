"""DB bridge — provides connection string for aigis-poc PostgreSQL."""

from __future__ import annotations

import os


def get_connection_string() -> str:
    """Build PostgreSQL connection string from environment variables."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5433")
    db   = os.environ.get("POSTGRES_DB", "aigis")
    user = os.environ.get("POSTGRES_USER", "aigis")
    pw   = os.environ.get("POSTGRES_PASSWORD", "aigis")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"
