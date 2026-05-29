# Database package — selects SQLite or Postgres adapter based on DATABASE_BACKEND env var
from __future__ import annotations

import logging
import os

from app.db.adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


def _build_adapter() -> DatabaseAdapter:
    backend = os.getenv("DATABASE_BACKEND", "sqlite").lower()
    logger.info("db_adapter: building adapter for backend=%s", backend)
    if backend == "postgres":
        db_url_present = bool(os.getenv("DATABASE_URL"))
        logger.info("db_adapter: DATABASE_URL present=%s", str(db_url_present).lower())
        from app.db.postgres_adapter import PostgresAdapter
        dsn = os.environ["DATABASE_URL"]
        logger.info("db_adapter: PostgresAdapter created (host masked)")
        return PostgresAdapter(dsn)
    logger.info("db_adapter: SQLiteAdapter created")
    from app.db.sqlite_adapter import SQLiteAdapter
    return SQLiteAdapter()


db_adapter: DatabaseAdapter = _build_adapter()
