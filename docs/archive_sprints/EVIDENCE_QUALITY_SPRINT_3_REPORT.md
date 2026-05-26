# Evidence Quality & Signal Semantics Audit — Sprint 3 Report

**Date:** 2026-05-26
**Authoritative artifact analyzed:** `pipeline_audit_artifacts/demo_track2_20260526T040110Z/`
**Report ID:** `report_dfd5e69a3a42`
**Scope:** 3-company demo scope (Nvidia, AMD, Supermicro), `demo_scope_enabled: true`

---

## Documentation Correction (Pre-Sprint Fix)

`AUTHORITATIVE_SPRINT_2_ARTIFACTS.md` previously stated "Full 8-company pipeline run" for
the demo artifact. **This was incorrect.** The run used `demo_scope_enabled: true` with
companies `["Nvidia", "AMD", "Supermicro"]` — confirmed from `demo_scope_config.json`.

**Fixed before starting Sprint 3.** Full 8-company run has not been executed yet.

---

## Files Changed

| File | Change type | Change |
|---|---|---|
| `backend/scripts/evidence_quality_audit.py` | NEW | audit-only script |
| `backend/app/utils/url_scorer.py` | MODIFY | validation-only: add `instagram.com` to SOCIAL_MARKERS |
| `backend/app/pipeline/agent3_fact_extractors.py` | MODIFY | extraction-prompt-only: add negative pricing_pressure examples |
| `AUTHORITATIVE_SPRINT_2_ARTIFACTS.md` | MODIFY | documentation fix: 3-company not 8-company |
| `SPRINT_3_IMPLEMENTATION_PLAN.md` | NEW | plan document |
| `EVIDENCE_QUALITY_SPRINT_3_REPORT.md` | NEW | this report |
| `AUTHORITATIVE_SPRINT_3_ARTIFACTS.md` | NEW | artifact index |

**LangGraph DAG changed:** NO
**Schema/types changed:** NO
**Frontend changed:** NO

---

## Pricing Pressure Semantic Audit Results

**5 pricing_pressure facts extracted** from 3 unique source domains.

| Fact | Entity | Conf | Label | Reason |
|---|---|---|---|---|
| "SemiAnalysis launched an H100 1-Year Rental Price Index on April 2, 2026." | market | 1.00 | `weak_pricing_signal` | Index launch ≠ price data; no price figure stated |
| "AI's demand for HBM is shrinking PC and phone supply, leading to increased prices." | market | 0.90 | `misclassified_pricing_signal` | HBM/memory shortage → should be `supplier_risk` |
| "A 1U SuperServer 112B-WR…has a starting price of $12,415.00." | Supermicro | 0.90 | `strong_pricing_signal` | Explicit $price from OEM reseller |
| "A 1U SuperServer 512B-WR…has a starting price of $12,288.00." | Supermicro | 0.90 | `strong_pricing_signal` | Explicit $price from OEM reseller |
| "A 2U SuperServer 522B-WR…is available with a starting price." | Supermicro | 0.80 | `weak_pricing_signal` | States price exists but does not give the figure |

**Summary:** 2 strong / 2 weak / 1 misclassified

**Verdict: WEAK** — only 40% of pricing_pressure facts are genuine pricing signals.
The pricing_pressure signal score of **-0.9717** in the demo report is driven primarily
by the SemiAnalysis "index launch" claim, which FinBERT scored as negative but is
actually a neutral/strategic event. True pricing signals are thin (2 Supermicro list prices
from a single OEM reseller page).

**Root cause:** Agent 3 previously had no guidance distinguishing "a pricing index was
launched" from "GPU prices changed." The prompt fix added explicit negative examples.
Effect will be visible in the next pipeline run.

---

## Per-Signal Semantics Audit Results

| Signal | Facts | Claims | Avg Conf | Sources | Suspicious |
|---|---|---|---|---|---|
| `investor_signal` | 19 | 2 | 0.97 | 4 | 3 |
| `strategic_messaging` | 18 | 2 | 0.89 | 4 | 15 |
| `product_launch` | 17 | 3 | 0.91 | 9 | 2 |
| `pricing_pressure` | 5 | 1 | 0.90 | 3 | 0 |
| `supplier_risk` | 4 | 2 | 0.88 | 3 | 0 |
| `hiring_momentum` | 0 | 0 | 0.00 | 0 | 0 |
| `news_sentiment` | 0 | 0 | 0.00 | 0 | 0 |

### Signal-by-signal notes

**investor_signal (19 facts, 3 suspicious):**
- Dominated by AMD Q1 2026 earnings and Supermicro quarterly results — appropriate.
- 3 suspicious: CEVA investor_signal ("Ceva provides investor relations information…"), two
  SEC EDGAR browse pages with no specific financial claim extracted. CEVA is not in the demo
  scope — see Source Quality section.
- Supermicro GAAP Net Income `$483,387` — raw SEC filing figure in thousands (~$483M actual).
  The claim is technically accurate but lacks the "(in thousands)" unit context.

**strategic_messaging (18 facts, 15 suspicious via vocab check):**
- The vocab-based check flags 15 claims that lack explicit strategy vocabulary terms
  ("strategy", "investment", "partnership", "roadmap", "ceo" etc.).
- Example false-positive: "AMD plans to invest over $10 billion in the Taiwan ecosystem" —
  contains "invest" but not "investment" (exact substring). This is a vocab list precision
  issue in the audit tool, not a true pipeline problem.
- True concerns: some claims read more like product descriptions ("AMD's product portfolio
  includes AI accelerators, CPUs…") than strategic messaging.

**product_launch (17 facts, 2 suspicious):**
- Two Intel product launch facts extracted from Supermicro documents (Intel Xeon 6, Gaudi 3).
  Intel is not in demo scope but facts are technically valid — Supermicro's product lineup
  includes Intel-based servers. Entity normalization assigns these to "Intel" not "Supermicro".
  Considered acceptable context.

**supplier_risk (4 facts, 0 suspicious):**
- HBM shortage and NVIDIA supply chain risk claims — appropriate.
- The HBM memory price fact (`misclassified_pricing_signal` in pricing audit) is
  correctly labeled `supplier_risk` in the signal breakdown. The problem was it was *also*
  extracted as a duplicate `pricing_pressure` fact from the same source.

**hiring_momentum / news_sentiment (0 facts each):**
- Neither signal was targeted in the demo scope query plan. Expected and acceptable.

---

## Source Quality Audit Results

12 unique domains across 63 facts.

| Domain | Rating | Facts | Notes |
|---|---|---|---|
| `ir.amd.com` | authoritative | 25 | SEC/IR tier-1 — AMD earnings, SEC filings |
| `ir.supermicro.com` | authoritative | 14 | SEC/IR tier-1 — Supermicro earnings |
| `thinkmate.com` | weak_but_usable | 7 | OEM reseller — all 3 pricing facts from here |
| `sec.gov` | authoritative | 4 | SEC filings — NVIDIA 10-K |
| `servethehome.com` | acceptable | 2 | Tier-3 hardware journalism |
| `newsletter.semianalysis.com` | weak_but_usable | 2 | Substack newsletter (possible paywall) |
| `tomshardware.com` | acceptable | 2 | Tier-3 hardware journalism |
| `enkiai.com` | weak_but_usable | 2 | Tier-4 AI market blog |
| `amd.com` | acceptable | 2 | Company press releases |
| `blogs.oracle.com` | acceptable | 1 | Oracle cloud blog |
| **`instagram.com`** | **suspicious_or_low_signal** | **1** | supplier_risk fact — social media; URL filtered going forward |
| **`ceva-ip.com`** | **reject_next_time_candidate** | **1** | CEVA Semiconductor IR page — out of scope |

**Rating summary:**
- authoritative: 3 domains (43 facts — 68% of all facts)
- acceptable: 4 domains (8 facts)
- weak_but_usable: 3 domains (11 facts)
- suspicious_or_low_signal: 1 domain (instagram.com — 1 fact)
- reject_next_time_candidate: 1 domain (ceva-ip.com — 1 fact)

**Instagram finding:** `instagram.com/p/DVpgwM-jEz0/` was accepted for an HBM shortage
query because Instagram was missing from `SOCIAL_MARKERS` in `url_scorer.py`. **Fixed.**
Going forward, Instagram URLs will be blocked at the hard-rejection stage.

**CEVA finding:** `ceva-ip.com` accepted via fallback for "AI hardware analyst reports
Bloomberg" query. The Agent 3 extraction yielded "Ceva provides investor relations
information…" — a metadata description, not a financial fact. This is a false positive
from the fallback triggering on a wrong-scope domain. The URL scorer already had a
below-relevance-threshold check (0.287 score) for two other candidates; CEVA slipped
through because `fallback:accepted` reason indicates it was accepted by the fallback
without scoring. The query should produce a zero-doc result rather than fall back to CEVA.

---

## Suspicious Claims Found

**1 confirmed suspicious claim:**

```
entity: market
signal_type: investor_signal
claim: "Ceva provides investor relations information including financial results, SEC filings,
        earnings webcasts…"
source: ceva-ip.com
reason: IR page metadata extracted as fact (pattern: "provides investor relations information")
```

This claim has zero financial content — it is a description of CEVA's IR page. Agent 3
should not have extracted it (rules say: "Do NOT infer, interpret, or add information not
present"). The issue is that the document itself was mostly an IR navigation page
(`metadata_only` quality), and Agent 3 extracted a description of the page structure as a
"fact." **Root cause:** the `metadata_only` document guard exists in the pipeline but
`ceva-ip.com` was not flagged as out-of-scope at retrieval time (see CEVA finding above).

---

## Fixes Applied

### Fix 1 — `url_scorer.py`: Instagram added to SOCIAL_MARKERS
**File:** `backend/app/utils/url_scorer.py:62`
**Change:** Added `"instagram.com"` to `SOCIAL_MARKERS` list.
**Effect:** Instagram URLs now rejected at hard-rejection stage for all query types.
**Risk:** Minimal — blocks only Instagram. No other behavior changes.

### Fix 2 — `agent3_fact_extractors.py`: Negative pricing_pressure prompt examples
**File:** `backend/app/pipeline/agent3_fact_extractors.py`
**Change:** Added `PRICING_PRESSURE SIGNAL RULES` section to the system prompt with:
  - Definition of what qualifies as a strong pricing signal (explicit $/rate/% change)
  - Six explicit "DO NOT use pricing_pressure for" patterns with redirect signal_types
**Effect:** Future extractions should:
  - Classify "index launch" claims as `strategic_messaging` or `news_sentiment`
  - Classify HBM/memory shortage → price claims as `supplier_risk`
  - Avoid "available with a starting price" (no $) as `pricing_pressure`
**Risk:** Prompt-only change. Does not affect other agents. Cannot be validated without
re-running extraction — validation deferred to next full pipeline run.

---

## Metrics Before/After

| Metric | Sprint 2 (demo run) | Sprint 3 post-fix |
|---|---|---|
| pricing_pressure strong facts | 2 / 5 (40%) | Expected to improve — needs new run to confirm |
| Instagram URLs blocked | No (missing from SOCIAL_MARKERS) | Yes (fixed) |
| Agent 3 pricing index misclassification | Possible | Guidance added to prompt |
| Suspicious confirmed claims | 1 (CEVA IR metadata) | 1 (existing data, unchanged) |
| Backend imports passing | Yes | Yes |

---

## Remaining Weaknesses

1. **Pricing coverage is thin.** Only 2 genuine strong pricing facts (both from a single
   OEM reseller, thinkmate.com). Cloud provider pricing pages (CoreWeave, RunPod, GCP)
   were fetched but yielded zero pricing_pressure extractions. The documents may be
   listing pages without explicit per-GPU rates, or Agent 3 failed to extract them.
   Root cause needs verification in next run.

2. **pricing_pressure signal score (-0.9717) is driven by a weak claim.** The SemiAnalysis
   "index launch" claim scored high confidence (1.00) and FinBERT-negative, making it the
   dominant signal driver. With the prompt fix, this fact should not be extracted as
   `pricing_pressure` in the next run — but the underlying signal score will then depend
   entirely on the 2 Supermicro list prices and the HBM claim (if reclassified to
   supplier_risk). The score direction may shift significantly.

3. **CEVA out-of-scope fallback.** The fallback for "AI hardware analyst reports" queries
   should not accept CEVA's IR page. Fix requires either adding CEVA to a domain blocklist
   or requiring entity-match validation at the query fallback level. Not fixed this sprint
   (no safe hook without schema change).

4. **strategic_messaging fact quality is mixed.** 18 facts extracted but some are general
   product/portfolio descriptions ("AMD's product portfolio includes…") that lack explicit
   strategic messaging content. These are not wrong per se, but they weaken the signal
   quality for the strategic_messaging bucket.

5. **No hiring_momentum or news_sentiment coverage.** These are `optional_signal_types`
   in demo scope — acceptable but should be flagged for the full-scope run.

6. **Intel entity appearing in demo scope facts.** Intel product launch facts extracted
   from Supermicro documents. This is technically valid context but should be noted for
   entity scope filtering in a full 8-company run.

---

## Next Recommended Sprint

**Sprint 4: Pricing Coverage Depth + Entity Scope Enforcement**

Priority tasks:
1. Re-run demo pipeline with the Agent 3 prompt fix and compare `pricing_pressure` fact
   quality. Check whether cloud provider documents (CoreWeave, RunPod, GCP pricing pages)
   now yield strong pricing facts. Cost: 1 demo run (~108 BrightData calls).
2. Investigate why CoreWeave/RunPod/GCP accepted docs produced zero pricing_pressure facts.
   Check document content quality and Agent 3 extraction behavior.
3. Add entity-scope validation at the URL fallback level to prevent out-of-scope domains
   (CEVA, etc.) from being accepted when the query target entity has no connection to the domain.
4. Consider a post-extraction signal-sanity filter: for each fact, check whether the entity
   in the fact is in the demo scope list, and flag or discard out-of-scope entities.
5. Full 8-company run only after single-company pricing coverage is confirmed clean.
