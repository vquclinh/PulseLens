# Pricing Pressure Retrieval Sprint 2 Report

## Scope

Sprint 2 narrowed the demo slice for the Bright Data Track 2 finance/market-intelligence hackathon.

- Market: US AI Hardware / Semiconductor
- Demo companies: Nvidia, AMD, Supermicro
- Core signals: investor_signal, product_launch, pricing_pressure, supplier_risk
- Optional signals: hiring_momentum, news_sentiment, strategic_messaging

No pricing evidence was faked and quality thresholds were not lowered to force a pass.

## Files Changed

- `backend/app/config/demo_scope.py` — demo/full scope config.
- `backend/.env.example` — demo scope environment defaults.
- `backend/app/pipeline/pricing_pressure_playbook.py` — deterministic pricing_pressure playbook.
- `backend/app/pipeline/agent1_query_planner.py` — scope-aware planning, pricing playbook injection, entity scope validation, query cap trimming.
- `backend/app/pipeline/agent2_web_workers.py` — pricing fallback policy, metadata-only handling, richer telemetry.
- `backend/app/utils/url_scorer.py` — pricing source-family acceptance/rejection rules.
- `backend/app/pipeline/graph.py` — pass demo scope to Agent 1, skip non-extractable metadata docs, preserve web audit counters.
- `backend/app/pipeline/node_quality_gate.py` — scope-aware required signal coverage.
- `backend/app/pipeline/state.py` — demo/core/optional signal state fields.
- `backend/app/schemas/models.py` — `RawDocument.extraction_allowed`.
- `frontend/src/types/index.ts` — matching frontend type field.
- `backend/scripts/pricing_pressure_retrieval_audit.py` — pricing-only audit.
- `backend/scripts/demo_track2_ai_hardware_audit.py` — demo full-pipeline audit.
- `backend/scripts/full_pipeline_retrieval_quality_audit.py` — demo/full scope awareness.
- `PRICING_PRESSURE_FAILURE_ANALYSIS.md` — pre-fix pricing failure analysis.

## Architecture Impact

- LangGraph DAG changed: no.
- Node order changed: no.
- Existing agents removed or bypassed: no.
- Downstream agent logic changed: no methodology changes. Agent 3 is only protected from `extraction_allowed=false` metadata-only docs at the graph boundary.
- Schema/types changed: yes, `RawDocument.extraction_allowed`.
- Frontend changed: type-only, no UI redesign.

## Before Changes

Source artifacts:

- `pipeline_audit_artifacts/20260525T171824Z/`
- `pipeline_audit_artifacts/20260526T030015Z/pricing_pressure_failure_analysis.json`

Observed baseline:

- Pipeline quality_status: PARTIAL_PASS
- Facts after SAFE/FinBERT: 93
- Sources: 45
- Covered signals: 6/7
- Missing signal: pricing_pressure
- Overall zero-doc query rate: 0.537
- Pricing_pressure queries analyzed: 8
- Pricing_pressure zero-doc queries: 4/8
- Pricing_pressure zero-doc rate: 0.50

Main failure causes:

- Pricing queries were spread across the full 8-company domain instead of the demo companies.
- Several pricing queries used strict `site:` constraints that blocked useful fallback results.
- Some queries were too generic for pricing evidence and lacked concrete GPU/server terms.
- Fallback scoring reused source assumptions from the original query even when fallback broadened the search.

## Playbook Implemented

Pricing query generation now includes deterministic demo-scope playbook queries.

Nvidia terms:

- H100, H200, B200, Blackwell, L40S, A100, RTX PRO, GPU instance
- AWS, Azure, CoreWeave, Lambda Labs, RunPod

AMD terms:

- MI300, MI300X, MI325, MI325X, MI350, Instinct, EPYC AI server
- Azure, Oracle, Dell, Supermicro, relevant cloud/OEM availability

Supermicro terms:

- GPU server, AI server, rack-scale, Blackwell, H100, H200, B200, MI300, MI325, liquid cooling
- Supermicro product/IR pages, distributor/OEM availability, delivery timing

Market-level terms:

- GPU rental price changes
- Cloud GPU instance discounts
- AI server lead times
- GPU availability, shortage, oversupply

## Accepted Source Families

The final pricing-only audit accepted documents from playbook-aligned domains:

- Cloud pricing: `runpod.io`, `coreweave.com`, `azure.microsoft.com`, `blogs.oracle.com`
- OEM / company / IR: `ir.supermicro.com`, `amd.com`, `dell.com`
- Pricing/news context: `semianalysis.com`, `servethehome.com`

## Rejected Sources

The stricter URL scorer rejected noisy sources with explicit reasons:

- `pricing_source_family_mismatch`: off-playbook domains and generic GPU-price aggregators.
- `fallback:pricing_source_family_mismatch`: broadened fallback still outside allowed pricing families.
- `site_constraint_mismatch`: SERP result did not match explicit `site:` operator.
- `pricing_missing_hardware_terms`: pricing-looking page without AI hardware terms.
- `social_or_low_signal_page_not_allowed`: social/video-style pages.
- `tracking_or_email_redirect_url`: tracking or email redirect URLs.
- `forum_or_community_source_not_allowed`: forum/community pages.

## After Metrics

Pricing-only audit:

- Artifact: `pipeline_audit_artifacts/pricing_pressure_20260526T034324Z/`
- Pricing query count: 15
- Accepted pricing documents: 13
- Zero-doc pricing queries: 3
- Zero-doc pricing query rate: 0.20
- Full-text documents: 9
- Metadata-only documents: 0
- Estimated Bright Data calls: 31

Demo full-pipeline audit:

- Artifact: `pipeline_audit_artifacts/demo_track2_20260526T040110Z/`
- Report ID: `report_dfd5e69a3a42`
- quality_status: PASS
- quality_reasons: none
- Core signals covered: investor_signal, pricing_pressure, product_launch, supplier_risk
- Core signals missing: none
- Evidence count: 63
- Source count: 23
- Pricing_pressure document count: 18
- Pricing_pressure scored facts: 5
- Zero-doc query rate: 0.0833
- Pulse score: 44.3
- Pulse status: risk_rising
- Estimated Bright Data calls: 108

Note: the live demo audit generated 36 queries before the final query-cap polish. After the audit, Agent 1 was updated to trim accepted queries to `DEMO_MAX_QUERIES` while preserving signal/company coverage. A deterministic unit check verified a 45-query candidate set trims to 32 while preserving all 4 core signals, all 3 companies, and market coverage. I did not rerun the expensive full pipeline a third time just to remeasure the cap.

## Known Weaknesses

- Pricing_pressure now reaches the report, but confidence is still moderate: the top pricing signal used 2 sources with confidence 0.593.
- Some pricing playbook queries still return zero accepted documents, especially AMD Azure MI300X and Supermicro AMD Instinct availability.
- Metadata-only evidence path was implemented but not exercised in the final pricing audit because no accepted docs were metadata-only.
- Full 8-company mode was not retested in this sprint by design.
- Agent 3 can still extract non-pricing facts from pricing pages; the clean demo run succeeded, but pricing extraction quality remains a next-sprint target.
- `full_pipeline_retrieval_quality_audit.py` was not run after the demo audit because it would duplicate the same expensive end-to-end path. The demo audit is the authoritative Sprint 2 full-pipeline run.

## Next Recommended Sprint

1. Add pricing-focused Agent 3 extraction examples without changing the schema.
2. Add per-signal extraction yield telemetry: documents collected vs raw facts vs SAFE facts per signal.
3. Add cheaper cached/offline replay mode for full-pipeline audits.
4. Tighten provider-specific pricing playbook templates for AMD MI300X/MI325X and Supermicro AMD Instinct availability.
