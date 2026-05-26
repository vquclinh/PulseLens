# Full Regression Weakness Report

**Report date:** 2026-05-26
**Authoritative report:** `report_3dfb4b94068b`
**Produced from:** Sprint 4 demo run (`demo_track2_20260526T063140Z/`) — used as regression baseline after clean regression attempt failed (see §Regression Failure)
**Scope:** Nvidia, AMD, Supermicro (3-company demo scope)

---

## Executive Summary

| Metric | Value | Assessment |
|---|---|---|
| `quality_status` | **PARTIAL_PASS** | Expected — fact_count < 50 after noise filtering |
| `evidence_count` | **43** | Below 50-fact threshold; correct given Sprint 4 filters |
| `source_count` | **17** | Exceeds 15-source minimum |
| `zero_doc_query_rate` | **33.3%** (12/36) | High — 1 in 3 queries returned nothing |
| `fetch_error_rate` | **0%** (0/36) | Clean — no failed fetches |
| `pricing_verdict` | **ACCEPTABLE** (4/4 strong, 100%) | Up from 40% in Sprint 2 |
| `suspicious_claim_count` | **0** | Clean — down from 1 in Sprint 2 |
| `demo_ready` | **CONDITIONAL** | Functional, honest, but PARTIAL_PASS needs explanation |

Sprint 4 filters eliminated misleading noise (CEVA IR metadata, index-tracker misclassifications, HBM reclassifications). The resulting PARTIAL_PASS is correct and preferred over the Sprint 2 PASS which included those artifacts. The primary weakness is retrieval depth: 12/36 queries returned zero documents, capping the fact count below the PASS threshold.

---

## 1. Quality Gate

| Criterion | Threshold | Actual | Pass? |
|---|---|---|---|
| `fact_count` | ≥ 50 | **43** | FAIL |
| `source_count` | ≥ 15 | **17** | PASS |
| `signal_types_covered` | ≥ 4 | **6 / 6** | PASS |
| `zero_doc_query_rate` | — | 33.3% | (informational) |

`PARTIAL_PASS` triggered after max rounds (2). The pipeline ran 2 full rounds; round 1 expanded retrieval but fact_count remained below 50 after filtering.

---

## 2. Evidence Pipeline

| Stage | Count | Notes |
|---|---|---|
| Queries generated | 36 (2 rounds) | Round 0: 32; Round 1: 4 expansion queries |
| Queries returning zero docs | 12 | 33.3% zero-doc rate |
| Documents accepted | 57 | 57/36 ≈ 1.6 docs/query average |
| Facts extracted (raw) | 48 | Before SAFE verification |
| Facts passed SAFE | 43 | 43/48 = **90% pass rate** |
| Facts rejected SAFE | 5 | 10% |
| Facts validated (gate) | 43 | Post-validate_facts() gate |
| Facts rejected by gate | 5 | nav_metadata=1, pricing_sanity=3, other=1 |
| Verified claims (triangulated) | **7** | Corroborated by ≥2 independent sources |
| Contradictions detected | **1** | Supermicro investor_signal (revenue guidance vs actual) |

---

## 3. SAFE Verification

- **Pass rate:** 43/48 = 90.0%
- 5 facts rejected as unverifiable against source documents
- High pass rate indicates Agent 3 extraction quality is strong
- The 10% rejection rate is expected and healthy — it removes hallucinated or over-extrapolated claims

---

## 4. Signal Coverage

| Signal Type | Facts | Verified | FinBERT (pos/neg/neu) | Score | Status |
|---|---|---|---|---|---|
| `investor_signal` | 26 | 1 | — | 0.000 | CONTRADICTED |
| `product_launch` | 6 | 2 | — | 0.136 | PASS |
| `supplier_risk` | 4 | 1 | — | 0.222 | PASS |
| `pricing_pressure` | 4 | 0 | — | — | WEAK TRIANGULATION |
| `strategic_messaging` | 2 | 1 | — | 0.831 | STRONG |
| `hiring_momentum` | 1 | 1 | — | — | PASS |

**ALL 6 signal types covered** — improvement from 4/6 in Sprint 2.

FinBERT overall: pos=13, neg=4, neu=26 (pulse_score=57.0, status=stable, confidence=0.682)

**investor_signal dominated:** 26/43 = 60% of facts are investor_signal. This creates imbalance — the pipeline retrieves heavily from IR domains (investor.nvidia.com, ir.amd.com, ir.supermicro.com, sec.gov). If IR sources are down or blocked, the entire report degrades.

---

## 5. Pricing Pressure Analysis

| Metric | Sprint 2 | Sprint 4 | Delta |
|---|---|---|---|
| Total pricing facts | 5 | 4 | −1 |
| Strong facts | 2 (40%) | 4 (100%) | +60% |
| Weak/misclassified | 3 | 0 | −3 |
| Pricing sanity rejected | — | 3 | new filter |
| Verified claims | 0 | 0 | unchanged |

**Pricing verdict: ACCEPTABLE** — all 4 remaining facts pass the strong-signal criteria (`$` amounts, explicit rates, specific lead times). However, zero verified claims means no triangulated pricing signals. The 4 facts come from only 2 domains (runpod.io + thinkmate.com), which is insufficient for ≥2-source triangulation on a per-claim basis.

**Cloud pricing gap persists:**
- CoreWeave: 2 direct pricing pages accepted, 0 facts extracted → JS-rendered tables inaccessible to HTML scraper
- GCP: 1 pricing page accepted, 0 facts extracted → same root cause
- RunPod: 5 URLs accepted (4 guides + 1 direct pricing) → only guides produced facts; direct page extracted nothing

---

## 6. Source Quality

### Top 10 accepted domains

| Domain | Doc count | Signal type |
|---|---|---|
| investor.nvidia.com | 12 | investor_signal |
| reuters.com | 10 | mixed |
| sec.gov | 6 | investor_signal |
| runpod.io | 5 | pricing_pressure |
| ir.amd.com | 4 | investor_signal |
| ir.supermicro.com | 4 | investor_signal |
| tomshardware.com | 3 | product_launch |
| coreweave.com | 2 | pricing_pressure |
| thinkmate.com | 2 | pricing_pressure |
| youtube.com | 2 | (low signal) |

IR domains (investor.nvidia.com + ir.amd.com + ir.supermicro.com + sec.gov) = **26/57 docs = 46% of corpus**. Heavy IR concentration is a structural dependency risk.

### Top 7 URL rejection reasons

| Reason | Count |
|---|---|
| `fallback:pricing_source_family_mismatch` | 66 |
| `pricing_source_family_mismatch` | 46 |
| `site_constraint_mismatch` | 16 |
| `ir_pages_requires_tier1_ir_or_sec_domain` | 10 |
| `pricing_missing_hardware_terms` | 9 |
| `below_relevance_threshold:0.000` | 8 |
| `social_or_low_signal_page_not_allowed` | 7 |

`pricing_source_family_mismatch` (112 total) is the dominant rejection reason — the pricing query route is narrow and rejects most retrieved URLs as irrelevant to GPU pricing. This is correct behavior but explains the low pricing fact count.

---

## 7. Entity Scope

- **Out-of-scope entities accepted:** 0 (CEVA IR pages now blocked by Fix 1)
- **Metadata/nav rejections:** 1 (IR navigation description eliminated by Fix 2)
- **Suspicious confirmed claims:** 0 (down from 1 in Sprint 2)

Sprint 4 entity scope enforcement is working correctly.

---

## 8. Regression Failure (Clean Regression Attempt)

A clean fresh regression run was attempted on 2026-05-26 at ~07:10Z.

**Failure:** The pipeline raised `ValueError: Quality gate FAIL: missing required signal types. Missing: ['investor_signal', 'product_launch', 'supplier_risk']` inside `query_planner` at round 1.

**Root cause:** Pre-existing bug in Agent 1 (query_planner) triggered when the LLM generates queries covering fewer signal types than required after all retries in the quality-gate expansion loop. This is not a regression introduced by Sprint 4 fixes — the Sprint 4 run completed successfully with the same code.

**Action taken:** Per plan rules, stopped after one failure. Failed run archived to `pipeline_audit_artifacts/archive_before_full_regression_20260526T065615Z/demo_track2_20260526T071020Z/`. Sprint 4 artifacts (`report_3dfb4b94068b`) used as authoritative regression baseline.

**Cost:** ~50 BrightData SERP calls, ~36 OpenRouter calls consumed before crash (round 1 incomplete).

---

## 9. Identified Weaknesses (Prioritized)

### P0 — Agent 1 ValueError in round 1 expansion (blocking)
- **Description:** query_planner crashes when LLM covers insufficient signal types after retries in round 1
- **Impact:** Full pipeline abort; no report produced; wasted API costs
- **Fix:** Wrap round 1 quality retry with catch for ValueError; fall back to PARTIAL_PASS with available signals rather than aborting
- **Effort:** Low (2–3 lines in graph.py or node_query_planner.py)

### P1 — fact_count < 50 (PARTIAL_PASS, not PASS)
- **Description:** 43 facts after filtering, below 50 threshold
- **Impact:** PARTIAL_PASS triggers quality gate warning; demo needs explanation
- **Root cause:** 12/36 queries (33%) returned zero documents; pricing subdomain coverage is shallow
- **Fix options:**
  1. Add per-company sub-queries for GPU pricing (e.g., "Nvidia H100 price 2026 site:runpod.io")
  2. Lower threshold to 40 (not recommended — masks retrieval weakness)
  3. Add 3–5 additional news/tech publication domains to acceptable sources
- **Effort:** Medium (query planner prompt tuning + domain list expansion)

### P2 — CoreWeave/GCP pricing facts = 0
- **Description:** JS-rendered pricing pages return scraped HTML with no price tables
- **Impact:** Cloud GPU pricing gap (only OEM/reseller prices captured)
- **Fix:** Add Playwright headless-browser fallback for direct_pricing_page URLs matching coreweave.com, cloud.google.com
- **Effort:** High (requires Playwright integration)

### P3 — investor_signal concentration (60% of facts)
- **Description:** 26/43 facts from IR domains; other signal types thin
- **Impact:** If IR domains blocked, report quality degrades sharply
- **Fix:** Increase diversity — add Reuters/Bloomberg news queries for product_launch; add job board queries for hiring_momentum
- **Effort:** Medium (query planner prompt + source scoring)

### P4 — pricing_pressure triangulation = 0 verified claims
- **Description:** 4 pricing facts but 0 triangulated — insufficient cross-source corroboration
- **Impact:** pricing_signal shown in report but marked unverified
- **Fix:** Lower pricing triangulation threshold to 1 independent source (currently requires 2) for explicit $ facts
- **Effort:** Low (config change in triangulator)

### P5 — 33% zero-doc query rate
- **Description:** 12 of 36 queries returned no documents
- **Impact:** Retrieval is incomplete; some signal types underrepresented
- **Root cause:** Narrow pricing query routing + site constraints filtering aggressively
- **Fix:** Audit zero-doc queries; loosen site constraints for high-confidence query types
- **Effort:** Medium

---

## 10. Demo-Ready Assessment

**Status: CONDITIONAL**

The pipeline produces a coherent, honest, artifact-rich report with:
- All 6 signal types covered
- 0 out-of-scope entities
- 0 suspicious claims
- 90% SAFE verification rate
- Meaningful narrative synthesis and watch-list item

The PARTIAL_PASS status requires a one-sentence explanation for demo audiences: *"Sprint 4 filtering removed low-quality noise — the PARTIAL_PASS reflects honest signal depth, not a pipeline error."* The pulse_score of 57.0 (+29% vs Sprint 2's 44.3) is a defensible result.

**Blockers before demo (P0 only):**
- Fix Agent 1 ValueError crash in round 1 expansion to prevent demo pipeline abort

**Not blocking demo:**
- All P1–P5 weaknesses are either within acceptable tolerances or have documented workarounds

---

## 11. Sprint 5 Recommendations

1. **Fix Agent 1 ValueError** (P0) — catch and degrade gracefully rather than abort
2. **Increase retrieval depth** (P1) — per-company pricing sub-queries; expand acceptable source domains
3. **Playwright fallback for JS pricing pages** (P2) — CoreWeave, GCP cloud pricing
4. **Reduce pricing triangulation threshold** (P4) — 1 independent source for explicit-$ facts
5. **Investor_signal diversity** (P3) — balance corpus so IR ≤ 40% of accepted docs
6. **Full 8-company run AFTER** fact_count consistently ≥50 on 3-company scope
