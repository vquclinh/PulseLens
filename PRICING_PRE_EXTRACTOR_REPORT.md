# Pricing Pre-Extractor Report

**Date:** 2026-05-27

---

## Files Changed

| File | Change |
|---|---|
| `backend/app/pipeline/pricing_pre_extractor.py` | New module (~220 lines) |
| `backend/app/pipeline/agent3_fact_extractors.py` | +25 lines in `extract_facts_from_documents()` |
| `backend/tests/pipeline/test_pricing_pre_extractor.py` | New — 14 zero-cost tests |
| `backend/scripts/replay_pricing_pre_extractor_on_artifact.py` | New — offline projection script |
| `PRICING_PRE_EXTRACTOR_PLAN.md` | New at repo root |
| `PRICING_PRE_EXTRACTOR_REPORT.md` | This file |

---

## Schema Changed?

**No.** `FactObject` and `RawDocument` are unchanged. Pre-extractor builds `FactObject` directly
using all existing required fields.

---

## LangGraph DAG Changed?

**No.** Node order, edges, and state field names are unchanged. The pre-extractor runs inside
`extract_facts_from_documents()` in Agent 3's node — same call site, no new nodes.

---

## Live APIs Called?

**No.** Zero BrightData calls. Zero OpenRouter calls. All implementation and testing used only
local code execution.

---

## Test Results

| Suite | Tests | Result |
|---|---|---|
| `test_pricing_pre_extractor.py` | 14 | ✅ 14/14 PASS |
| `test_pricing_browser_routing.py` | 12 | ✅ 12/12 PASS |
| `test_agent1_expansion_stability.py` | 4 | ✅ 4/4 PASS |
| `test_agent1_signal_balance.py` | 15 | ✅ 15/15 PASS |
| Pipeline import (`from app.pipeline import graph`) | — | ✅ PASS |

---

## Offline Replay Result

Document text was **not persisted** in audit artifacts (web_collection_audit.json stores
content_length and price_pattern_count but not the full text). Live replay is impossible
without a new pipeline run.

**Projection from artifact telemetry:**

| URL | Price patterns | Projected new facts |
|---|---|---|
| coreweave.com/pricing | 166 | 4 |
| coreweave.com/pricing/classic | 62 | 3 |
| runpod.io/pricing | 55 | 2 |
| runpod.io/articles/guides/top-cloud-gpu-providers | 39 | 1 |
| runpod.io/articles/alternatives/lambda-labs | 39 | 1 |
| **TOTAL projected** | | **~11** |

Assumption: 1 fact per 20 price patterns, max 4 per URL (conservative).

---

## Expected Impact on fact_count

| Metric | Before | After (projected) |
|---|---|---|
| `pricing_pressure` facts | 3 | ~14 |
| Total facts | 35 | ~46 |
| Quality status | PARTIAL_PASS | PARTIAL_PASS (≥50 = PASS) |

The projected ~46 facts remains below the 50-fact PASS threshold. The remaining gap (~4 facts)
depends on how many context windows in the actual page content contain clearly attributed GPU
pricing sentences. A live run is needed to confirm.

---

## Remaining Risks

| Risk | Mitigation |
|---|---|
| Context windows hit `_PRICING_REJECT_RE` (false reject) | Patterns are conservative; tested against synthetic data |
| `entity="market"` for windows without GPU model | Still a valid KNOWN_ENTITIES member; pricing_pressure facts with entity=market are accepted |
| SAFE verification rejects pre-extractor facts | SAFE requires atomic claim support in source → explicit price facts with verbatim quotes should pass |
| RunPod comparison articles (not primary price pages) extract low-quality facts | `_MAX_FACTS_PER_DOC=8` caps extraction; dedup on evidence_quote removes redundancy |
| GCP pricing page returned 0 bytes from Browser API | Pre-extractor won't run (0 patterns < threshold=5); no impact |

---

## Live Evaluation Command

```bash
cd /mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens/backend
PULSELENS_DEMO_SCOPE=true python scripts/demo_track2_ai_hardware_audit.py
```
