from __future__ import annotations

from datetime import date, datetime, timezone
import json
import logging
from typing import Any

import asyncpg

from app.db.adapter import DatabaseAdapter
from app.schemas.models import (
    CompanyNarrative,
    FactObject,
    MarketPulseReport,
    MomentumLabel,
    PulseStatus,
    QualityStatus,
    SignalType,
    VerifiedClaim,
)
from app.utils.embeddings import cosine_similarity, embed_texts, lexical_score
from app.utils.helpers import extract_domain

logger = logging.getLogger(__name__)

_VECTOR_STR_MAX = 384


def _list_to_vector_str(vec: list[float]) -> str:
    return "[" + ",".join(str(v) for v in vec) + "]"


def _vector_str_to_list(raw: str | None) -> list[float] | None:
    if not raw:
        return None
    try:
        return [float(x) for x in raw.strip("[]").split(",")]
    except (ValueError, AttributeError):
        return None


def _parse_datetime(value: object) -> datetime | None:
    """Convert an ISO datetime string (or passthrough datetime) to a Python datetime.

    asyncpg requires a datetime object for TIMESTAMPTZ columns — it rejects bare strings.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


_DATE_STRPTIME_FORMATS = (
    "%B %d, %Y",   # January 9, 2026
    "%b %d, %Y",   # Jan 9, 2026
    "%B %d %Y",    # January 9 2026 / May 28 2026
    "%b %d %Y",    # Jan 9 2026
    "%d %B %Y",    # 9 January 2026
    "%d %b %Y",    # 9 Jan 2026
)


def _parse_date(value: object) -> date | None:
    """Convert various date representations to a Python date.

    Handles: None/empty, date, datetime, ISO date strings (YYYY-MM-DD),
    ISO datetime strings (T or space separator), and human-readable strings
    like "January 9, 2026" / "Jan 9, 2026" / "May 28 2026".
    Returns None for unrecognised values instead of raising.
    asyncpg requires a date object for DATE columns — it rejects bare strings.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip().rstrip(".,")
    if not s:
        return None
    # ISO datetime: "2026-01-09T..." or "2026-01-09 00:00:00"
    if "T" in s or (len(s) > 10 and s[4:5] == "-" and s[10:11] == " "):
        try:
            iso = s if not s.endswith("Z") else s[:-1] + "+00:00"
            return datetime.fromisoformat(iso).date()
        except ValueError:
            pass
    # ISO date: "YYYY-MM-DD"
    if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            pass
    # Human-readable formats
    for fmt in _DATE_STRPTIME_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    logger.debug("_parse_date: unrecognised date string %r — stored as NULL", s)
    return None


def _fact_search_text(fact: FactObject) -> str:
    return (
        f"{fact.entity} {fact.signal_type.value} {fact.claim} "
        f"{fact.evidence_quote} {fact.source_url}"
    )


class PostgresAdapter(DatabaseAdapter):

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self._dsn,
                min_size=1,
                max_size=5,
                command_timeout=30,
                init=_init_connection,
            )
        return self._pool

    # ─── save_report ─────────────────────────────────────────────────────────

    async def save_report(
        self,
        report: MarketPulseReport,
        facts: list[FactObject] | None = None,
        claims: list[VerifiedClaim] | None = None,
    ) -> None:
        facts = facts or []
        claims = claims or []
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await _upsert_report(conn, report)
            for fact in facts:
                await _upsert_fact(conn, report.report_id, fact)
            for claim in claims:
                await _upsert_claim(conn, report.report_id, claim)
            for narrative in report.company_narratives:
                await _upsert_narrative(conn, report.report_id, narrative)

    # ─── load_report ─────────────────────────────────────────────────────────

    async def load_report(self, report_id: str) -> MarketPulseReport | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM reports WHERE report_id = $1", report_id
            )
            if row is None:
                return None
            narrative_rows = await conn.fetch(
                "SELECT * FROM company_narratives WHERE report_id = $1 ORDER BY id",
                report_id,
            )
        return _row_to_report(row, narrative_rows)

    # ─── latest_report_id ────────────────────────────────────────────────────

    async def latest_report_id(self) -> str | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT report_id FROM reports
                WHERE report_id LIKE 'report_%'
                ORDER BY generated_at DESC NULLS LAST,
                         created_at  DESC NULLS LAST
                LIMIT 1
                """
            )
        return row["report_id"] if row else None

    # ─── list_report_facts ───────────────────────────────────────────────────

    async def list_report_facts(self, report_id: str) -> list[FactObject]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM facts WHERE report_id = $1", report_id
            )
        return [_row_to_fact(r) for r in rows]

    # ─── get_fact ────────────────────────────────────────────────────────────

    async def get_fact(self, report_id: str, fact_id: str) -> FactObject | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM facts WHERE report_id = $1 AND fact_id = $2",
                report_id,
                fact_id,
            )
        return _row_to_fact(row) if row else None

    # ─── get_claim ───────────────────────────────────────────────────────────

    async def get_claim(self, report_id: str, claim_id: str) -> VerifiedClaim | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM verified_claims WHERE report_id = $1 AND claim_id = $2",
                report_id,
                claim_id,
            )
        return _row_to_claim(row) if row else None

    # ─── search_facts ────────────────────────────────────────────────────────

    async def search_facts(
        self, report_id: str, query: str, top_k: int = 10
    ) -> list[FactObject]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Check if any facts have embeddings
            has_embedding = await conn.fetchval(
                "SELECT COUNT(*) FROM facts WHERE report_id = $1 AND embedding IS NOT NULL",
                report_id,
            )
            if has_embedding:
                try:
                    query_vec = embed_texts([query])[0]
                    vec_str = _list_to_vector_str(query_vec)
                    rows = await conn.fetch(
                        """
                        SELECT *, (embedding <=> $2::vector) AS dist
                        FROM facts
                        WHERE report_id = $1 AND embedding IS NOT NULL
                        ORDER BY dist ASC
                        LIMIT $3
                        """,
                        report_id,
                        vec_str,
                        top_k,
                    )
                    facts = [_row_to_fact(r) for r in rows]
                    return [f for f in facts if f is not None]
                except Exception as exc:
                    logger.warning("Vector search failed, falling back to lexical: %s", exc)

            # Lexical fallback
            rows = await conn.fetch(
                "SELECT * FROM facts WHERE report_id = $1", report_id
            )
        all_facts = [_row_to_fact(r) for r in rows]
        scored = [
            (lexical_score(query, _fact_search_text(f)), f)
            for f in all_facts
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for score, f in scored[:top_k] if score > 0]

    # ─── get_company_narrative ───────────────────────────────────────────────

    async def get_company_narrative(
        self, report_id: str, ticker_or_company: str
    ) -> CompanyNarrative | None:
        needle = ticker_or_company.lower().strip()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM company_narratives
                WHERE report_id = $1
                  AND (LOWER(ticker) = $2 OR LOWER(company) = $2)
                LIMIT 1
                """,
                report_id,
                needle,
            )
        return _row_to_narrative(row) if row else None

    # ─── save_chat_message ───────────────────────────────────────────────────

    async def save_chat_message(
        self, session_id: str, role: str, content: str
    ) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Ensure session exists
            await conn.execute(
                """
                INSERT INTO chat_sessions (session_id)
                VALUES ($1)
                ON CONFLICT (session_id) DO NOTHING
                """,
                session_id,
            )
            await conn.execute(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES ($1, $2, $3)
                """,
                session_id,
                role,
                content,
            )


# ─── asyncpg init ────────────────────────────────────────────────────────────

async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register JSONB codec so asyncpg returns Python objects, not strings."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


# ─── INSERT helpers ──────────────────────────────────────────────────────────

async def _upsert_report(conn: asyncpg.Connection, report: MarketPulseReport) -> None:
    await conn.execute(
        """
        INSERT INTO reports (
            report_id, market, time_window, generated_at,
            pulse_score, pulse_status, pulse_confidence, trend_vs_previous,
            evidence_count, source_count, quality_status,
            signal_breakdown, quality_reasons, audit_summary,
            top_signals, market_narrative, grounded_brief,
            news_items, contradictions
        ) VALUES (
            $1, $2, $3, $4,
            $5, $6, $7, $8,
            $9, $10, $11,
            $12, $13, $14,
            $15, $16, $17,
            $18, $19
        )
        ON CONFLICT (report_id) DO UPDATE SET
            pulse_score       = EXCLUDED.pulse_score,
            pulse_status      = EXCLUDED.pulse_status,
            pulse_confidence  = EXCLUDED.pulse_confidence,
            trend_vs_previous = EXCLUDED.trend_vs_previous,
            evidence_count    = EXCLUDED.evidence_count,
            source_count      = EXCLUDED.source_count,
            quality_status    = EXCLUDED.quality_status,
            signal_breakdown  = EXCLUDED.signal_breakdown,
            quality_reasons   = EXCLUDED.quality_reasons,
            audit_summary     = EXCLUDED.audit_summary,
            top_signals       = EXCLUDED.top_signals,
            market_narrative  = EXCLUDED.market_narrative,
            grounded_brief    = EXCLUDED.grounded_brief,
            news_items        = EXCLUDED.news_items,
            contradictions    = EXCLUDED.contradictions,
            updated_at        = NOW()
        """,
        report.report_id,
        report.market,
        report.time_window,
        _parse_datetime(report.generated_at),
        report.pulse_score,
        report.pulse_status.value,
        report.pulse_confidence,
        report.trend_vs_previous,
        report.evidence_count,
        report.source_count,
        report.quality_status.value,
        report.signal_breakdown,
        report.quality_reasons,
        report.audit_summary.model_dump(),
        [s.model_dump() for s in report.top_signals],
        report.market_narrative.model_dump(),
        report.grounded_brief.model_dump(),
        [n.model_dump() for n in report.news_items],
        [c.model_dump() for c in report.contradictions],
    )


async def _upsert_fact(
    conn: asyncpg.Connection, report_id: str, fact: FactObject, embedding: list[float] | None = None
) -> None:
    embed_str = _list_to_vector_str(embedding) if embedding else None
    await conn.execute(
        """
        INSERT INTO facts (
            fact_id, report_id, doc_id, entity, signal_type, claim,
            evidence_quote, source_url, source_domain, source_tier,
            published_date, sentiment, sentiment_score, confidence,
            safe_verified, atomic_claims, embedding
        ) VALUES (
            $1, $2, $3, $4, $5, $6,
            $7, $8, $9, $10,
            $11, $12, $13, $14,
            $15, $16, $17::vector
        )
        ON CONFLICT (fact_id) DO NOTHING
        """,
        fact.fact_id,
        report_id,
        fact.doc_id,
        fact.entity,
        fact.signal_type.value,
        fact.claim,
        fact.evidence_quote,
        fact.source_url,
        extract_domain(fact.source_url),
        fact.source_tier,
        _parse_date(fact.published_date),
        fact.sentiment,
        fact.sentiment_score,
        fact.confidence,
        fact.safe_verified,
        fact.atomic_claims,
        embed_str,
    )


async def _upsert_claim(
    conn: asyncpg.Connection, report_id: str, claim: VerifiedClaim
) -> None:
    await conn.execute(
        """
        INSERT INTO verified_claims (
            claim_id, report_id, entity, signal_type, summary,
            supporting_facts, corroboration_count, source_tiers_present,
            weighted_sentiment, recency_score, final_confidence, factscore,
            is_contradicted, contradiction_note
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8,
            $9, $10, $11, $12,
            $13, $14
        )
        ON CONFLICT (claim_id) DO NOTHING
        """,
        claim.claim_id,
        report_id,
        claim.entity,
        claim.signal_type.value,
        claim.summary,
        claim.supporting_facts,
        claim.corroboration_count,
        claim.source_tiers_present,
        claim.weighted_sentiment,
        claim.recency_score,
        claim.final_confidence,
        claim.factscore,
        claim.is_contradicted,
        claim.contradiction_note,
    )


async def _upsert_narrative(
    conn: asyncpg.Connection, report_id: str, narrative: CompanyNarrative
) -> None:
    await conn.execute(
        """
        INSERT INTO company_narratives (
            report_id, company, ticker, momentum, momentum_score,
            narrative, key_events, key_drivers, competitive_position,
            supporting_claim_ids, evidence_count,
            price_current, price_change_7d_pct, signal_lead_days
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9,
            $10, $11,
            $12, $13, $14
        )
        ON CONFLICT (report_id, ticker) DO UPDATE SET
            momentum             = EXCLUDED.momentum,
            momentum_score       = EXCLUDED.momentum_score,
            narrative            = EXCLUDED.narrative,
            key_events           = EXCLUDED.key_events,
            key_drivers          = EXCLUDED.key_drivers,
            competitive_position = EXCLUDED.competitive_position,
            supporting_claim_ids = EXCLUDED.supporting_claim_ids,
            evidence_count       = EXCLUDED.evidence_count,
            price_current        = EXCLUDED.price_current,
            price_change_7d_pct  = EXCLUDED.price_change_7d_pct,
            signal_lead_days     = EXCLUDED.signal_lead_days
        """,
        report_id,
        narrative.company,
        narrative.ticker,
        narrative.momentum.value,
        narrative.momentum_score,
        narrative.narrative,
        narrative.key_events,
        narrative.key_drivers,
        narrative.competitive_position,
        narrative.supporting_claim_ids,
        narrative.evidence_count,
        narrative.price_current,
        narrative.price_change_7d_pct,
        narrative.signal_lead_days,
    )


# ─── row → model helpers ─────────────────────────────────────────────────────

def _row_to_report(
    row: asyncpg.Record, narrative_rows: list[asyncpg.Record]
) -> MarketPulseReport:
    from app.schemas.models import (
        GroundedBrief, MarketNarrative, NewsItem, PipelineAuditSummary,
        SignalSummary, ContradictionFlag,
    )
    return MarketPulseReport(
        report_id=row["report_id"],
        market=row["market"],
        time_window=row["time_window"],
        generated_at=str(row["generated_at"].isoformat()) if hasattr(row["generated_at"], "isoformat") else str(row["generated_at"]),
        pulse_score=float(row["pulse_score"]),
        pulse_status=PulseStatus(row["pulse_status"]),
        pulse_confidence=float(row["pulse_confidence"]),
        trend_vs_previous=float(row["trend_vs_previous"]) if row["trend_vs_previous"] is not None else None,
        evidence_count=int(row["evidence_count"]),
        source_count=int(row["source_count"]),
        quality_status=QualityStatus(row["quality_status"]),
        signal_breakdown=dict(row["signal_breakdown"]) if row["signal_breakdown"] else {},
        quality_reasons=list(row["quality_reasons"]) if row["quality_reasons"] else [],
        audit_summary=PipelineAuditSummary.model_validate(row["audit_summary"]),
        top_signals=[SignalSummary.model_validate(s) for s in (row["top_signals"] or [])],
        market_narrative=MarketNarrative.model_validate(row["market_narrative"]),
        grounded_brief=GroundedBrief.model_validate(row["grounded_brief"]),
        news_items=[NewsItem.model_validate(n) for n in (row["news_items"] or [])],
        contradictions=[ContradictionFlag.model_validate(c) for c in (row["contradictions"] or [])],
        company_narratives=[_row_to_narrative(nr) for nr in narrative_rows],
    )


def _row_to_fact(row: asyncpg.Record) -> FactObject:
    return FactObject(
        fact_id=row["fact_id"],
        doc_id=row["doc_id"] or "",
        entity=row["entity"],
        signal_type=SignalType(row["signal_type"]),
        claim=row["claim"],
        evidence_quote=row["evidence_quote"],
        source_url=row["source_url"],
        source_tier=int(row["source_tier"]),
        published_date=str(row["published_date"]) if row["published_date"] else None,
        sentiment=row["sentiment"],  # type: ignore[arg-type]
        sentiment_score=float(row["sentiment_score"]),
        confidence=float(row["confidence"]),
        safe_verified=bool(row["safe_verified"]),
        atomic_claims=list(row["atomic_claims"]) if row["atomic_claims"] else None,
    )


def _row_to_claim(row: asyncpg.Record) -> VerifiedClaim:
    return VerifiedClaim(
        claim_id=row["claim_id"],
        entity=row["entity"],
        signal_type=SignalType(row["signal_type"]),
        summary=row["summary"],
        supporting_facts=list(row["supporting_facts"]) if row["supporting_facts"] else [],
        corroboration_count=int(row["corroboration_count"]),
        source_tiers_present=list(row["source_tiers_present"]) if row["source_tiers_present"] else [],
        weighted_sentiment=float(row["weighted_sentiment"]),
        recency_score=float(row["recency_score"]),
        final_confidence=float(row["final_confidence"]),
        factscore=float(row["factscore"]),
        is_contradicted=bool(row["is_contradicted"]),
        contradiction_note=row["contradiction_note"],
    )


def _validate_datetime_parse() -> None:
    """Zero-cost check that _parse_datetime/_parse_date work on real pipeline values.

    Run manually:  python -c "from app.db.postgres_adapter import _validate_datetime_parse; _validate_datetime_parse()"
    """
    dt = _parse_datetime("2026-05-28T03:27:43.118231+00:00")
    assert isinstance(dt, datetime), f"expected datetime, got {type(dt)}"
    assert dt.tzinfo is not None, "datetime must be tz-aware"

    dt_z = _parse_datetime("2026-05-27T17:48:35Z")
    assert isinstance(dt_z, datetime)

    assert _parse_datetime(None) is None
    assert _parse_datetime("") is None

    d = _parse_date("2026-05-20")
    assert isinstance(d, date) and not isinstance(d, datetime)

    d_full = _parse_date("2026-05-20T00:00:00+00:00")
    assert isinstance(d_full, date)

    d_space = _parse_date("2026-05-20 00:00:00")
    assert isinstance(d_space, date)

    # Human-readable formats
    d_jan = _parse_date("January 9, 2026")
    assert d_jan == date(2026, 1, 9), f"got {d_jan!r}"

    d_jan_abbr = _parse_date("Jan 9, 2026")
    assert d_jan_abbr == date(2026, 1, 9), f"got {d_jan_abbr!r}"

    d_may = _parse_date("May 28 2026")
    assert d_may == date(2026, 5, 28), f"got {d_may!r}"

    # Graceful failure — must return None, not raise
    assert _parse_date("not a date") is None
    assert _parse_date("") is None
    assert _parse_date(None) is None

    # Passthrough of already-correct types
    now_dt = datetime.now(tz=timezone.utc)
    assert _parse_datetime(now_dt) is now_dt
    today = now_dt.date()
    assert _parse_date(today) is today


def _row_to_narrative(row: asyncpg.Record) -> CompanyNarrative:
    return CompanyNarrative(
        company=row["company"],
        ticker=row["ticker"],
        momentum=MomentumLabel(row["momentum"]),
        momentum_score=int(row["momentum_score"]),
        narrative=row["narrative"],
        key_events=list(row["key_events"]) if row["key_events"] else [],
        key_drivers=list(row["key_drivers"]) if row["key_drivers"] else [],
        competitive_position=row["competitive_position"],  # type: ignore[arg-type]
        supporting_claim_ids=list(row["supporting_claim_ids"]) if row["supporting_claim_ids"] else [],
        evidence_count=int(row["evidence_count"]),
        price_current=float(row["price_current"]) if row["price_current"] is not None else None,
        price_change_7d_pct=float(row["price_change_7d_pct"]) if row["price_change_7d_pct"] is not None else None,
        signal_lead_days=int(row["signal_lead_days"]) if row["signal_lead_days"] is not None else None,
    )
