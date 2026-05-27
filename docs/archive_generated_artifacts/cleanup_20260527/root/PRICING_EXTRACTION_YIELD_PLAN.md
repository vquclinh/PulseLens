# Pricing Extraction Yield Plan

**Date:** 2026-05-27  
**Report under analysis:** `report_1df9ca6a1014`  
**Artifact folder:** `pipeline_audit_artifacts/demo_track2_20260527T074938Z/`

---

## Context

After enabling BrightData Web Unlocker + Browser API routing (Sprint 8 Task A), the live pipeline
run improved retrieval (84 docs accepted, 9.52% zero-doc rate vs 31% baseline). However,
`pricing_pressure` yield remained at **3 facts**, all from non-cloud-provider sources. Direct cloud
pricing pages — coreweave.com (166 price patterns, 98KB), runpod.io/pricing (55 patterns, 51KB) —
produced **zero facts** despite being correctly fetched.

**Goal:** Diagnose the extraction bottleneck and propose a targeted fix that does not require re-running
the live pipeline or modifying the LangGraph DAG / Quality Gate thresholds.

---

## Root Causes (Confirmed)

| # | Bottleneck | Docs Affected | Evidence |
|---|---|---|---|
| 1 | **Agent 3 content truncation** | 6 | `agent3_fact_extractors.py: doc.content[:8000]`. coreweave.com = 98KB; LLM sees only 8% |
| 2 | **Tabular format** | 5 | Cloud pricing pages clean to sparse rows (`H100 SXM5  $2.49  per hour`). No sentence structure for declarative claims or verbatim `evidence_quote` |
| 3 | **Entity mismatch** | 6 | "CoreWeave", "RunPod", "Google Cloud" not in `KNOWN_ENTITIES` (`node_validate_and_split.py`). Agent 3 attributes facts to cloud provider → validation rejects them |
| 4 | **Thin content / bot-block** | 6 | AMD IR pages, NVIDIA product page, GCP (escalated, browser returned 0 chars) |

**Note:** Bottlenecks 1 + 2 + 3 co-occur on the same 5 high-pattern pages, so fixing any one helps;
fixing all three maximally helps.

---

## Deliverables

| File | Status |
|---|---|
| `PRICING_EXTRACTION_YIELD_PLAN.md` (this file) | ✅ |
| `backend/scripts/pricing_fact_yield_diagnosis.py` | ✅ |
| `pipeline_audit_artifacts/demo_track2_20260527T074938Z/pricing_doc_fact_yield.json` | ✅ |
| `pipeline_audit_artifacts/demo_track2_20260527T074938Z/high_pattern_zero_fact_docs.json` | ✅ |
| `pipeline_audit_artifacts/demo_track2_20260527T074938Z/pricing_extraction_bottleneck_summary.json` | ✅ |
| `PRICING_EXTRACTION_YIELD_REPORT.md` | ✅ |

---

## Recommended Fix: Option B — Deterministic Pricing Pre-Extractor

**Status: PROPOSED — awaiting user approval before implementation.**

### What changes

**File:** `backend/app/pipeline/agent3_fact_extractors.py`

Add `_distill_pricing_content(content: str) -> str`:

1. Scan full `doc.content` (not truncated) using `_PRICE_PATTERNS` regex
2. For each price pattern match, extract a ±250-char sentence-aware context window
3. Deduplicate overlapping windows
4. Concatenate up to ~2500 chars of distilled pricing context
5. Replace `doc.content[:8000]` with the distilled string only when:
   - `doc.source_type == "pricing_pages"`, AND
   - The full content has ≥ 5 price pattern matches (guard: skip distiller on thin pages)

### Why this solves all three bottlenecks

| Bottleneck | How Option B helps |
|---|---|
| Truncation | Scans full 98KB content, not just first 8KB |
| Tabular format | Window extraction produces sentence-like context (`"H100 SXM5 GPU available at $2.49 per hour on CoreWeave"`) |
| Entity mismatch | Distilled sentences mention GPU model names (H100, MI300X) → Agent 3 assigns entity to GPU vendor (Nvidia, AMD) not cloud provider |

### What does NOT change

- LangGraph DAG / node order
- Quality Gate thresholds (`QUALITY_MIN_FACTS=50`)
- `node_validate_and_split.py` validation logic
- `KNOWN_ENTITIES` list
- BrightData routing (already implemented)
- Any other Agent (1, 2, 4, 5, 6, 7)

---

## Diagnosis Script

**File:** `backend/scripts/pricing_fact_yield_diagnosis.py`

Run from `backend/`:
```bash
python scripts/pricing_fact_yield_diagnosis.py \
  --artifact-dir ../pipeline_audit_artifacts/demo_track2_20260527T074938Z \
  --report-id report_1df9ca6a1014
```

Inputs: `web_collection_audit.json` (escalation telemetry) + `data/pulselens.db` (pricing_pressure facts).  
No API calls. No BrightData calls.

---

## Verification Plan (after Option B implementation)

Zero-cost checks (no API calls):
```bash
cd backend
python -c "from app.pipeline.agent3_fact_extractors import _distill_pricing_content; print('import OK')"
python tests/pipeline/test_pricing_preextractor.py   # new test file TBD
python tests/pipeline/test_agent1_signal_balance.py  # regression guard
```

Live evaluation (run ONLY after user approval):
```bash
cd backend
PULSELENS_DEMO_SCOPE=true python scripts/demo_track2_ai_hardware_audit.py
```

Expected improvement: 5–10 additional `pricing_pressure` facts from coreweave.com and runpod.io
pricing pages → pricing_pressure signal score > 0.

---

## Rollback

If Option B degrades fact quality:
```bash
git checkout backend/app/pipeline/agent3_fact_extractors.py
```
No DB changes, no .env changes needed.
