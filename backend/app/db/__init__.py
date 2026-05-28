# Database package — selects SQLite or Postgres adapter based on DATABASE_BACKEND env var
from __future__ import annotations

import os

from app.db.adapter import DatabaseAdapter


def _build_adapter() -> DatabaseAdapter:
    backend = os.getenv("DATABASE_BACKEND", "sqlite").lower()
    if backend == "postgres":
        from app.db.postgres_adapter import PostgresAdapter
        dsn = os.environ["DATABASE_URL"]
        return PostgresAdapter(dsn)
    from app.db.sqlite_adapter import SQLiteAdapter
    return SQLiteAdapter()


db_adapter: DatabaseAdapter = _build_adapter()

