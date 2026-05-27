# Agent 1 Signal Distribution Audit — Sprint 7

**Date:** 2026-05-26
**Purpose:** Diagnose why Sprint 6 Retry signal distribution collapsed vs Sprint 5.

---

## Query Budget (Demo Scope)

From `demo_scope.py` lines 69-70:
- `scope.min_queries = 22`, `scope.max_queries = 32` (env var defaults)
- With 15 pricing playbook seeds: `llm_min = max(8, 22-15) = 8`, `llm_max = max(8, 32-15) = 17`
- **LLM generates 8–17 queries** (the "8 to 17 LLM-generated queries" in the log)
- Total round 0: 23-32 queries

---

## Sprint 5 Signal Distribution

### Query planner audit (from `sprint5_review_bundle_20260526T081013Z/query_planner_audit.json`)

Round 0 LLM generated: 29 raw queries → 32 accepted (after +15 seeds, dedup)
Round 1 expansion LLM generated: 7 queries → 10 accepted (gap-fill)
Total: **42 queries**

Round 0 signal distribution (inferred from evidence):
- investor_signal: ~5-7 LLM queries
- product_launch: ≥3 LLM queries (minimum met)
- supplier_risk: ≥2 LLM queries (minimum met)
- pricing_pressure: 15 deterministic playbook

### Evidence domain distribution (Sprint 5)

| Signal type | Facts | Top domains |
|---|---|---|
| investor_signal | 13 | ir.supermicro.com(7), investor.nvidia.com(2), medium.com(2), sec.gov(1), ir.amd.com(1) |
| product_launch | 14 | ir.amd.com(9), servethehome.com(2), anandtech.com(1), amd.com(1), ir.supermicro.com(1) |
| pricing_pressure | 5 | runpod.io(3), blogs.oracle.com(1), thinkmate.com(1) |
| supplier_risk | 2 | digitimes.com(1), ir.amd.com(1) |
| strategic_messaging | 6 | reuters.com(2), servethehome.com(2), ir.amd.com(2) |
| Total | 40 | 19 source domains |

**Key Sprint 5 insight:** `ir.amd.com` was spread across product_launch(9), strategic_messaging(2),
supplier_risk(1), investor_signal(1). The SAME domain contributed DIFFERENT signal types because
different sub-pages were retrieved in Sprint 5:
- Press release pages → product_launch facts
- Strategic update pages → strategic_messaging facts
- Quarterly report pages → investor_signal facts

---

## Sprint 6 Retry Signal Distribution

### Pipeline run (from log `pipeline_audit_artifacts/demo_track2_20260526T155555Z/`)

Round 0 LLM generated: 36 raw queries → 32 accepted (Trimmed from 36 to 32)
No expansion round needed (max rounds reached at round 1)
Total: **32 queries**

### Evidence domain distribution (Sprint 6 Retry — REGRESSED)

| Signal type | Facts | Top domains |
|---|---|---|
| investor_signal | 29 | ir.amd.com(13), sec.gov(8), seekingalpha.com(5), ifp.org(2), bloomberg.com(2) |
| supplier_risk | 3 | (not audited in detail) |
| product_launch | 1 | amd.com(1) |
| pricing_pressure | 1 | (not audited) |
| Total | 34 | 9 source domains |

**Key Sprint 6 Retry finding:** `ir.amd.com` contributed 13 investor_signal facts (vs 1 in Sprint 5).
The LLM generated queries targeting AMD quarterly earnings pages, SEC EDGAR filings, investor.amd.com
— all investor-heavy content. The product_launch queries also targeted AMD IR pages, but those
pages were AMD quarterly reports (investor content) rather than product announcement pages.

---

## Root Cause: Same Domain, Different Sub-Pages

`ir.amd.com` is a multi-purpose domain:
- `ir.amd.com/news/press-releases/` → product launch announcements → product_launch facts
- `ir.amd.com/news-events/financial-releases/` → quarterly earnings → investor_signal facts
- `ir.amd.com` root → strategic company updates → mixed signals

**In Sprint 5:** The LLM generated queries like "AMD MI325X product announcement ir.amd.com" which
retrieved press-release sub-pages → 9 product_launch facts from ir.amd.com.

**In Sprint 6 Retry:** The LLM generated queries like "AMD Q1 2026 revenue earnings ir.amd.com"
which retrieved quarterly report sub-pages → 13 investor_signal facts from ir.amd.com.

Both satisfy the product_launch minimum (≥3 queries generated) and investor_signal minimum (≥5).
The failure is invisible at the QUERY level — it appears only at the EVIDENCE level.

---

## Signal-Specific Source Domain Analysis

| Signal type | Should target | Should NOT target |
|---|---|---|
| investor_signal | sec.gov, ir.company.com, investor.company.com, earnings transcripts | Product pages, tech review sites |
| product_launch | company.com/news, newsroom, servethehome.com, anandtech.com, tomshardware.com | IR quarterly reports, SEC filings |
| supplier_risk | reuters.com, bloomberg.com, digitimes.com, techinsights.com | IR pages, pricing sites |
| pricing_pressure | runpod.io, lambdalabs.com, thinkmate.com, servethehome.com | IR pages, earnings |
| strategic_messaging | ir.company.com newsroom, earnings calls, investor days | Not applicable |

**The `_MULTIHYDE_SYSTEM` prompt currently has NO rule about signal-specific source domains.**
It says "Use site: operators from company metadata" but does not prevent investor_signal queries
from targeting the SAME IR sub-pages that product_launch queries should target exclusively.

---

## LLM vs Deterministic Query Counts

| Source | Sprint 5 round 0 | Sprint 6 Retry round 0 |
|---|---|---|
| Pricing playbook (deterministic) | 15 | 15 |
| LLM-generated | ~17 | ~17 |
| Total | 32 | 32 |
| Signal coverage | 4 types present | 4 types present |
| Source diversity | 19 domains | 9 domains |

The query COUNTS were similar. The DOMAIN DIVERSITY collapsed because LLM signal types converged
on the same sub-domain (AMD quarterly reports). This is not detectable from query counts alone.

---

## Why Targeted Regeneration Was Not Triggered in Sprint 6 Retry

The existing `_enforce_final_quality` signal_minimums check:
- product_launch minimum: 3. Sprint 6 Retry had ≥3 product_launch queries → no ValueError → no retry
- investor_signal minimum: 5. Sprint 6 Retry had ≥5 investor_signal queries → no ValueError → no retry

The quality gates PASSED at the query-planning level, but the retrieved documents failed to
produce diverse evidence because the queries targeted a homogeneous source domain.

---

## Sprint 7 Fix Required

1. **Prompt-level (B2):** Add source-domain specificity rules to `_MULTIHYDE_SYSTEM`. Force
   product_launch queries to target newsrooms/tech-review sites, NOT IR pages. Force supplier_risk
   to target reuters/bloomberg.

2. **Cap-level (B1, B3):** Add `_DEMO_SIGNAL_QUERY_CAPS` to prevent investor_signal from
   exceeding 7 LLM queries. This is a structural backstop even if the prompt is ignored.

3. **Demo minimums (B1, B4):** Raise product_launch minimum to 4, supplier_risk to 3. Combined
   with source-domain rules, this ensures these signals get adequate DIVERSE coverage.

4. **Targeted regeneration (B5):** After LLM generation, if a demo-required signal is below its
   minimum on LLM-generated queries, issue one focused LLM call for that signal. This catches
   cases where the main LLM call under-represents a signal even after the prompt fix.

5. **Telemetry (B6):** Track per-signal query counts (LLM vs deterministic) so future sprints
   can diagnose signal imbalance without running a full pipeline.

---

## Telemetry Gap in Sprint 5 (Known Issue)

From `SPRINT_5_INTEGRITY_AUDIT_REPORT.md`:
> `expansion_generated_signal_counts` and `expansion_trimmed_signal_counts` are identical
> (both post-trim). The "generated" name implies pre-trim, but pre-trim counts are not captured.

Sprint 7 adds `query_distribution_before_trim` and `query_distribution_after_trim` to fix this.
The legacy field `expansion_generated_signal_counts` is not renamed (schema stability).
