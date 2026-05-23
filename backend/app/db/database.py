# SQLite connection management and table creation for facts, claims, reports, chat_history
import sqlite3
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "pulselens.db"


async def get_db():
    pass


async def create_tables():
    pass
