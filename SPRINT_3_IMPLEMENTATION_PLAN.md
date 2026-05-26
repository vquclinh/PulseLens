# Sprint 3 Implementation Plan — Evidence Quality & Signal Semantics Audit

**Goal:** Verify that the system extracts the right *kinds* of facts for each signal type,
especially whether `pricing_pressure` facts are genuine pricing signals rather than index
announcements, availability pages, or generic market commentary.

---

## Pre-work

| Task | Done |
|---|---|
| Archive stale Sprint 3 artifacts (none found) | ✅ |
| Verify Sprint 2 authoritative artifacts intact | ✅ |
| Fix `AUTHORITATIVE_SPRINT_2_ARTIFACTS.md` — demo run was 3-company scope, not 8-company | ✅ |

**Documentation correction:** `demo_track2_20260526T040110Z` used `demo_scope_enabled: true` with
companies `["Nvidia", "AMD", "Supermicro"]`. The earlier description "Full 8-company pipeline run"
was a documentation typo, confirmed by reading `demo_scope_config.json`. Full-scope (8-company) run
not yet performed; cost would be ~3× more BrightData calls. Recommend doing only if Sprint 3 audit
confirms the 3-company baseline is clean first.

---

## Files to Create or Modify

| File | Change type | Scope |
|---|---|---|
| `backend/scripts/evidence_quality_audit.py` | **NEW** | audit-only |
| `backend/app/utils/url_scorer.py` | **MODIFY** | validation-only (add instagram.com to SOCIAL_MARKERS) |
| `backend/app/pipeline/agent3_fact_extractors.py` | **MODIFY** | extraction-prompt-only (add negative pricing examples) |
| `SPRINT_3_IMPLEMENTATION_PLAN.md` | **NEW** | plan |
| `AUTHORITATIVE_SPRINT_2_ARTIFACTS.md` | **MODIFY** | documentation fix |
| `EVIDENCE_QUALITY_SPRINT_3_REPORT.md` | **NEW** | report |
| `AUTHORITATIVE_SPRINT_3_ARTIFACTS.md` | **NEW** | report |

**LangGraph DAG changes:** NO — node order and graph topology unchanged.
**Downstream agent methodology changes:** NO — only Agent 3 prompt examples adjusted.
**Schema/types changes:** NO — Python and TypeScript types are already correct.
**Frontend changes:** NO.

---

## Safety Constraints Honored

- LangGraph DAG not modified
- Node order not changed
- No agents removed or bypassed
- Quality thresholds not lowered
- No evidence faked
- Frontend not redesigned
- Failures remain visible in telemetry
- metadata_only documents cannot become high-confidence claims (no change to existing guard)

---

## 1. Evidence Quality Audit Script

**File:** `backend/scripts/evidence_quality_audit.py`
**Type:** audit-only
**Cost:** Zero (reads from SQLite DB + existing artifact JSON files)

### Inputs
- `--report-id` — SQLite report ID (default: `report_dfd5e69a3a42`)
- `--artifact-dir` — artifact folder for context (default: `pipeline_audit_artifacts/demo_track2_20260526T040110Z/`)

### Outputs under `pipeline_audit_artifacts/evidence_quality_<timestamp>/`
- `evidence_quality_summary.json` — high-level pass/fail metrics
- `signal_semantics_audit.json` — per-signal-type breakdown
- `pricing_pressure_semantics_audit.json` — detailed per-fact pricing classification
- `suspicious_claims.json` — facts/claims with suspicious patterns
- `source_tier_quality_audit.json` — per-domain quality ratings
- `evidence_quality_run.log` — console-level log

---

## 2. Pricing Pressure Semantic Validation

**Strong pricing signals must contain at least one of:**
- Explicit price amount (e.g., "$2.49/hr", "$12,415.00")
- Percentage price change ("H100 prices rose 40%")
- Discount or promotional pricing
- On-demand/spot/reserved/rental rate
- Cost per hour/month/year
- Lead time explicitly tied to pricing/availability pressure
- Shortage or oversupply explicitly tied to price/cost
- Margin pressure from pricing dynamics
- Cloud GPU pricing comparison with specific $$ figures
- OEM/distributor pricing or availability signal with price or lead time

**Weak pricing signals (do NOT count as genuine pricing evidence):**
- "A pricing index was launched"
- "An index was announced"
- "A product is available" — without price or cost context
- "Prices may change" — no current figure
- Generic shortage narrative without price or dollar figure
- Memory shortage causing price pressure (on memory) → classify as supplier_risk, not pricing_pressure

**Classification labels:**
- `strong_pricing_signal` — satisfies at least one strong criterion above
- `weak_pricing_signal` — pricing-adjacent but no explicit price data
- `misclassified_pricing_signal` — not about pricing at all (e.g., memory shortage → supplier_risk)
- `insufficient_evidence` — claim too vague to classify

---

## 3. Per-Signal Semantics Audit

For each signal type, compute and report:
- `fact_count`
- `verified_claim_count`
- `average_confidence`
- `source_count`
- `top_domains`
- `suspicious_claim_count`
- `common_suspicious_patterns`

### Signal-specific sanity checks

| Signal | Must involve |
|---|---|
| `investor_signal` | earnings, revenue, margin, guidance, filings, stockholder events, analyst/investor info |
| `product_launch` | actual product, instance, platform, hardware, SKU, launch, availability, deployment |
| `supplier_risk` | shortage, dependency, supplier, HBM, foundry, memory, logistics, export controls |
| `pricing_pressure` | price, cost, rental, discount, lead-time, availability pressure with $ figure |
| `strategic_messaging` | company strategy, investment, partnership, roadmap, executive messaging |
| `news_sentiment` | external news coverage and market reaction |
| `hiring_momentum` | job postings, headcount, hiring, team expansion |

---

## 4. Source Quality Audit

Rate all accepted domains as one of:
- `authoritative` — SEC, IR pages, tier-1 journalism
- `acceptable` — tier-2/3 hardware media, cloud provider pages, tech journalism
- `weak_but_usable` — tier-4 specialized blogs, secondary news aggregators
- `suspicious_or_low_signal` — content farms, social media, metadata-only pages
- `reject_next_time_candidate` — wrong domain type accepted due to fallback

**Known risk domains to inspect:**
- `instagram.com` — accepted for supplier_risk in the demo run (missing from SOCIAL_MARKERS — fix)
- `enkiai.com` — tier-4 AI market intelligence blog
- `ceva-ip.com` — investor_signal claim extracted about CEVA (wrong entity/scope)
- `semianalysis.com` (newsletter.semianalysis.com) — Substack paywall; content may be partial
- `thinkmate.com` — OEM reseller, acceptable for pricing

---

## 5. Audit Metadata Fields

**Decision: Keep in audit artifacts only.** The `PipelineAuditSummary` model already exists and
is already stored in the report. Adding new fields to the schema now would require a migration
and frontend type update — low risk but unnecessary before the audit proves these metrics are
stable enough to be worth surfacing in the report.

Fields recorded in `evidence_quality_summary.json` only (not in report schema):
- `strong_pricing_signal_count`
- `weak_pricing_signal_count`
- `misclassified_signal_count`
- `suspicious_claim_count`
- `weak_source_count`

---

## 6. Targeted Fixes (post-audit)

### Fix A — `url_scorer.py`: Add `instagram.com` to SOCIAL_MARKERS
**Problem:** `instagram.com` URLs are being accepted through the supplier_risk pipeline
because `SOCIAL_MARKERS` only blocks `facebook.com`, `twitter.com`, `x.com/`,
`linkedin.com/pulse`, `linkedin.com/posts`.
**Fix:** Add `"instagram.com"` to `SOCIAL_MARKERS`.
**Risk:** Minimal — only blocks future Instagram URLs. No other behavior changes.

### Fix B — `agent3_fact_extractors.py`: Add negative pricing_pressure examples
**Problem:** Agent 3 is extracting "SemiAnalysis launched an H100 1-Year Rental Price Index"
as a `pricing_pressure` fact with confidence 1.00. Launching a price index is not itself a
pricing signal — it is a strategic/news event.
Also extracting HBM shortage → increased memory prices as `pricing_pressure` instead of
`supplier_risk`.
**Fix:** Add explicit negative examples to the prompt:
- Index/tracker launches → NOT pricing_pressure → strategic_messaging or news_sentiment
- Memory/HBM shortage causing memory price increases → NOT pricing_pressure → supplier_risk
- "Available with a starting price" without stating the price → NOT pricing_pressure
**Risk:** Prompt-only change. No schema or logic change. Does not affect other agents.

---

## 7. Verification Plan

| Check | When | Cost |
|---|---|---|
| Backend import check (`python -c "import app.utils.url_scorer"`) | After Fix A | Zero |
| Backend import check (`python -c "import app.pipeline.agent3_fact_extractors"`) | After Fix B | Zero |
| Run `evidence_quality_audit.py` against demo artifact | After audit script created | Zero (DB read) |
| Run `pricing_pressure_retrieval_audit.py` | ONLY if url_scorer domains changed | Low (BrightData) |
| Run `demo_track2_ai_hardware_audit.py` | ONLY if Agent 3 extraction logic changed and cost is justified | High (BrightData) |
| Frontend build (`npm run build`) | ONLY if frontend types changed | Zero |

**Frontend types are already correct** — `quality_status` and `quality_reasons` are already in
`frontend/src/types/index.ts` (lines 185–187). No frontend build needed.

---

## 8. Known Weaknesses Going In

Based on pre-audit analysis of the live DB facts:

1. **Pricing pressure score is -0.9717** — driven by a single FinBERT-negative claim about the
   SemiAnalysis index launch, which is a neutral/strategic event, not a price decline.

2. **Only 5 pricing_pressure facts** — 2 strong (thinkmate server prices), 2 weak (index launch,
   vague availability), 1 misclassified (HBM→memory price). True strong pricing evidence is thin.

3. **CEVA investor signal** — `market|investor_signal` claim extracted from ceva-ip.com (CEVA
   Semiconductor). CEVA is not in the demo scope. The URL was accepted via a fallback for an
   "AI hardware analyst reports" query, then Agent 3 extracted an irrelevant fact about CEVA's IR page.

4. **Intel product launch facts** — Intel is not in the demo scope, but Intel product facts are
   extracted from Supermicro documents (Supermicro supports Intel Xeon 6, Intel Gaudi 3).
   These are technically valid context claims about Supermicro's product portfolio.

5. **Supermicro GAAP Net Income $483,387** — This is the raw number from the SEC filing in
   thousands (i.e., ~$483M). The claim text is technically accurate but the raw figure without
   units context is misleading at first read.
