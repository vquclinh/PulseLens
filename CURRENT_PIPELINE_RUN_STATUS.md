# Current Pipeline Run Status

**Assessed:** 2026-05-26
**Purpose:** Determine whether Sprint 4 run is usable before proceeding with full regression.

---

## Background Process Status

**All background processes have terminated.** The background demo run spawned in the Sprint 4 session
(PID 120509/120511) completed with EXIT_CODE:0. No lingering pipeline processes found via `ps aux`.

---

## Latest Report in DB

| Field | Value |
|---|---|
| `report_id` | `report_3dfb4b94068b` |
| `created_at` | 2026-05-26 06:40:04 |
| `quality_status` | PARTIAL_PASS |
| `quality_reasons` | `fact_count 43 < 50` |
| `pulse_score` | 57.0 |
| `evidence_count` | 43 |
| `source_count` | 17 |
| `covered_signal_types` | ALL 6 |
| `missing_signal_types` | (none) |
| `query_count` | 36 (2 rounds) |
| `zero_doc_query_count` | 12 / 36 = 33% |
| `fetch_error_count` | 0 |

---

## Sprint 4 Demo Run Folder: `demo_track2_20260526T063140Z/`

| File | Present? | Notes |
|---|---|---|
| `pipeline_run.log` | YES | 436 lines, ends at `report_assembler saved report_id=report_3dfb4b94068b` |
| `demo_scope_config.json` | YES | Companies: Nvidia, AMD, Supermicro |
| `query_planner_audit.json` | YES | 2 rounds |
| `web_collection_audit.json` | YES | 57 accepted docs |
| `quality_gate_audit.json` | YES | PARTIAL_PASS, fact_count 43 < 50 |
| `fetch_error_summary.json` | YES | 0 fetch errors |
| `final_report_quality_summary.json` | YES | pulse_score=57.0 |
| `demo_report_summary.json` | YES | Full summary with signal coverage |

**All 8 expected files present. Run is COMPLETE.**

---

## Sprint 4 Evidence Quality Audit Folder: `evidence_quality_20260526T064101Z/`

| File | Present? |
|---|---|
| `evidence_quality_summary.json` | YES |
| `pricing_pressure_semantics_audit.json` | YES |
| `signal_semantics_audit.json` | YES |
| `suspicious_claims.json` | YES |
| `source_tier_quality_audit.json` | YES |
| `evidence_quality_run.log` | YES |

**All 6 expected files present. Audit is COMPLETE.**

---

## Sprint 4 Pricing Diagnosis Folder: `pricing_extraction_diagnosis_20260526T061730Z/`

| File | Present? |
|---|---|
| `pricing_document_extraction_diagnosis.json` | YES |
| `cloud_pricing_docs_with_price_patterns.json` | YES |
| `cloud_pricing_docs_without_price_patterns.json` | YES |
| `pricing_extraction_gap_summary.json` | YES |

**All 4 expected files present. Diagnosis is COMPLETE.**

---

## Last 80 Lines of `pipeline_run.log`

Condensed key milestones (full log: `pipeline_audit_artifacts/demo_track2_20260526T063140Z/pipeline_run.log`):

```
13:31:xx  node: query_planner (round=0) — 32 queries generated
13:18-13:36  Agent 2: 57 docs accepted across 2 rounds
13:36:xx  node: fact_extractor documents=47 skipped_metadata_only=0
13:36:xx  node: validate_fact — (new Sprint 4 filters applied)
13:36:xx  SAFE verification: 43/48 facts passed (90%)
13:39:37  node: finbert_scorer facts=43 — pos=13 neg=4 neu=26
13:39:37  quality_gate: facts=43 signal_types=6 companies=100% zero_doc=33% round=1
13:39:37  quality_gate: PARTIAL_PASS after max rounds reasons=['fact_count 43 < 50']
13:39:37  node: triangulator: 7 verified claims, 1 contradiction
13:39:38  node: contradiction_writer: wrote 1 note (Supermicro investor_signal)
13:39:38  node: signal_scorer: pulse_score=57.0 status=stable confidence=0.682
13:39:42  node: company_narratives built=3
13:39:46  node: narrative_synthesizer headline="AMD's strategic AI investments..."
13:39:48  node: watch_list_builder items=1
13:40:04  node: report_assembler saved report_id=report_3dfb4b94068b
```
EXIT_CODE: 0 (confirmed from `/tmp/sprint4_demo_run.log` tail)

---

## Archive Assessment

| Folder | Status |
|---|---|
| `archive_sprint4_stale/demo_track2_20260526T061824Z/` | Stale — timeout at round 1 (only pipeline_run.log, no report saved) |
| `archive_sprint4_stale/pricing_extraction_diagnosis_20260526T061051Z/` | Stale — empty first run (DB schema bug) |

Both already in `archive_sprint4_stale/`. No additional stale folders in live tree.

---

## Assessment: Is it safe to proceed with clean regression?

**YES — safe to proceed.**

- Sprint 4 run is fully complete, all files present, EXIT_CODE:0
- Report `report_3dfb4b94068b` is in DB with PARTIAL_PASS / 57.0 score
- No background processes running
- Stale artifacts already archived
- Code changes (Sprint 4 fixes) are applied and passing import checks

The clean regression will produce a NEW demo run with the same Sprint 4 fixes active.
It will cost approximately 118–140 BrightData + ~115 OpenRouter calls.
The Sprint 4 run (`report_3dfb4b94068b`) serves as the safety net — if regression fails, it remains authoritative.
