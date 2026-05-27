# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

### Frontend

```bash
cd frontend
npm run dev       # dev server on :5173 (proxies /api → :8000)
npm run build     # tsc type-check + Vite build → dist/
npm run preview   # serve dist/ locally
```

### Backend

```bash
# Start API server
cd backend
uvicorn main:app --reload   # FastAPI on :8000

# Run full demo pipeline (writes report_id to /tmp/pulselens_report_id.txt)
python run_pipeline.py

# Run evidence quality audit against a specific report (no API calls, reads DB + JSON)
python scripts/evidence_quality_audit.py --report-id report_05aacb872fda

# Zero-cost static regression tests (no API keys needed)
python tests/pipeline/test_agent1_expansion_stability.py   # 4 tests, Sprint 5 guard
python tests/pipeline/test_agent1_signal_balance.py        # 15 tests, Sprint 7 guard

# pytest (live integration tests require API keys)
cd backend && pytest tests/test_chat.py -v
```
Do not run `pytest` over the entire backend test suite unless API keys are available and live API cost is acceptable. Prefer zero-cost tests in backend/tests/pipeline/.

Use `python run_pipeline.py` for the app pipeline endpoint-style run.
Use `python scripts/demo_track2_ai_hardware_audit.py` only when intentionally producing a full audit artifact bundle.

All scripts must be run from `backend/` so that `app.*` imports resolve correctly.

---

## Architecture

### LangGraph Pipeline (`backend/app/pipeline/graph.py`)

A linear StateGraph with conditional expansion. Order:

```
agent1_query_planner → agent2_web_collector → validate_and_split
  → quality_gate (conditional router) ──┐
       │ PASS/PARTIAL_PASS              │ FAIL_EXPAND (max 2 rounds)
       ↓                                └→ agent1 (regeneration round)
  agent4_finbert_scorer → agent5_triangulator
  → company_narratives → report_assembler
  → (agent6_narrative_synthesizer, agent7_watch_list_builder) [parallel]
```

`quality_gate` (`node_quality_gate.py`) is pure Python, no LLM — it enforces `MIN_FACTS=50` and `MIN_SOURCE_COUNT=15` and routes the graph.

`validate_and_split` runs SAFE verification (arXiv:2403.18802) on every extracted fact before the quality gate sees them.

### Agent 1 — Query Planning (`agent1_query_planner.py`)

The most complex agent. Two phases:
1. **Step-Back abstraction** — generates a sector-level framing prompt
2. **Multi-HyDE fan-out** — generates hypothetical document embeddings per signal type, then expands into actual search queries

Key Sprint 7 structural constants (do not remove):
- `_DEMO_SIGNAL_QUERY_MINIMUMS` — per-signal floor (product_launch≥4, supplier_risk≥3, investor_signal≥4, strategic_messaging≥2)
- `_DEMO_SIGNAL_QUERY_CAPS` — per-signal ceiling (investor_signal≤7) to prevent collapse into a single signal type
- `_targeted_signal_regeneration` — priority-ordered regen (product_launch → supplier_risk → strategic_messaging), max 2 calls

These three mechanisms together prevent the Sprint 6 regression (product_launch collapsed from 14→1 fact, 7 hallucinations appeared).

### State (`backend/app/pipeline/state.py`)

`PipelineState` is a `TypedDict` with 79+ fields. It flows through all nodes. Important field groups:
- `queries` / `query_telemetry` — Agent 1 outputs
- `documents` — Agent 2 outputs (RawDocument list)
- `facts` / `verified_facts` — Agent 3 + SAFE outputs
- `verified_claims` / `contradictions` — Triangulator outputs
- `quality_status` / `quality_reason` — Quality gate decisions
- `pulse_score` / `pulse_status` / `company_narratives` — Final report fields

### Data Models (`backend/app/schemas/models.py`)

Core types in dependency order:
- `SignalType` enum (7 types: hiring_momentum, product_launch, pricing_pressure, strategic_messaging, investor_signal, news_sentiment, supplier_risk)
- `RawDocument` → `FactObject` → `VerifiedClaim` → `CompanyNarrative` → `MarketPulseReport`
- `QualityStatus`: PASS / PARTIAL_PASS / FAIL_EXPAND
- `VerifiedClaim.factscore` maps to FActScore (arXiv:2305.14251)

### Demo Scope (`backend/app/config/demo_scope.py`)

When `PULSELENS_DEMO_SCOPE=true` (default), the pipeline targets:
- Companies: Nvidia, AMD, Supermicro
- Signals: product_launch, investor_signal, pricing_pressure, supplier_risk, strategic_messaging
- Query budget: 22–32 total (15 deterministic playbook + 7–17 LLM-generated)

Full-scope mode adds 5 more companies and all 7 signal types.

### FastAPI Backend (`backend/main.py`)

Three endpoints:
- `POST /api/run` — triggers the pipeline asynchronously, returns `report_id`
- `GET /api/report/{report_id}` — fetches `MarketPulseReport` from SQLite
- `POST /api/chat` — RAG chat over facts for a given `report_id`

### Frontend (`frontend/src/`)

Vite + React 18 + TailwindCSS 4 + Recharts. Module structure under `src/modules/`:
- `dashboard/` — main report view with charts and fact cards
- `chat/` — chat interface over report facts
- `sector-select/` — market/scope selector
- `news/` — news items from report

`vite.config.ts` proxies all `/api` requests to `http://localhost:8000`. No direct API key exposure in the frontend.

### Database (`backend/app/db/database.py`)

Async SQLite (`aiosqlite`) at `backend/data/pulselens.db`. Schema auto-created on startup. Tables: `facts`, `verified_claims`, `reports`, `company_narratives`, `chat_history`. Do not delete this file — it holds all sprint pipeline outputs.

---

## Key Environment Variables

See `backend/.env.example` if present. Do not print secret values.

```
OPENROUTER_API_KEY        # LLM calls (Agent 1, 3, 6, 7)
BRIGHTDATA_API_KEY        # Web collection (Agent 2)
PULSELENS_DEMO_SCOPE=true # Use Track 2 demo slice (Nvidia/AMD/Supermicro)
QUALITY_MIN_FACTS=50      # Do not lower — controls PARTIAL_PASS threshold
QUALITY_MIN_SOURCE_COUNT=15
AGENT1_MODEL=google/gemini-2.5-flash
FINBERT_MODEL=ProsusAI/finbert
```

---

## Sprint 7 Authoritative Baseline

The authoritative demo report is `report_05aacb872fda` (PARTIAL_PASS, 49/50 facts, pulse_score=55.8). All Sprint 7.1 reconciliation documents are at the repo root. Audit artifacts are in `pipeline_audit_artifacts/sprint7_review_bundle_20260527T001729Z/`.

**Do not:**
- Lower `QUALITY_MIN_FACTS` to fake PASS
- Remove the signal balance constants from `agent1_query_planner.py`
- Modify `node_quality_gate.py` thresholds
- Re-run the live pipeline without explicit instruction

---

## Scripts Organization

```
backend/scripts/                          # primary entrypoints only
  demo_track2_ai_hardware_audit.py        # live demo runner
  evidence_quality_audit.py              # offline evidence audit (reads DB + JSON)
  pricing_document_extraction_diagnosis.py

backend/scripts/diagnostics/             # live diagnostic scripts (require API keys)
backend/scripts/archive_pre_submission/  # archived integration tests

backend/tests/pipeline/                  # zero-cost static tests (no API keys)
  test_agent1_expansion_stability.py
  test_agent1_signal_balance.py
```

---

## Current Focus

Sprint 8 — judge-facing demo dashboard and submission polish. Prefer frontend and report-presentation work. Do not optimize backend retrieval, rerun the live pipeline, or change Quality Gate thresholds unless explicitly instructed.
