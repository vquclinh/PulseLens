# Clean Repository Structure — Sprint 7.1 Submission

**Date:** 2026-05-27
**Status:** Submission-ready

---

## Root

```
PulseLens/
├── README.md                                    ← Project overview
├── ARCHITECTURE.md                              ← System architecture
├── ARCHITECTURE.pdf                             ← Architecture diagram
├── idea.pdf                                     ← Original project concept
│
├── JUDGE_READINESS_ASSESSMENT_SPRINT_7.md       ← Demo readiness: safe/unsafe claims
├── SPRINT_7_EVIDENCE_RECONCILIATION_REPORT.md   ← Evidence audit + code bug fix
├── AUTHORITATIVE_SPRINT_7_1_ARTIFACTS.md        ← Sprint 7.1 artifact index
├── BALANCED_QUERY_PLANNING_SPRINT_7_REPORT.md   ← Query planning architecture
├── FULL_STAGE_PIPELINE_TRACE_SPRINT_7.md        ← Stage-by-stage trace
├── SPRINT_7_REGRESSION_COMPARISON.md            ← Sprint 4/5/6/7 regression table
│
├── SOURCE_HYGIENE_AUDIT_REPORT.md               ← Source hygiene scan results
├── CLEAN_REPOSITORY_STRUCTURE.md               ← This file
├── SUBMISSION_ARTIFACT_INDEX.md                 ← All artifact locations
├── SUBMISSION_CLEANUP_PLAN.md                   ← Cleanup plan + constraints
├── CLEANUP_MANIFEST.md                          ← All moved/archived files
│
├── backend/
├── frontend/
├── papers/
├── docs/
└── pipeline_audit_artifacts/
```

---

## backend/

```
backend/
├── app/
│   ├── api/            ← FastAPI routes
│   ├── config/         ← Settings, signal/company/scope definitions
│   ├── pipeline/       ← LangGraph agents (1-8), graph.py, quality_gate.py
│   │   └── [NO test files] ← test_a2_a3.py removed in Sprint 7.1
│   ├── schemas/        ← Pydantic models
│   └── utils/          ← url_scorer, helpers, llm_client, brightdata_client
│
├── scripts/
│   ├── demo_track2_ai_hardware_audit.py         ← PRIMARY: demo runner
│   ├── evidence_quality_audit.py                ← PRIMARY: evidence quality audit
│   ├── pricing_document_extraction_diagnosis.py ← PRIMARY: pricing diagnosis
│   │
│   ├── diagnostics/
│   │   ├── full_pipeline_live_audit.py          ← Live pipeline telemetry wrapper
│   │   ├── full_pipeline_retrieval_quality_audit.py ← Focused retrieval audit
│   │   └── pricing_pressure_retrieval_audit.py  ← Pricing-only retrieval audit
│   │
│   └── archive_pre_submission/
│       └── test_a2_a3.py                        ← Live A2→A3 integration test (archived)
│
├── tests/
│   ├── __init__.py
│   ├── test_chat.py                             ← Chat RAG unit tests
│   ├── test_pipeline_live.py                    ← Live integration tests (requires API keys)
│   ├── test_pipeline_quality.py                 ← Pipeline quality regression (live)
│   └── pipeline/
│       ├── __init__.py
│       ├── test_agent1_expansion_stability.py   ← Zero-cost Sprint 5 regression test
│       └── test_agent1_signal_balance.py        ← Zero-cost Sprint 7 regression test
│
├── data/
│   └── pulselns.db                              ← SQLite evidence store (preserved)
├── .env                                         ← API keys (preserved, never committed)
└── .venv/                                       ← Python virtual environment
```

---

## pipeline_audit_artifacts/

```
pipeline_audit_artifacts/
├── README.md
│
├── sprint7_review_bundle_20260527T001729Z/      ← AUTHORITATIVE Sprint 7 bundle
│   ├── evidence_quality_summary.json
│   ├── signal_semantics_audit.json
│   ├── suspicious_claims.json
│   ├── source_tier_quality_audit.json
│   ├── pricing_pressure_semantics_audit.json
│   ├── quality_gate_audit.json
│   ├── final_report_quality_summary.json
│   ├── query_planner_audit.json
│   ├── web_collection_audit.json
│   ├── demo_report_summary.json
│   └── [Sprint 7.1 documents]
│
├── demo_track2_20260526T165950Z/                ← Sprint 7 pipeline run artifacts
├── evidence_quality_20260526T171620Z/           ← Sprint 7 evidence audit artifacts
├── sprint7_signal_balance_tests_20260526T165738Z/ ← Sprint 7 static test results (final)
├── sprint5_review_bundle_20260526T081013Z/      ← Sprint 5 baseline reference
│
└── archive_pre_submission_20260527T175900Z/     ← All pre-Sprint-7 artifacts (23 dirs)
```

---

## docs/

```
docs/
├── submission/       ← Copies of 8 judge-facing documents
└── archive_sprints/  ← 35 archived sprint planning/history docs
```

---

## Key Design Decisions

### scripts/ vs tests/pipeline/ split

`backend/scripts/` contains only entrypoints that a human operator runs to audit or demo the system. `backend/tests/pipeline/` contains automated static tests that verify pipeline invariants with zero API cost — these are safe to run at any time without credentials.

### diagnostics/ classification

`full_pipeline_live_audit.py`, `full_pipeline_retrieval_quality_audit.py`, and `pricing_pressure_retrieval_audit.py` require live API credentials and write to pipeline_audit_artifacts. They are useful for debugging retrieval quality but are not part of the primary demo workflow. They live in `scripts/diagnostics/` rather than `scripts/` root to reduce clutter.

### archive_pre_submission/ classification

`test_a2_a3.py` is a live integration test (calls BrightData + OpenRouter) that was originally misplaced inside `backend/app/pipeline/` (the production package). It was relocated to `backend/scripts/` in Sprint 7.1 and archived in Sprint 7.1 source hygiene pass 2. It is not a demo entrypoint and not a zero-cost static test.

### No deletion of useful scripts

All scripts are preserved in either their primary location, `diagnostics/`, or `archive_pre_submission/`. Nothing was deleted.

---

## Running the Zero-Cost Tests

```bash
cd backend

# Sprint 5 expansion stability (4 tests, no API calls)
python tests/pipeline/test_agent1_expansion_stability.py

# Sprint 7 signal balance (15 tests, no API calls)
python tests/pipeline/test_agent1_signal_balance.py
```

Both write results to `pipeline_audit_artifacts/` for archival.

---

## Running the Primary Audit Scripts

```bash
cd backend

# Evidence quality audit against Sprint 7 authoritative report
python scripts/evidence_quality_audit.py

# Pricing extraction diagnosis
python scripts/pricing_document_extraction_diagnosis.py

# Full demo pipeline run (requires BRIGHTDATA_* + OPENROUTER_API_KEY)
python scripts/demo_track2_ai_hardware_audit.py
```
