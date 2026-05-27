# Pricing Pre-Extractor Plan

**Date:** 2026-05-27

---

## Problem

`report_1df9ca6a1014` (PARTIAL_PASS, 35 facts) accepted 14 pricing documents but only 3 produced
`pricing_pressure` facts. Five high-pattern docs had 361 combined price patterns and yielded zero facts.

**Root causes:**
1. `agent3_fact_extractors.py` passes `doc.content[:8000]` to the LLM — for a 98KB CoreWeave pricing
   page the LLM sees <8% of the content. Price tables are deeper.
2. Cloud provider names ("CoreWeave", "RunPod") are not in `KNOWN_ENTITIES` — any facts Agent 3
   extracts get rejected at validation.
3. HTML tables clean to sparse rows without sentence structure for verbatim evidence_quote extraction.

---

## Solution

Deterministic pricing pre-extractor that:
- Scans **full** `doc.content` (bypasses truncation)
- Extracts ±200-char context windows around explicit price patterns
- Maps GPU model → entity (H100 → Nvidia, MI300X → AMD) to pass KNOWN_ENTITIES check
- Produces verbatim evidence_quotes that pass the validate_fact substring check
- Merges with Agent 3 LLM facts before existing validation/SAFE/FinBERT pipeline

---

## Files Changed

| File | Action |
|---|---|
| `backend/app/pipeline/pricing_pre_extractor.py` | CREATED |
| `backend/app/pipeline/agent3_fact_extractors.py` | MODIFIED — 25 lines added to `extract_facts_from_documents()` |
| `backend/tests/pipeline/test_pricing_pre_extractor.py` | CREATED — 14 zero-cost tests |
| `backend/scripts/replay_pricing_pre_extractor_on_artifact.py` | CREATED |

**No schema changes.** `FactObject` and `RawDocument` are unchanged.  
**No LangGraph DAG changes.** Node order and edges unchanged.

---

## Integration Point

`extract_facts_from_documents()` in `agent3_fact_extractors.py` — after the LLM gather loop,
the pre-extractor runs on all docs where:
- `signal_type_hint == SignalType.pricing_pressure` OR domain in pricing allowlist
- `count_pricing_patterns(doc.content) >= 5`

Pre-extractor facts are merged via evidence_quote deduplication.

---

## Validation Compatibility

All pre-extractor facts pass through `validate_fact` unchanged:
- `evidence_quote in doc.content` ✓ (verbatim substring from `doc.content`)
- `claim <= 150 chars` ✓ (capped at 140)
- `confidence >= 0.60` ✓ (0.85 for explicit price)
- `entity in KNOWN_ENTITIES` ✓ (H100→Nvidia, MI300X→AMD mapping)
- `_PRICING_STRONG_PATTERNS` ✓ (evidence contains `\$[\d,]+`)

---

## Projected Recovery (offline)

From `pricing_pre_extractor_replay_20260527T162038Z/pricing_pre_extractor_replay_summary.json`:

| URL | Patterns | Projected new facts |
|---|---|---|
| coreweave.com/pricing | 166 | 4 |
| coreweave.com/pricing/classic | 62 | 3 |
| runpod.io/pricing | 55 | 2 |
| runpod.io/articles/guides/* | 39 | 1 |
| runpod.io/articles/alternatives/* | 39 | 1 |
| **Total** | | **~11** |

Current: 35 facts → Projected: **~46 facts** (PARTIAL_PASS threshold stays at 50).  
Live run needed to close the gap and confirm.

---

## Live Evaluation Command (after user approval)

```bash
cd /mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens/backend
PULSELENS_DEMO_SCOPE=true python scripts/demo_track2_ai_hardware_audit.py
```
