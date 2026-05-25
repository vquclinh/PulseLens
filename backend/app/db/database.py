# SQLite connection management and table creation for facts, claims, reports, chat_history
from __future__ import annotations

from collections.abc import AsyncIterator
import json
import logging
from pathlib import Path
import sqlite3

from app.schemas.models import CompanyNarrative, FactObject, MarketPulseReport, VerifiedClaim
from app.utils.embeddings import cosine_similarity, embed_texts, lexical_score

logger = logging.getLogger(__name__)

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
                embedding TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
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
        _ensure_column(db, "facts", "embedding", "TEXT")
        db.commit()


async def save_report(
    report: MarketPulseReport,
    facts: list[FactObject] | None = None,
    claims: list[VerifiedClaim] | None = None,
) -> None:
    """Persist a complete report and its fact payloads for later API/chat lookup."""
    await create_tables()
    facts = facts or []
    embeddings = await _embed_facts_for_storage(facts)
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            INSERT OR REPLACE INTO reports (report_id, payload)
            VALUES (?, ?)
            """,
            (report.report_id, report.model_dump_json()),
        )
        for fact in facts:
            db.execute(
                """
                INSERT OR REPLACE INTO facts (fact_id, report_id, payload, embedding)
                VALUES (?, ?, ?, ?)
                """,
                (
                    fact.fact_id,
                    report.report_id,
                    fact.model_dump_json(),
                    json.dumps(embeddings.get(fact.fact_id)) if fact.fact_id in embeddings else None,
                ),
            )
        for claim in claims or []:
            db.execute(
                """
                INSERT OR REPLACE INTO claims (claim_id, report_id, payload)
                VALUES (?, ?, ?)
                """,
                (claim.claim_id, report.report_id, claim.model_dump_json()),
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


async def list_report_facts(report_id: str) -> list[FactObject]:
    await create_tables()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT payload FROM facts WHERE report_id = ?",
            (report_id,),
        ).fetchall()
    return [FactObject.model_validate_json(row["payload"]) for row in rows]


async def get_fact(report_id: str, fact_id: str) -> FactObject | None:
    await create_tables()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT payload FROM facts WHERE report_id = ? AND fact_id = ?",
            (report_id, fact_id),
        ).fetchone()
    return FactObject.model_validate_json(row["payload"]) if row else None


async def get_claim(report_id: str, claim_id: str) -> VerifiedClaim | None:
    await create_tables()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT payload FROM claims WHERE report_id = ? AND claim_id = ?",
            (report_id, claim_id),
        ).fetchone()
    return VerifiedClaim.model_validate_json(row["payload"]) if row else None


async def search_facts(report_id: str, query: str, top_k: int = 10) -> list[FactObject]:
    """
    Semantic search over stored fact embeddings.

    If the embedding model is unavailable or older facts lack embeddings, falls
    back to deterministic lexical scoring so chat can still answer cautiously.
    """
    await create_tables()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT payload, embedding FROM facts WHERE report_id = ?",
            (report_id,),
        ).fetchall()

    if not rows:
        return []

    items: list[tuple[FactObject, list[float] | None]] = []
    for row in rows:
        fact = FactObject.model_validate_json(row["payload"])
        embedding = _parse_embedding(row["embedding"])
        items.append((fact, embedding))

    if any(embedding is not None for _fact, embedding in items):
        try:
            query_embedding = embed_texts([query])[0]
            scored = [
                (cosine_similarity(query_embedding, embedding), fact)
                for fact, embedding in items
                if embedding is not None
            ]
            scored.sort(key=lambda item: item[0], reverse=True)
            return [fact for score, fact in scored[:top_k] if score > 0]
        except Exception as exc:
            logger.warning("Embedding search failed; falling back to lexical search: %s", exc)

    scored = [
        (lexical_score(query, _fact_search_text(fact)), fact)
        for fact, _embedding in items
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [fact for score, fact in scored[:top_k] if score > 0]


async def get_company_narrative(report_id: str, ticker_or_company: str) -> CompanyNarrative | None:
    report = await load_report(report_id)
    if report is None:
        return None
    needle = ticker_or_company.lower().strip()
    for narrative in report.company_narratives:
        if narrative.ticker.lower() == needle or narrative.company.lower() == needle:
            return narrative
    return None


async def save_chat_message(session_id: str, role: str, content: str) -> None:
    await create_tables()
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            INSERT INTO chat_history (session_id, role, content)
            VALUES (?, ?, ?)
            """,
            (session_id, role, content),
        )
        db.commit()


def _ensure_column(db: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    existing = {
        row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


async def _embed_facts_for_storage(facts: list[FactObject]) -> dict[str, list[float]]:
    if not facts:
        return {}
    try:
        texts = [_fact_search_text(fact) for fact in facts]
        # Keep this synchronous. In this environment, default-executor shutdown
        # can linger after failed model loads, and report persistence must not
        # keep the process alive after a handled embedding failure.
        vectors = embed_texts(texts)
        return {
            fact.fact_id: vector
            for fact, vector in zip(facts, vectors)
        }
    except Exception as exc:
        logger.warning("Fact embedding generation skipped: %s", exc)
        return {}


def _fact_search_text(fact: FactObject) -> str:
    return (
        f"{fact.entity} {fact.signal_type.value} {fact.claim} "
        f"{fact.evidence_quote} {fact.source_url}"
    )


def _parse_embedding(raw: object) -> list[float] | None:
    if not raw:
        return None
    try:
        data = json.loads(str(raw))
        if isinstance(data, list):
            return [float(item) for item in data]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return None
