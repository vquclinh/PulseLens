# SQLite connection management and table creation for facts, claims, reports, chat_history
from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sqlite3

from app.schemas.models import FactObject, MarketPulseReport

DB_PATH = Path(__file__).parent.parent.parent / "data" / "pulselens.db"


async def get_db() -> AsyncIterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    try:
        db.row_factory = sqlite3.Row
        yield db
    finally:
        db.close()


async def create_tables() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS facts (
                fact_id TEXT PRIMARY KEY,
                report_id TEXT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        db.commit()


async def save_report(report: MarketPulseReport, facts: list[FactObject] | None = None) -> None:
    """Persist a complete report and its fact payloads for later API/chat lookup."""
    await create_tables()
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            INSERT OR REPLACE INTO reports (report_id, payload)
            VALUES (?, ?)
            """,
            (report.report_id, report.model_dump_json()),
        )
        for fact in facts or []:
            db.execute(
                """
                INSERT OR REPLACE INTO facts (fact_id, report_id, payload)
                VALUES (?, ?, ?)
                """,
                (fact.fact_id, report.report_id, fact.model_dump_json()),
            )
        db.commit()


async def load_report(report_id: str) -> MarketPulseReport | None:
    await create_tables()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cursor = db.execute("SELECT payload FROM reports WHERE report_id = ?", (report_id,))
        row = cursor.fetchone()
    if row is None:
        return None
    return MarketPulseReport.model_validate_json(row["payload"])
