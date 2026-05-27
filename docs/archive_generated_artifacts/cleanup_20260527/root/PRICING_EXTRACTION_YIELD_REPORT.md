# Pricing Extraction Yield Report

**Date:** 2026-05-27  
**Report:** `report_1df9ca6a1014`  
**Artifact folder:** `pipeline_audit_artifacts/demo_track2_20260527T074938Z/`  
**Diagnosis script:** `backend/scripts/pricing_fact_yield_diagnosis.py`

---

## Summary

| Metric | Value |
|---|---|
| Pricing docs accepted | 14 |
| Docs with ≥ 1 pricing fact | 2 |
| Docs with 0 pricing facts | 12 |
| Zero-fact rate | **85.7%** |
| High-pattern zero-fact docs (≥ 10 patterns) | **5** |
| Pricing_pressure facts in DB | **3** |
| Estimated facts recoverable (Option B) | **~10** |

---

## Per-Document Yield Table

| URL | Content (chars) | Price Patterns | Facts | Bottleneck |
|---|---|---|---|---|
| coreweave.com/pricing | 98,904 | **166** | 0 | truncation + tabular_format + entity_mismatch |
| coreweave.com/pricing/classic | 86,661 | **62** | 0 | truncation + tabular_format + entity_mismatch |
| runpod.io/pricing | 51,417 | **55** | 0 | truncation + tabular_format + entity_mismatch |
| runpod.io/articles/guides/top-cloud-gpu-providers | 116,377 | 39 | 0 | truncation + tabular_format + entity_mismatch |
| runpod.io/articles/alternatives/lambda-labs | 86,897 | 39 | 0 | truncation + tabular_format + entity_mismatch |
| blogs.oracle.com/…mi300x-gpus | 26,773 | 4 | 0 | truncation + entity_mismatch |
| cloud.google.com/gpus-pricing | 30 | 0 | 0 | thin_content (browser escalated, returned 0B) |
| amd.com/en/where-to-buy/accelerators | 0 | 0 | 0 | thin_content |
| ir.amd.com/… | 0 | 0 | 0 | thin_content |
| dell.com/…amd-instinct-blog | 0 | 0 | 0 | thin_content |
| ir.supermicro.com/… | 0 | 0 | 0 | thin_content |
| nvidia.com/en-us/data-center/h100 | 0 | 0 | 0 | thin_content |
| **newsletter.semianalysis.com/…** | 0\* | 0\* | **1** | — |
| **thinkmate.com/systems/supermicro/…** | 0\* | 0\* | **2** | — |

\* No escalation telemetry (not in browser-allowed domain list); content was fetched and produced facts.

---

## Bottleneck Breakdown

| Bottleneck | Zero-fact docs affected |
|---|---|
| Truncation (`doc.content[:8000]`, page > 8KB) | 6 |
| Entity mismatch (domain not in KNOWN_ENTITIES) | 6 |
| Thin content / bot-blocked | 6 |
| Tabular format (≥ 10 price patterns, no sentence structure) | 5 |

All five **high-pattern** pages have the triple co-occurrence: truncation + tabular_format + entity_mismatch.
This means fixing only one of the three would still leave facts unextracted on those pages.

---

## Root Cause Detail

### 1. Agent 3 Content Truncation (Primary)

`backend/app/pipeline/agent3_fact_extractors.py` passes `doc.content[:8000]` to the LLM.

For a 98,904-char pricing page, the LLM sees only the **first 8%** of the document — typically
introductory marketing copy, navigation headers, and feature descriptions. The actual price table
(e.g., `H100 SXM5  $2.49/hr  on-demand`) is deeper in the page and is completely invisible to
Agent 3.

### 2. Tabular Format

After `clean_html`, cloud pricing pages produce row fragments like:
```
H100 SXM5
$2.49
per hour
on-demand
```
These are not declarative sentences. Agent 3's LLM prompt asks for claims with a verbatim
`evidence_quote`. Sparse table rows don't produce well-formed claims, and the row fragments
don't appear verbatim in the original content in the way the validation check expects.

### 3. Entity Mismatch

When Agent 3 does extract a claim from a coreweave.com pricing page, it naturally assigns the
entity as `"CoreWeave"` (the page owner). But `KNOWN_ENTITIES` in `node_validate_and_split.py`
contains only `{AMD, Nvidia, Supermicro, Dell, Intel, Broadcom, Micron, HPE, market}`.
`"CoreWeave"` fails the entity check → fact discarded.

Evidence: Round 1 quality gate audit shows **8 entity validation failures** (not present in Round 0,
which had fewer pricing docs). These failures exactly correspond to the cloud provider docs added in
the expansion round.

### 4. Thin Content / Bot-Blocked

6 URLs returned ≤ 30 chars of content — likely JavaScript-heavy pages that even the Browser API
couldn't render, or corporate IR pages that block scrapers. `cloud.google.com/gpus-pricing`
was browser-escalated but returned 0 bytes from the Browser API. These are harder to fix without
changing the source selection strategy.

---

## Why ThinkMate and SemiAnalysis Worked

- **thinkmate.com**: Product listing with explicit USD prices embedded in plain HTML (`$12,415.00`).
  Content is short enough (< 8KB estimate) that truncation is not an issue. Entity is `Supermicro`
  (ThinkMate sells Supermicro servers) — a valid KNOWN_ENTITY.

- **semianalysis.com**: Newsletter article with a declarative sentence: `"H100 1-year GPU rental
  contract pricing increased by almost 40% to $2.35 per hour per GPU by March 2026"`. Natural prose
  → clean claim + verbatim quote. Entity is `market` — valid KNOWN_ENTITY.

Both sources happen to avoid all three bottlenecks. Cloud pricing pages hit all three simultaneously.

---

## Recommendation: Option B — Deterministic Pricing Pre-Extractor

Add `_distill_pricing_content(content: str) -> str` in `agent3_fact_extractors.py`.

**Algorithm:**
1. Scan full `doc.content` using `_PRICE_PATTERNS` regex (same regex as agent2)
2. For each match, extract a ±250-char sentence-aware context window
3. Deduplicate overlapping windows
4. Prepend a one-line header: `"[GPU pricing data from {domain}]"`
5. Concatenate up to ~2500 chars
6. Return as `content_for_llm`

**Guard:** Only activate when `source_type == "pricing_pages"` AND full content has ≥ 5 price
pattern matches. Short pages (< 5 patterns) continue using `doc.content[:8000]` unchanged.

**Example transformation** (coreweave.com/pricing, chars 45,000–46,000):
```
Before (what LLM sees — first 8000 chars):
  "CoreWeave delivers cloud-native GPU infrastructure...
   [2500 chars of marketing copy, then nav links]"

After (distilled from full 98KB):
  "[GPU pricing data from coreweave.com]
   H100 SXM5 available at $2.49 per hour on-demand. Reserved instances
   from $1.80/hr. H200 NVL available at $3.20 per hour...
   A100 80GB PCIE at $1.89/hr. RTX A6000 at $0.76/hr..."
```

The distilled content:
- Contains GPU model names (H100, H200, MI300X) → Agent 3 assigns entity to GPU vendor, not cloud provider
- Sentence-like structure → clean claims with verbatim evidence_quote
- Covers the entire page → no truncation

**Expected outcome:** 5–10 additional `pricing_pressure` facts from coreweave.com (2–3) and
runpod.io (2–3) direct pricing pages. `pricing_pressure` signal score > 0.0 (currently 0.0
with source_count=0).

---

## Options Not Chosen

| Option | Reason Not Chosen |
|---|---|
| A: Prompt/schema tuning | Does not fix truncation — LLM still sees only 8% of content |
| C: Lower confidence threshold | Would admit low-quality facts; risks hallucinations from thin content |
| D: Source-specific adapter per domain | High maintenance; brittle to page layout changes |
| E: No change | Leaves pricing_pressure at 0.0 score for the demo |

---

## What Does NOT Change

- LangGraph DAG / node order
- Quality Gate thresholds (`QUALITY_MIN_FACTS=50`)
- `node_validate_and_split.py` — `KNOWN_ENTITIES` list stays as-is
- BrightData routing (already done in Task A)
- Agent 1 signal balance constants
- Any other Agent (1, 2, 4, 5, 6, 7)

---

## Next Step

Approve Option B implementation. The change is isolated to one function in
`backend/app/pipeline/agent3_fact_extractors.py` and can be verified with zero-cost static tests
before any live pipeline run.
