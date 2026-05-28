-- ============================================================
-- PulseLens — Supabase / PostgreSQL Schema
-- Migration: 001_supabase_schema.sql
--
-- Run once in Supabase SQL Editor on a fresh project.
-- Safe to re-run: all objects use IF NOT EXISTS / OR REPLACE.
-- Does NOT contain secrets. Does NOT reference environment vars.
-- ============================================================

-- ── Extensions ───────────────────────────────────────────────
-- pgvector: semantic search over 384-dim fact embeddings
-- (enabled by default on Supabase; included for completeness)
CREATE EXTENSION IF NOT EXISTS vector;


-- ── updated_at auto-stamp helper ─────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;


-- ============================================================
-- CORE TABLES
-- ============================================================

-- ── reports ─────────────────────────────────────────────────
-- One row per completed pipeline run. Scalar fields are
-- promoted for fast filtering; nested structures live in JSONB.
CREATE TABLE IF NOT EXISTS reports (
    report_id           TEXT        PRIMARY KEY,
    market              TEXT        NOT NULL,
    time_window         TEXT        NOT NULL,
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pulse_score         FLOAT       NOT NULL,
    pulse_status        TEXT        NOT NULL CHECK (pulse_status IN (
                            'heating_up','stable','cooling_down','volatile','risk_rising')),
    pulse_confidence    FLOAT       NOT NULL,
    trend_vs_previous   FLOAT,
    evidence_count      INT         NOT NULL DEFAULT 0,
    source_count        INT         NOT NULL DEFAULT 0,
    quality_status      TEXT        NOT NULL CHECK (quality_status IN ('PASS','PARTIAL_PASS','FAIL_EXPAND')),
    -- JSONB columns for nested / list fields
    signal_breakdown    JSONB       NOT NULL DEFAULT '{}'::jsonb,  -- {signal_type: score}
    quality_reasons     JSONB       NOT NULL DEFAULT '[]'::jsonb,  -- [string, ...]
    audit_summary       JSONB       NOT NULL DEFAULT '{}'::jsonb,  -- PipelineAuditSummary
    top_signals         JSONB       NOT NULL DEFAULT '[]'::jsonb,  -- [SignalSummary, ...]
    market_narrative    JSONB       NOT NULL DEFAULT '{}'::jsonb,  -- {headline, body, anomalies, watch_list}
    grounded_brief      JSONB       NOT NULL DEFAULT '{}'::jsonb,  -- {what_we_found, what_we_infer, strategic_implication}
    news_items          JSONB       NOT NULL DEFAULT '[]'::jsonb,  -- [NewsItem, ...]
    contradictions      JSONB       NOT NULL DEFAULT '[]'::jsonb,  -- [ContradictionFlag, ...]
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_reports_created_at   ON reports (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_market        ON reports (market);
CREATE INDEX IF NOT EXISTS idx_reports_quality       ON reports (quality_status);
CREATE INDEX IF NOT EXISTS idx_reports_pulse_score   ON reports (pulse_score DESC);


-- ── facts ────────────────────────────────────────────────────
-- One row per extracted, SAFE-verified fact.
-- Scalar fields promoted for filtering/aggregation.
-- pgvector column for semantic chat retrieval.
CREATE TABLE IF NOT EXISTS facts (
    fact_id         TEXT        PRIMARY KEY,
    report_id       TEXT        NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    doc_id          TEXT,
    entity          TEXT        NOT NULL,
    signal_type     TEXT        NOT NULL CHECK (signal_type IN (
                        'hiring_momentum','product_launch','pricing_pressure',
                        'strategic_messaging','investor_signal','news_sentiment','supplier_risk')),
    claim           TEXT        NOT NULL,
    evidence_quote  TEXT        NOT NULL,
    source_url      TEXT        NOT NULL,
    source_domain   TEXT        NOT NULL,   -- extracted from source_url, pre-stored for indexing
    source_tier     SMALLINT    NOT NULL CHECK (source_tier BETWEEN 1 AND 4),
    published_date  DATE,
    sentiment       TEXT        NOT NULL CHECK (sentiment IN ('positive','negative','neutral')),
    sentiment_score FLOAT       NOT NULL DEFAULT 0.0,
    confidence      FLOAT       NOT NULL DEFAULT 0.0,
    safe_verified   BOOLEAN     NOT NULL DEFAULT FALSE,
    atomic_claims   JSONB,                  -- [string, ...] from SAFE verification
    embedding       vector(384),            -- sentence-transformers/all-MiniLM-L6-v2
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_facts_report_id     ON facts (report_id);
CREATE INDEX IF NOT EXISTS idx_facts_signal_type   ON facts (signal_type);
CREATE INDEX IF NOT EXISTS idx_facts_entity        ON facts (entity);
CREATE INDEX IF NOT EXISTS idx_facts_source_domain ON facts (source_domain);
CREATE INDEX IF NOT EXISTS idx_facts_source_tier   ON facts (source_tier);
CREATE INDEX IF NOT EXISTS idx_facts_confidence    ON facts (confidence DESC);
-- HNSW index for vector similarity search (Supabase pgvector)
CREATE INDEX IF NOT EXISTS idx_facts_embedding
    ON facts USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);


-- ── verified_claims ──────────────────────────────────────────
-- Triangulated claims supported by ≥2 independent facts.
CREATE TABLE IF NOT EXISTS verified_claims (
    claim_id            TEXT        PRIMARY KEY,
    report_id           TEXT        NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    entity              TEXT        NOT NULL,
    signal_type         TEXT        NOT NULL CHECK (signal_type IN (
                            'hiring_momentum','product_launch','pricing_pressure',
                            'strategic_messaging','investor_signal','news_sentiment','supplier_risk')),
    summary             TEXT        NOT NULL,
    supporting_facts    JSONB       NOT NULL DEFAULT '[]'::jsonb,   -- [fact_id, ...]
    corroboration_count INT         NOT NULL DEFAULT 0,
    source_tiers_present JSONB      NOT NULL DEFAULT '[]'::jsonb,   -- [1, 2, ...]
    weighted_sentiment  FLOAT       NOT NULL DEFAULT 0.0,
    recency_score       FLOAT       NOT NULL DEFAULT 0.0,
    final_confidence    FLOAT       NOT NULL DEFAULT 0.0,
    factscore           FLOAT       NOT NULL DEFAULT 0.0,
    is_contradicted     BOOLEAN     NOT NULL DEFAULT FALSE,
    contradiction_note  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claims_report_id   ON verified_claims (report_id);
CREATE INDEX IF NOT EXISTS idx_claims_entity      ON verified_claims (entity);
CREATE INDEX IF NOT EXISTS idx_claims_signal_type ON verified_claims (signal_type);
CREATE INDEX IF NOT EXISTS idx_claims_confidence  ON verified_claims (final_confidence DESC);


-- ── company_narratives ───────────────────────────────────────
-- Per-company momentum summary produced by agent7.
CREATE TABLE IF NOT EXISTS company_narratives (
    id                  BIGSERIAL   PRIMARY KEY,
    report_id           TEXT        NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    company             TEXT        NOT NULL,
    ticker              TEXT        NOT NULL,
    momentum            TEXT        NOT NULL CHECK (momentum IN (
                            'strong_positive','positive','neutral','mixed','negative','elevated_risk')),
    momentum_score      INT         NOT NULL DEFAULT 0,
    narrative           TEXT        NOT NULL,
    key_events          JSONB       NOT NULL DEFAULT '[]'::jsonb,           -- [string, ...]
    key_drivers         JSONB       NOT NULL DEFAULT '[]'::jsonb,           -- [string, ...]
    competitive_position TEXT       NOT NULL CHECK (competitive_position IN ('gaining','holding','losing')),
    supporting_claim_ids JSONB      NOT NULL DEFAULT '[]'::jsonb,          -- [claim_id, ...]
    evidence_count      INT         NOT NULL DEFAULT 0,
    price_current       FLOAT,
    price_change_7d_pct FLOAT,
    signal_lead_days    INT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_narratives_report_company
    ON company_narratives (report_id, ticker);
CREATE INDEX IF NOT EXISTS idx_narratives_report_id ON company_narratives (report_id);
CREATE INDEX IF NOT EXISTS idx_narratives_ticker    ON company_narratives (ticker);
CREATE INDEX IF NOT EXISTS idx_narratives_momentum  ON company_narratives (momentum);


-- ============================================================
-- CHAT
-- ============================================================

-- ── chat_sessions ────────────────────────────────────────────
-- Session envelope linking chat to a specific report.
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id  TEXT        PRIMARY KEY,
    report_id   TEXT        REFERENCES reports(report_id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_chat_sessions_report_id  ON chat_sessions (report_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions (created_at DESC);


-- ── chat_messages ────────────────────────────────────────────
-- Individual turns within a chat session.
CREATE TABLE IF NOT EXISTS chat_messages (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      TEXT        NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role            TEXT        NOT NULL CHECK (role IN ('user','assistant')),
    content         TEXT        NOT NULL,
    cited_fact_ids  JSONB,                  -- [fact_id, ...] for assistant turns
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id  ON chat_messages (session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at  ON chat_messages (created_at);


-- ============================================================
-- PIPELINE OBSERVABILITY
-- ============================================================

-- ── pipeline_runs ────────────────────────────────────────────
-- Tracks each pipeline invocation regardless of whether it
-- produced a saved report (supports debugging failed runs).
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          TEXT        PRIMARY KEY,
    report_id       TEXT        REFERENCES reports(report_id) ON DELETE SET NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'running'
                                    CHECK (status IN ('running','completed','failed')),
    market          TEXT        NOT NULL,
    companies       JSONB       NOT NULL DEFAULT '[]'::jsonb,
    demo_scope      BOOLEAN     NOT NULL DEFAULT FALSE,
    expansion_rounds INT        NOT NULL DEFAULT 0,
    config_snapshot JSONB,               -- env-derived config at run time (no secrets)
    errors          JSONB       NOT NULL DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_report_id   ON pipeline_runs (report_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at  ON pipeline_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status      ON pipeline_runs (status);


-- ── audit_artifacts ──────────────────────────────────────────
-- Unified table for all audit JSON bundles produced by the
-- pipeline (query_planner, web_collection, quality_gate, etc.).
-- Uses an audit_type discriminator to avoid 12 separate tables.
CREATE TABLE IF NOT EXISTS audit_artifacts (
    id          BIGSERIAL   PRIMARY KEY,
    report_id   TEXT        REFERENCES reports(report_id) ON DELETE CASCADE,
    run_id      TEXT        REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
    audit_type  TEXT        NOT NULL CHECK (audit_type IN (
                    'query_planner',
                    'web_collection',
                    'quality_gate',
                    'evidence_quality',
                    'pricing_diagnostics',
                    'source_quality',
                    'pricing_extraction_gap',
                    'signal_semantics',
                    'fetch_error_summary',
                    'suspicious_claims',
                    'pricing_pressure_semantics',
                    'pipeline_run_log'
                )),
    payload     JSONB       NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_report_id   ON audit_artifacts (report_id);
CREATE INDEX IF NOT EXISTS idx_audit_type        ON audit_artifacts (audit_type);
CREATE INDEX IF NOT EXISTS idx_audit_created_at  ON audit_artifacts (created_at DESC);


-- ============================================================
-- ROW-LEVEL SECURITY
-- Supabase enforces RLS by default when enabled.
-- Backend uses the service-role key which bypasses RLS.
-- Frontend must NOT access Supabase directly.
-- ============================================================

ALTER TABLE reports             ENABLE ROW LEVEL SECURITY;
ALTER TABLE facts                ENABLE ROW LEVEL SECURITY;
ALTER TABLE verified_claims      ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_narratives   ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions        ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages        ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs        ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_artifacts      ENABLE ROW LEVEL SECURITY;

-- No public policies intentionally. The backend service role bypasses RLS.
-- Add per-user policies here when auth is introduced.


-- ============================================================
-- HELPER VIEWS
-- ============================================================

-- Latest report per market (useful for /api/reports/latest)
CREATE OR REPLACE VIEW latest_reports AS
SELECT DISTINCT ON (market)
    report_id, market, generated_at, pulse_score, pulse_status,
    evidence_count, source_count, quality_status
FROM reports
ORDER BY market, created_at DESC;


-- Signal fact count per report (denormalized for quick chart rendering)
CREATE OR REPLACE VIEW report_signal_counts AS
SELECT
    report_id,
    signal_type,
    COUNT(*)            AS fact_count,
    AVG(confidence)     AS avg_confidence,
    SUM(CASE WHEN safe_verified THEN 1 ELSE 0 END) AS verified_count
FROM facts
GROUP BY report_id, signal_type;


-- ============================================================
-- END OF MIGRATION
-- ============================================================
