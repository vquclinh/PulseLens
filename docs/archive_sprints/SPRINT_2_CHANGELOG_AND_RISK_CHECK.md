# Sprint 2 Changelog and Risk Check

## Change Summary

Implemented Backend Stabilization Sprint 2 for a demo-ready Bright Data Track 2 vertical slice.

Primary outcome:

- Demo scope now defaults to Nvidia, AMD, and Supermicro.
- Pricing_pressure retrieval uses deterministic playbook queries plus LLM-generated supporting queries.
- Agent 2 now applies pricing-specific URL acceptance and fallback policy.
- Reports remain honest: quality gate still uses strict thresholds and can return PASS / PARTIAL_PASS / FAIL_EXPAND.

## DAG / Compatibility

- LangGraph DAG changed: no.
- LangGraph node order changed: no.
- Nodes removed or bypassed: no.
- Downstream agent logic changed: no methodology changes.
- Agent 3 / SAFE / FinBERT / M4 / M5 / Agent 6 / Agent 7 / report assembly removed or weakened: no.
- Schema/types changed: yes, `RawDocument.extraction_allowed: bool`.
- Frontend files changed: yes, type-only update in `frontend/src/types/index.ts`.
- New source_type enum values: no.
- Existing SignalType values changed: no.

## Compatibility Risks

- `RawDocument.extraction_allowed` is backward-compatible in Python because it defaults to `True`, but old frontend assumptions needed the TypeScript type update.
- Demo scope is enabled by default with `PULSELENS_DEMO_SCOPE=true`; full mode remains available with `PULSELENS_DEMO_SCOPE=false`.
- Strict pricing source-family rules intentionally reject many generic GPU pricing aggregators. This improves evidence quality but can increase zero-doc rates for weak queries.
- Metadata-only documents are preserved but excluded from extraction by default. This avoids weak snippets becoming high-confidence claims.
- Query trimming now enforces max query count after validation. The trimmer preserves deterministic pricing playbook queries, required signals, company coverage, market coverage, and signal minimums before filling remaining slots.

## Commands Run

Backend/local checks:

```bash
cd backend && .venv/bin/python -m compileall -q app scripts
cd backend && .venv/bin/python -m app.utils.url_scorer
git diff --check
```

Focused validation snippets:

```bash
cd backend && .venv/bin/python - <<'PY'
from app.pipeline.agent1_query_planner import QueryPlanner
# verified target_entity_outside_requested_scope rejection
PY
```

```bash
cd backend && .venv/bin/python - <<'PY'
from app.pipeline.agent1_query_planner import QueryPlanner
# verified query cap trimming from 45 candidates to 32 while preserving coverage
PY
```

Live audits:

```bash
cd backend && .venv/bin/python scripts/pricing_pressure_retrieval_audit.py
cd backend && .venv/bin/python scripts/demo_track2_ai_hardware_audit.py
```

Frontend:

```bash
cd frontend && npm run build
```

Skipped intentionally:

```bash
cd backend && .venv/bin/python scripts/full_pipeline_retrieval_quality_audit.py
```

Reason: the clean demo audit already ran the narrowed full end-to-end pipeline with OpenRouter, Bright Data, SAFE, FinBERT, M4, M5, Agent 6, Agent 7, report assembly, and embeddings. Running the full audit script again would duplicate the same expensive path for little extra signal.

## Audit Artifacts

Pre-fix failure analysis:

- `pipeline_audit_artifacts/20260526T030015Z/pricing_pressure_failure_analysis.json`
- `PRICING_PRESSURE_FAILURE_ANALYSIS.md`

Pricing-only live audit:

- `pipeline_audit_artifacts/pricing_pressure_20260526T034324Z/pricing_scope_config.json`
- `pipeline_audit_artifacts/pricing_pressure_20260526T034324Z/pricing_queries.json`
- `pipeline_audit_artifacts/pricing_pressure_20260526T034324Z/pricing_web_collection_audit.json`
- `pipeline_audit_artifacts/pricing_pressure_20260526T034324Z/pricing_accepted_documents.json`
- `pipeline_audit_artifacts/pricing_pressure_20260526T034324Z/pricing_rejected_urls.json`
- `pipeline_audit_artifacts/pricing_pressure_20260526T034324Z/pricing_failure_summary.json`
- `pipeline_audit_artifacts/pricing_pressure_20260526T034324Z/pricing_pressure_failure_analysis.json`

Clean demo full-pipeline audit:

- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/demo_scope_config.json`
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/query_planner_audit.json`
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/web_collection_audit.json`
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/quality_gate_audit.json`
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/fetch_error_summary.json`
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/final_report_quality_summary.json`
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/demo_report_summary.json`
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/pipeline_run.log`

Ignored artifact:

- `pipeline_audit_artifacts/demo_track2_20260526T034920Z/`

Reason: this run started before the Agent 1 demo-scope entity validation fix and planned outside the 3-company demo scope.

## Test Results

Pricing-only audit:

- Scope mode: demo
- Companies: Nvidia, AMD, Supermicro
- Pricing queries: 15
- Accepted pricing documents: 13
- Zero-doc pricing queries: 3
- Zero-doc pricing query rate: 0.20
- Full-text docs: 9
- Metadata-only docs: 0
- Estimated Bright Data calls: 31

Demo full-pipeline audit:

- Report ID: `report_dfd5e69a3a42`
- quality_status: PASS
- quality_reasons: none
- Core signals covered: investor_signal, pricing_pressure, product_launch, supplier_risk
- Core signals missing: none
- Evidence count: 63
- Source count: 23
- Pricing_pressure document count: 18
- Zero-doc query rate: 0.0833
- Pulse score: 44.3
- Pulse status: risk_rising
- Watch list items: 3

Build/check results:

- Backend compile/import check: passed.
- URL scorer standalone checks: passed.
- Query scope rejection check: passed.
- Query cap trim check: passed.
- Frontend production build: passed.

## Anything Intentionally Not Fixed

- Agent 3 extraction prompt was not changed in this sprint because the safety constraints asked not to change Agent 3 logic.
- Full 8-company mode was not run because Sprint 2 was explicitly demo-scope focused.
- Quality thresholds were not lowered.
- Metadata-only evidence was not allowed into normal fact extraction.
- No frontend redesign was done.

## Remaining Risks

- Pricing_pressure is now present, but the pricing signal still has moderate confidence and few supporting sources.
- Some SEC/Reuters/Bloomberg direct fetches still time out occasionally; Agent 2 now logs these clearly.
- The demo full-pipeline live metrics used 36 queries; after that run, a query cap was added and unit-verified. A future audit should re-run once to collect post-cap live metrics when cost is acceptable.
- Embedding and FinBERT model loading can hit Hugging Face during cold starts; caching or prewarming would make demos smoother.
