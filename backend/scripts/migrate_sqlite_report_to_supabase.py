"""
Migrate report_e68e7289fc30 from local SQLite into Supabase.

Usage (run from backend/):
    DATABASE_URL="postgresql://postgres:[password]@[host]:5432/postgres" \\
        python scripts/migrate_sqlite_report_to_supabase.py

DATABASE_URL must be passed as env var — not read from .env — to avoid secret leakage.

Row counts verified after migration:
    reports     = 1
    facts       = 67
    verified_claims = 10
    company_narratives = 3
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
import json
import os
import sqlite3
import sys
from pathlib import Path

# Ensure app.* imports resolve when running from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg

from app.schemas.models import (
    CompanyNarrative,
    FactObject,
    MarketPulseReport,
    VerifiedClaim,
)
from app.utils.helpers import extract_domain

REPORT_ID = "report_e68e7289fc30"
DB_PATH = Path(__file__).parent.parent / "data" / "pulselens.db"
BUNDLE_DIRNAME = f"final_review_bundle_{REPORT_ID}"

EXPECTED = {
    "reports": 1,
    "facts": 67,
    "verified_claims": 10,
    "company_narratives": 3,
}

# Maps substrings found in a JSON filename → valid audit_type value (schema CHECK constraint).
# First match wins; order from most specific to least.
_AUDIT_TYPE_PATTERNS: list[tuple[str, str]] = [
    ("pricing_pressure_semantics", "pricing_pressure_semantics"),
    ("pricing_extraction_gap",     "pricing_extraction_gap"),
    ("pricing_diagnostics",        "pricing_diagnostics"),
    ("signal_semantics",           "signal_semantics"),
    ("evidence_quality",           "evidence_quality"),
    ("source_quality",             "source_quality"),
    ("fetch_error_summary",        "fetch_error_summary"),
    ("fetch_error",                "fetch_error_summary"),
    ("suspicious_claims",          "suspicious_claims"),
    ("quality_gate",               "quality_gate"),
    ("web_collection",             "web_collection"),
    ("query_planner",              "query_planner"),
    ("pipeline_run_log",           "pipeline_run_log"),
    ("run_log",                    "pipeline_run_log"),
]


def _detect_audit_type(filename: str) -> str | None:
    stem = filename.lower()
    for pattern, audit_type in _AUDIT_TYPE_PATTERNS:
        if pattern in stem:
            return audit_type
    return None


def _find_bundle_dir() -> Path | None:
    """Search for the final review bundle at several plausible locations."""
    script_dir = Path(__file__).resolve().parent        # backend/scripts/
    backend_dir = script_dir.parent                     # backend/
    repo_root = backend_dir.parent                      # PulseLens/
    cwd = Path.cwd().resolve()

    candidates = [
        repo_root  / "pipeline_audit_artifacts" / BUNDLE_DIRNAME,
        backend_dir / "pipeline_audit_artifacts" / BUNDLE_DIRNAME,
        cwd        / "pipeline_audit_artifacts" / BUNDLE_DIRNAME,
        cwd        / BUNDLE_DIRNAME,
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return None


# ─── datetime / date helpers ─────────────────────────────────────────────────
# asyncpg requires Python datetime/date objects — it rejects bare ISO strings
# for built-in Postgres types (timestamptz, date).

def _parse_datetime(value: object) -> datetime | None:
    """Parse an ISO datetime string (or passthrough datetime) into a datetime."""
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
    return None


# ─── SQLite readers ──────────────────────────────────────────────────────────

def _sqlite_load_report() -> MarketPulseReport:
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT payload FROM reports WHERE report_id = ?", (REPORT_ID,)
        ).fetchone()
    if row is None:
        raise SystemExit(f"[ERROR] {REPORT_ID} not found in {DB_PATH}")
    return MarketPulseReport.model_validate_json(row["payload"])


def _sqlite_load_facts() -> list[tuple[FactObject, list[float] | None]]:
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT payload, embedding FROM facts WHERE report_id = ?", (REPORT_ID,)
        ).fetchall()
    result = []
    for row in rows:
        fact = FactObject.model_validate_json(row["payload"])
        embedding: list[float] | None = None
        if row["embedding"]:
            try:
                data = json.loads(row["embedding"])
                if isinstance(data, list):
                    embedding = [float(v) for v in data]
            except (ValueError, json.JSONDecodeError):
                pass
        result.append((fact, embedding))
    return result


def _sqlite_load_claims() -> list[VerifiedClaim]:
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT payload FROM claims WHERE report_id = ?", (REPORT_ID,)
        ).fetchall()
    return [VerifiedClaim.model_validate_json(row["payload"]) for row in rows]


# ─── asyncpg helpers ─────────────────────────────────────────────────────────

async def _init_conn(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


def _vec_str(vec: list[float]) -> str:
    return "[" + ",".join(str(v) for v in vec) + "]"


async def _insert_report(conn: asyncpg.Connection, report: MarketPulseReport) -> None:
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
        ON CONFLICT (report_id) DO NOTHING
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


async def _insert_fact(
    conn: asyncpg.Connection,
    report_id: str,
    fact: FactObject,
    embedding: list[float] | None,
) -> None:
    embed_str = _vec_str(embedding) if embedding else None
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


async def _insert_claim(
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


async def _insert_audit_artifact(
    conn: asyncpg.Connection,
    report_id: str,
    audit_type: str,
    payload: dict,
) -> None:
    # audit_artifacts has no unique constraint on (report_id, audit_type), so we
    # guard idempotency with WHERE NOT EXISTS rather than ON CONFLICT.
    await conn.execute(
        """
        INSERT INTO audit_artifacts (report_id, audit_type, payload)
        SELECT $1, $2, $3
        WHERE NOT EXISTS (
            SELECT 1 FROM audit_artifacts
            WHERE report_id = $1 AND audit_type = $2
        )
        """,
        report_id,
        audit_type,
        payload,
    )


async def _insert_narrative(
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
        ON CONFLICT (report_id, ticker) DO NOTHING
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


# ─── verification ─────────────────────────────────────────────────────────────

async def _verify(conn: asyncpg.Connection) -> bool:
    actuals: dict[str, int] = {}
    for table in ("reports", "facts", "verified_claims", "company_narratives"):
        where = f"WHERE report_id = '{REPORT_ID}'"
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table} {where}")
        actuals[table] = int(count)

    ok = True
    print()
    print("─── Verification ───────────────────────────────")
    for table, expected in EXPECTED.items():
        actual = actuals.get(table, 0)
        status = "✓" if actual == expected else "✗ MISMATCH"
        print(f"  {table:<22} {actual:>3} / {expected:<3}  {status}")
        if actual != expected:
            ok = False
    print("────────────────────────────────────────────────")
    return ok


# ─── main ────────────────────────────────────────────────────────────────────

async def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("[ERROR] DATABASE_URL env var is required. Do not store in .env.")

    print(f"[INFO] Source SQLite: {DB_PATH}")
    print(f"[INFO] Target Postgres: {dsn.split('@')[-1]}")  # host portion only, no credentials

    print("[INFO] Reading from SQLite…")
    report = _sqlite_load_report()
    fact_pairs = _sqlite_load_facts()
    claims = _sqlite_load_claims()
    print(f"  report_id : {report.report_id}")
    print(f"  facts     : {len(fact_pairs)}")
    print(f"  claims    : {len(claims)}")
    print(f"  narratives: {len(report.company_narratives)}")

    # ── Dry validation (zero-cost, no network) ────────────────────────────────
    generated_at_dt = _parse_datetime(report.generated_at)
    date_parsed_count = sum(
        1 for f, _ in fact_pairs if _parse_date(f.published_date) is not None
    )
    print("[INFO] Dry validation:")
    print(f"  generated_at type    : {type(generated_at_dt).__name__} ({generated_at_dt})")
    print(f"  facts with date      : {date_parsed_count} / {len(fact_pairs)}")
    if generated_at_dt is None:
        raise SystemExit("[ERROR] generated_at parsed to None — cannot insert report row.")

    # ── Audit bundle discovery ────────────────────────────────────────────────
    audit_dir = _find_bundle_dir()
    audit_files: list[tuple[Path, str]] = []
    if audit_dir is None:
        print(f"[SKIP] audit bundle not found — audit_artifacts table will be empty")
        print(f"       (searched: repo_root, backend/, cwd for '{BUNDLE_DIRNAME}')")
    else:
        print(f"[INFO] audit bundle found: {audit_dir}")
        for json_file in sorted(audit_dir.glob("*.json")):
            audit_type = _detect_audit_type(json_file.name)
            if audit_type:
                audit_files.append((json_file, audit_type))
                print(f"       {json_file.name} → {audit_type}")
            else:
                print(f"       [SKIP] {json_file.name} — no matching audit_type, skipped")

    print()
    print("[INFO] Connecting to Supabase…")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3, init=_init_conn)

    async with pool.acquire() as conn:
        print("[INFO] Inserting report row…")
        await _insert_report(conn, report)

        print(f"[INFO] Inserting {len(fact_pairs)} facts…")
        for fact, embedding in fact_pairs:
            await _insert_fact(conn, REPORT_ID, fact, embedding)

        print(f"[INFO] Inserting {len(claims)} verified_claims…")
        for claim in claims:
            await _insert_claim(conn, REPORT_ID, claim)

        print(f"[INFO] Inserting {len(report.company_narratives)} company_narratives…")
        for narrative in report.company_narratives:
            await _insert_narrative(conn, REPORT_ID, narrative)

        if audit_files:
            print(f"[INFO] Inserting {len(audit_files)} audit_artifact rows…")
            for json_path, audit_type in audit_files:
                try:
                    payload = json.loads(json_path.read_text(encoding="utf-8"))
                    await _insert_audit_artifact(conn, REPORT_ID, audit_type, payload)
                except Exception as exc:
                    print(f"       [WARN] failed to insert {json_path.name}: {exc}")

        ok = await _verify(conn)

    await pool.close()

    if ok:
        print("\n[OK] Migration completed successfully.")
    else:
        print("\n[FAIL] Row counts do not match expected values.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
