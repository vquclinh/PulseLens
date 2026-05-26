# Sprint 2 Implementation Plan

## Sprint Goal

Backend Stabilization Sprint 2 focuses on a demo-ready Bright Data Track 2 slice:

- Market: US AI Hardware / Semiconductor
- Demo companies: Nvidia, AMD, Supermicro
- Required core signals: investor_signal, product_launch, pricing_pressure, supplier_risk
- Optional signals: hiring_momentum, news_sentiment, strategic_messaging

The goal is to improve real pricing_pressure retrieval without faking evidence, bypassing validation, or weakening quality thresholds to force PASS.

## Safety Decisions

- LangGraph DAG node order will not change.
- Existing agents will not be removed or bypassed.
- Agent 3, SAFE, FinBERT, M4 triangulation, Agent 6, Agent 7, and report assembly will not be redesigned.
- Existing `SignalType` values will not change.
- Existing source types will be reused: mainly `pricing_pages` and `serp_news`.
- No new source_type enum values are planned.
- Metadata-only documents will not enter normal fact extraction by default.
- Full 8-company mode will remain available.
- Quality thresholds will not be lowered to hide weak retrieval.

## Planned File Changes

| File | Change Type | Planned Change |
| --- | --- | --- |
| `backend/app/config/demo_scope.py` | config-only | New small config layer for `PULSELENS_DEMO_SCOPE`, demo companies, core signals, optional signals, and helpers for demo/full scope. |
| `backend/.env.example` | config-only | Add `PULSELENS_DEMO_SCOPE=true` and comments explaining demo vs full mode. |
| `backend/app/pipeline/pricing_pressure_playbook.py` | query-planning-only | New deterministic pricing query playbook for Nvidia, AMD, Supermicro, and market-level pricing context. |
| `backend/app/pipeline/agent1_query_planner.py` | query-planning-only | Add optional target signal set support; inject deterministic pricing_pressure playbook queries for demo scope; keep LLM query generation small and merge/dedupe with deterministic queries. |
| `backend/app/pipeline/state.py` | schema-adjacent pipeline-state-only | Add optional state fields for `target_signal_types`, `core_signal_types`, `optional_signal_types`, and `demo_scope_enabled`. |
| `backend/app/pipeline/graph.py` | graph-node-logic-only | Pass demo/target signal scope to Agent 1; keep DAG and node order unchanged. |
| `backend/app/pipeline/node_quality_gate.py` | config/quality-logic-only | Make required signal coverage scope-aware using state-provided core signals; do not lower configured thresholds globally. |
| `backend/app/schemas/models.py` | schema-only | Add `RawDocument.extraction_allowed: bool = True` so metadata_only documents can be preserved but excluded from extraction. |
| `frontend/src/types/index.ts` | frontend-type-only | Mirror `RawDocument.extraction_allowed`. |
| `backend/app/pipeline/agent2_web_workers.py` | web-worker-only | Add pricing-specific fallback policy telemetry; preserve strong pricing metadata as `metadata_only` with `extraction_allowed=False`; avoid applying stale strict site constraints to intentional pricing fallbacks. |
| `backend/app/utils/url_scorer.py` | URL-scoring-only | Add pricing-specific acceptance/rejection reasons and source-family rules for cloud pricing, OEM/distributor, and pricing/news context. |
| `backend/scripts/pricing_pressure_retrieval_audit.py` | audit-only | New cheap audit that runs only pricing query planning and Agent 2 collection for demo scope. |
| `backend/scripts/demo_track2_ai_hardware_audit.py` | audit-only | New demo full-pipeline audit using 3 companies and 4 core signals. |
| `backend/scripts/full_pipeline_retrieval_quality_audit.py` | audit-only | Make the existing script clearly report demo/full scope and respect demo scope unless explicitly disabled. |
| `PRICING_PRESSURE_FAILURE_ANALYSIS.md` | audit/report-only | Summarize why pricing_pressure failed in the latest artifact. |
| `PRICING_PRESSURE_RETRIEVAL_SPRINT_2_REPORT.md` | audit/report-only | Final sprint report with before/after metrics. |
| `SPRINT_2_CHANGELOG_AND_RISK_CHECK.md` | audit/report-only | Risk and compatibility checklist. |

## LangGraph DAG Impact

LangGraph DAG order will not change.

No nodes will be added or removed. The existing sequence remains:

`query_planner -> web_worker -> fact_extractor -> validate_fact -> validate_and_split -> finbert_scorer -> quality_gate -> triangulator -> contradiction_writer -> signal_scorer -> company_narratives -> narrative_synthesizer -> watch_list_builder -> report_assembler`

The only graph-level change is passing scope fields through state and filtering documents with `extraction_allowed=False` before fact extraction.

## Downstream Agent Logic Impact

Downstream agent methodology will not change.

- Agent 3 extraction prompt and validation stay the same.
- SAFE stays fail-closed and uses the same configured threshold.
- FinBERT stays enabled.
- M4/M5 logic stays enabled.
- Agent 6/7 stay enabled.
- Report assembler stays logically the same except it will receive better quality diagnostics from the existing state.

Small compatibility change:

- The graph wrapper around Agent 3 will exclude metadata-only documents where `extraction_allowed=False`.

## Schema / Type Impact

Schema/type change planned:

- Add `RawDocument.extraction_allowed: bool = True`.
- Update frontend `RawDocument` type to include `extraction_allowed: boolean`.

No `SignalType` changes.
No `SearchQuery` model changes are planned. Pricing playbook metadata will be stored in audit artifacts / query planner telemetry, not in the core query schema.

## Frontend Impact

Frontend redesign: no.

Frontend type update: yes, only to mirror `RawDocument.extraction_allowed`.

No UI layout or feature changes are planned.

## Audit Strategy

Before code changes:

- Analyze latest pricing_pressure failures from `pipeline_audit_artifacts/20260525T171824Z`.
- Save failure JSON under a new `pipeline_audit_artifacts/<timestamp>/` directory.
- Write `PRICING_PRESSURE_FAILURE_ANALYSIS.md`.

After code changes:

- Run backend compile/import checks.
- Run `pricing_pressure_retrieval_audit.py`.
- Run `demo_track2_ai_hardware_audit.py`.
- Run `full_pipeline_retrieval_quality_audit.py` only in demo scope unless cost/time looks unreasonable.
- Run frontend build only because frontend types changed.

## Expected Outcome

Success does not require forcing `PASS`.

The sprint is successful if:

- Pricing pressure produces real accepted full-text documents or clearly marked metadata-only weak signals.
- Metadata-only pricing snippets are not extracted as normal facts.
- The demo full pipeline covers all 4 core signals or honestly returns `PARTIAL_PASS` with specific reasons.
- The zero-doc rate improves for pricing_pressure compared with the latest full-scope audit.
- All failures remain visible in telemetry and artifacts.
