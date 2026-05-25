# Retrieval Quality Stabilization Report

Generated: 2026-05-26

## 1. Scope

This was a focused stabilization pass for retrieval honesty and diagnosability. I did not add new product features and did not weaken thresholds to force a green report.

Primary target areas:

- Agent 1 query validation, regeneration, and planning telemetry.
- Agent 2 URL routing, rejection, fallback, and Bright Data diagnostics.
- Quality Gate strict PASS / PARTIAL_PASS / FAIL_EXPAND behavior.
- Report-facing quality metadata and frontend type/display support.
- Config/env cleanup for FinBERT, SAFE, and quality thresholds.
- Rerunnable retrieval-quality audit script.

## 2. Files Changed

Core backend changes:

- `backend/app/config/quality_gates.py`
- `backend/.env.example`
- `backend/app/schemas/models.py`
- `backend/app/pipeline/state.py`
- `backend/app/pipeline/agent1_query_planner.py`
- `backend/app/pipeline/agent2_web_workers.py`
- `backend/app/utils/url_scorer.py`
- `backend/app/utils/brightdata_client.py`
- `backend/app/pipeline/node_quality_gate.py`
- `backend/app/pipeline/node_report_assembler.py`
- `backend/app/pipeline/graph.py`
- `backend/app/pipeline/agent4_finbert_scorer.py`
- `backend/app/pipeline/node_validate_and_split.py`
- `backend/app/api/report.py`
- `backend/scripts/full_pipeline_retrieval_quality_audit.py`

Frontend-facing/schema changes:

- `frontend/src/types/index.ts`
- `frontend/src/types/api.ts`
- `frontend/src/modules/dashboard/components/overview/pulse-score-card.tsx`
- `frontend/src/modules/about/pages/about-page.tsx`

Minor stale comment cleanup:

- `backend/app/utils/finbert_client.py`
- `backend/app/pipeline/agent5_contradiction_writer.py`

## 3. Exact Problems Found

### Problem A — Quality Gate pretended weak coverage was fine

Before this pass, the full run generated a report with `PASS` even though the previous run showed:

- Agent 2 returned zero documents for `17/40` queries.
- Bright Data returned `24` permanent HTTP fetch errors.
- Agent 2 discarded `41/84` fetched documents as low quality.
- The Quality Gate passed with only `5/7` signal types covered.

That was the central correctness bug: the pipeline could produce an apparently confident report even when retrieval coverage was visibly weak.

### Problem B — Agent 1 accepted too much LLM variability

Agent 1 did not have enough deterministic post-processing around malformed rows, empty required fields, duplicate or near-duplicate query text, unsupported signal types, disallowed raw/tracking URLs, or final coverage telemetry.

### Problem C — Agent 2 mixed discovery URLs and document URLs too loosely

Agent 2 needed clearer separation between:

- search query sent to SERP,
- result URL discovered from SERP,
- direct page fetch.

It also needed explicit rejection of search-engine URLs, tracking/email redirects, irrelevant domains, unsupported forum/social pages, and source-type mismatches.

### Problem D — Bright Data errors were too opaque

Several errors logged with little useful detail. This made it hard to distinguish bad URLs, zone problems, API payload problems, paywall/blocking, and transient network failures.

### Problem E — Final reports had no honest retrieval audit summary

The report schema did not surface whether the output was complete, partial, or failed. It also did not include query/document/fetch coverage counts for the frontend.

### Problem F — Configuration had stale or hard-coded values

FinBERT model, SAFE thresholds, and quality thresholds needed config/env control. Stale frontend copy referenced Claude even though the implementation uses OpenRouter with configured agent models.

## 4. Changes Made

### Agent 1

Implemented strict parsing and deterministic validation in `agent1_query_planner.py`.

Key behavior now:

- Rejects non-list LLM output.
- Rejects malformed rows.
- Rejects empty `target_entity`, `signal_type`, `source_type`, or `query_text`.
- Rejects unsupported signal types.
- Rejects unsupported source types.
- Rejects unknown entities.
- Rejects raw/tracking URLs in search query text.
- Rejects missing time anchors.
- Rejects invalid priority/tier fields.
- Rejects duplicate or near-duplicate query text.
- If rejected query rate exceeds `AGENT1_MAX_MALFORMED_QUERY_RATE` default `0.10`, Agent 1 asks the LLM once for replacement queries only.
- Records `query_planner_audit` with per-round telemetry.

Relevant code:

- `backend/app/pipeline/agent1_query_planner.py:469`
- `backend/app/pipeline/agent1_query_planner.py:556`
- `backend/app/pipeline/agent1_query_planner.py:659`

### Agent 2

Hardened URL handling and routing.

Key behavior now:

- SERP discovery and direct page fetch are separate.
- Google/search-engine result URLs are rejected.
- Bloomberg email tracking and `links.message.*` style redirects are rejected.
- `site:` constraints are enforced.
- Forum/community pages are rejected unless the source type explicitly allows community pages.
- `ir_pages` requires Tier 1 IR/SEC/company-domain style sources.
- `job_pages` prefers careers/jobs pages.
- Pricing pages require market/pricing relevance.
- Short tickers use word-boundary matching so `MU` does not match words like `communications`.
- Cache key includes `source_type`.
- Tier 2 blocked/paywalled sources can be kept as `metadata_only` when useful snippet metadata exists.
- Each zero-doc query gets one bounded fallback pass with two fallback searches.

Relevant code:

- `backend/app/pipeline/agent2_web_workers.py:137`
- `backend/app/pipeline/agent2_web_workers.py:263`
- `backend/app/pipeline/agent2_web_workers.py:409`
- `backend/app/utils/url_scorer.py:117`
- `backend/app/utils/url_scorer.py:200`

### Bright Data Diagnostics

Improved Bright Data logging and fixed a live API payload bug discovered during verification.

Key behavior now:

- Logs URL, zone, attempt number, exception class, exception message, HTTP status, and response snippet.
- `BrightDataError` includes structured error details.
- `render_js=True` now sends `"render": true`; the previous payload shape caused Bright Data `400` errors.
- Fetch telemetry summarizes total attempts, successes, failures, permanent failures, domains, and reasons.

Relevant code:

- `backend/app/utils/brightdata_client.py:108`
- `backend/app/utils/brightdata_client.py:120`
- `backend/app/utils/brightdata_client.py:133`
- `backend/app/pipeline/agent2_web_workers.py:529`

### Quality Gate

Replaced permissive pass/fail behavior with strict statuses:

- `PASS`
- `FAIL_EXPAND`
- `PARTIAL_PASS`

Defaults now come from `backend/app/config/quality_gates.py`:

- `QUALITY_MIN_FACTS=50`
- `QUALITY_MIN_SIGNAL_TYPES=7`
- `QUALITY_MIN_COMPANY_COVERAGE_RATIO=0.75`
- `QUALITY_MAX_ZERO_DOC_QUERY_RATE=0.35`
- `QUALITY_MAX_FETCH_ERROR_RATE=0.35`
- `QUALITY_MIN_SOURCE_COUNT=15`

Important behavior:

- `FAIL_EXPAND` is used only while expansion rounds remain.
- `PARTIAL_PASS` is used after max rounds are exhausted but useful evidence exists.
- `PASS` is used only when all strict thresholds pass.
- Quality diagnostics are stored in state.

Relevant code:

- `backend/app/config/quality_gates.py:31`
- `backend/app/pipeline/node_quality_gate.py:14`
- `backend/app/pipeline/node_quality_gate.py:79`
- `backend/app/pipeline/node_quality_gate.py:99`

### LangGraph Integration

The graph now carries retrieval telemetry through the pipeline.

Key behavior:

- Agent 1 writes `pending_queries` for the current round.
- Agent 2 reads `pending_queries` first so expansion does not refetch the entire previous query set.
- Query planner audit, web collection audit, and fetch summary are merged across rounds.
- Quality Gate loops back to Agent 1 only on `FAIL_EXPAND`.

Relevant code:

- `backend/app/pipeline/graph.py:34`
- `backend/app/pipeline/graph.py:74`
- `backend/app/pipeline/graph.py:101`
- `backend/app/pipeline/graph.py:308`

### Report Metadata

`MarketPulseReport` now includes:

- `quality_status`
- `quality_reasons`
- `audit_summary`

If the report is `PARTIAL_PASS`:

- `pulse_confidence` is capped at `0.5`.
- The grounded brief says coverage is incomplete.
- The market narrative is prefixed with a visible coverage warning.

Relevant code:

- `backend/app/schemas/models.py:35`
- `backend/app/schemas/models.py:166`
- `backend/app/schemas/models.py:178`
- `backend/app/pipeline/node_report_assembler.py:99`
- `backend/app/pipeline/node_report_assembler.py:137`
- `backend/app/pipeline/node_report_assembler.py:170`

### Frontend-Facing Support

Updated TypeScript model types and displayed partial coverage in the pulse card.

Relevant code:

- `frontend/src/types/index.ts:27`
- `frontend/src/types/index.ts:154`
- `frontend/src/types/index.ts:166`
- `frontend/src/modules/dashboard/components/overview/pulse-score-card.tsx:70`

### Focused Audit Script

Added `backend/scripts/full_pipeline_retrieval_quality_audit.py`.

It runs the full pipeline once and writes:

- `query_planner_audit.json`
- `web_collection_audit.json`
- `quality_gate_audit.json`
- `fetch_error_summary.json`
- `final_report_quality_summary.json`
- `pipeline_run.log`

Relevant code:

- `backend/scripts/full_pipeline_retrieval_quality_audit.py:87`
- `backend/scripts/full_pipeline_retrieval_quality_audit.py:135`
- `backend/scripts/full_pipeline_retrieval_quality_audit.py:143`

## 5. Before / After Metrics

### Before

From `FULL_PIPELINE_TEST_REPORT.md`:

| Metric | Before |
| --- | ---: |
| Final verdict | `PASS` |
| Query count | 40 |
| Raw documents | 43 |
| Raw facts | 79 |
| Facts after validate_fact | 72 |
| Facts after SAFE | 60 |
| Covered fact signal types | 5/7 |
| Zero-doc queries | 17/40 |
| Permanent HTTP fetch errors | 24 |
| Low-quality docs discarded | 41/84 |
| Quality gate behavior | Passed despite weak coverage |

### After

Focused audit artifact:

`pipeline_audit_artifacts/20260525T171824Z/`

| Metric | After |
| --- | ---: |
| Final quality_status | `PARTIAL_PASS` |
| Quality reasons | `signal_types 6 < 7`; `zero_doc_query_rate 0.54 > 0.35` |
| Query count | 54 |
| Accepted documents | 85 |
| Raw facts extracted | 123 |
| Facts after validate_fact | 121 |
| Facts after SAFE / FinBERT | 93 |
| Verified claims | 14 |
| Covered signal types | 6/7 |
| Missing signal types | `pricing_pressure` |
| Company coverage | 1.0 |
| Source count | 45 |
| Zero-doc queries | 29/54 |
| Zero-doc query rate | 0.537 |
| Fetch attempts | 63 |
| Successful fetches | 61 |
| Failed fetches | 2 |
| Fetch error rate | 0.0317 |
| Permanent failures | 0 |
| Top failed domains | `finance.yahoo.com`, `perplexity.ai` |
| Top failure reasons | `http_502`, `timeout` |

Interpretation:

The run is not perfect, and the system now says so. The pipeline collected enough evidence to produce a usable report, but retrieval still failed to cover `pricing_pressure` and the zero-doc rate stayed above the strict threshold. Therefore `PARTIAL_PASS` is correct.

## 6. Verification Commands

All commands below completed successfully.

```bash
cd backend
.venv/bin/python -m compileall -q app scripts
```

Result: exit `0`.

```bash
cd backend
.venv/bin/python -c "from app.pipeline.graph import pipeline_graph; print('backend imports OK')"
```

Result: exit `0`, printed `backend imports OK`.

```bash
cd frontend
npm run build
```

Result: exit `0`. Vite emitted only the existing chunk-size warning for the main JS bundle.

```bash
cd backend
.venv/bin/python scripts/full_pipeline_retrieval_quality_audit.py
```

Result: exit `0`. Artifacts saved to `pipeline_audit_artifacts/20260525T171824Z/`.

## 7. Remaining Known Weaknesses

### Pricing pressure retrieval is still weak

The final run missed `pricing_pressure` facts entirely. The strict URL rules are doing their job, but the current pricing queries still return many zero-doc outcomes. This is now visible instead of hidden.

Recommended next fix:

- Build a specific pricing-source allowlist/playbook for cloud GPU prices, server distributors, vendor SKU pages, procurement/news coverage, and availability/lead-time pages.

### Zero-doc rate is still too high

The final zero-doc query rate was `0.537`, above the `0.35` threshold. The system correctly returned `PARTIAL_PASS`.

Recommended next fix:

- Analyze `web_collection_audit.json` by source type and rewrite query templates that consistently produce no accepted documents.

### Fallback queries often conflict with strict `site:` expectations

Top rejection reasons included:

- `fallback:site_constraint_mismatch`
- `site_constraint_mismatch`
- `ir_pages_requires_tier1_ir_or_sec_domain`

Recommended next fix:

- When fallback queries intentionally remove strict `site:` filters, also evaluate fallback results against a fallback-specific routing policy instead of the original source-type/site constraint in every case.

### Agent 3 reprocesses accumulated documents after expansion

After the expansion pass, Agent 3 extracted again across all accumulated documents. This is reliable but expensive.

Recommended next fix:

- Track `pending_documents` or processed `doc_id`s so Agent 3 extracts facts only from newly added documents, then merges facts safely.

### SAFE is expensive and chatty

SAFE verification made many OpenRouter calls. This improves factual safety, but latency/cost is high.

Recommended next fix:

- Batch atomic verification per document or per small fact group while keeping fail-closed behavior.

### LangGraph checkpoint serialization warnings are not fully fixed

The focused audit script avoids checkpoint state reads that previously triggered unregistered Pydantic/Enum deserialization warnings. However, `graph.py` still uses `MemorySaver` with Pydantic models in state.

Recommended next fix:

- Convert graph-boundary state to JSON-serializable dict/list/scalars, or configure LangGraph serde allowlists deliberately.

## 8. Verdict

Stabilization result: **successful but not perfect**.

The pipeline now behaves honestly:

- It expands once when strict coverage fails.
- It returns `PARTIAL_PASS` after max expansion when coverage is still incomplete.
- It surfaces exact quality reasons in state and final report metadata.
- It preserves useful evidence instead of failing the whole run silently.
- It generates rerunnable artifacts for debugging retrieval quality.

Current readiness:

- Ready to continue improving retrieval quality.
- Not ready to treat every generated MarketPulseReport as fully complete.
- The next bottleneck is pricing-pressure source/query design, not LangGraph wiring.
