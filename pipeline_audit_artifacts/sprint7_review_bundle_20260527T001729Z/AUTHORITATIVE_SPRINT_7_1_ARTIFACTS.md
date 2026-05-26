# Authoritative Sprint 7.1 Artifacts

**Date:** 2026-05-27
**Sprint 7.1 type:** Offline evidence reconciliation + judge readiness audit. No pipeline rerun.

---

## Sprint 7.1 Verdict

**Sprint 7 is the authoritative demo baseline.** The reconciliation audit confirms:
- Zero fabrication-pattern claims (top-level suspicious_claim_count = 0)
- Zero contradictions in verified claims
- 8 verified claims clean through MiniCheck
- 14% noise in raw fact pool (7/49 facts with quality issues) — none promoted to verified claims
- PARTIAL_PASS is honest, not a pipeline failure

---

## Code Change in Sprint 7.1

**File:** `backend/scripts/evidence_quality_audit.py` line 220

**Bug:** `str.lstrip("www.")` strips individual characters in the set `{'w','.'}` rather than the exact string prefix, causing `www.wsj.com` → `sj.com` and classifying a WSJ fact as domain `unknown` instead of `acceptable`.

**Fix:** Replaced `lstrip("www.")` with `removeprefix("www.")`.

**Effect:** The supplier_risk fact sourced from WSJ (Microsoft lobbying on AI chip exports) now correctly classified as `acceptable` tier domain. Source tier summary after fix: 4 authoritative, 7 acceptable, 1 suspicious (youtube.com), 0 unknown.

---

## Sprint 7.1 Documents Created

| Document | Description |
|---|---|
| `SPRINT_7_1_RECONCILIATION_PLAN.md` | Audit scope, investigation questions, task list |
| `SPRINT_7_EVIDENCE_RECONCILIATION_REPORT.md` | Full reconciliation: suspicious count mismatch, per-signal fact analysis, extract_domain bug |
| `JUDGE_READINESS_ASSESSMENT_SPRINT_7.md` | Safe/unsafe claims, best demo narrative, evidence panels, limitations |
| `AUTHORITATIVE_SPRINT_7_1_ARTIFACTS.md` | This file — artifact index |

---

## Suspicious Count Mismatch — Resolved

Two distinct checks both named `suspicious_claim_count`:

| Check | Location | Meaning | Sprint 7 value |
|---|---|---|---|
| Fabrication pattern | `evidence_quality_summary.json` + `suspicious_claims.json` | Fact matched one of 6 boilerplate/hallucination regex patterns | **0** |
| Vocabulary sanity | `signal_semantics_audit.json` per signal | Fact has zero vocabulary keyword matches for its signal type | **17 total** (across signals) |

These are **different checks**. The 17 vocabulary mismatches are NOT fabrications. Most are legitimate facts whose claim text uses synonyms outside the keyword list. The naming inconsistency is a documentation bug, not a data correctness bug.

---

## Fact Quality Issues Found (7 of 49 facts)

| # | Fact | Issue | Impact |
|---|---|---|---|
| 1–3 | Nvidia Q2/Q3/Q4 FY earnings presentation dates | Misclassified as `product_launch`, should be `investor_signal` | Did NOT promote to verified claim |
| 4 | AMD Instinct GPU roadmap | Stale content — URL dated 2024-06-02 | Did NOT promote to verified claim |
| 5 | Dell AI gear client count | Out-of-scope entity (Dell not AMD/Nvidia/SMCI) | Did NOT promote to verified claim |
| 6 | Runpod alternatives to Lambda Labs | Misclassified as `strategic_messaging`, is market data | Did NOT promote to verified claim |
| 7 | Nvidia beneficial ownership filing | Vocabulary mismatch only — legitimate SEC Form 4 filing | Legitimate, vocabulary check false positive |

All 7 facts with quality issues were **correctly filtered** by the Triangulator before reaching the report.

---

## Corrected Source Tier Summary (after extract_domain fix)

| Domain | Tier | Facts | Signals |
|---|---|---|---|
| ir.amd.com | authoritative (1) | 10 | investor_signal, product_launch, strategic_messaging |
| sec.gov | authoritative (1) | 9 | investor_signal |
| investor.nvidia.com | authoritative (1) | 9 | investor_signal, product_launch, strategic_messaging |
| bloomberg.com | acceptable (2) | 7 | all four active signals |
| servethehome.com | acceptable (4) | 4 | product_launch, strategic_messaging |
| blogs.oracle.com | acceptable (4) | 2 | pricing_pressure |
| ir.supermicro.com | authoritative (1) | 2 | investor_signal |
| tomshardware.com | acceptable (3) | 2 | product_launch |
| wsj.com | acceptable (now) | 1 | supplier_risk |
| runpod.io | acceptable (4) | 1 | strategic_messaging |
| amd.com | acceptable (4) | 1 | product_launch |
| youtube.com | suspicious | 1 | investor_signal |

---

## Sprint 7.2 Recommendations (from reconciliation findings)

| Priority | Issue | Recommended fix |
|---|---|---|
| LOW | `audit_signal_semantics()` field named `suspicious_claim_count` conflicts with top-level fabrication check | Rename to `vocab_mismatch_count` and `vocab_mismatch_facts` |
| LOW | `SIGNAL_SANITY_TERMS` vocabulary too narrow → 60% false positive rate | Add: `introduces`, `unveils`, `unveiled`, `expands`, `upcoming`, `collaboration`, `anticipates` |
| MEDIUM | 3 product_launch facts are investor event calendar dates | Add to Agent 3 prompt: "If fact is 'Company will present/announce financial results' → label as investor_signal not product_launch" |
| MEDIUM | 1 stale fact from 2024 URL | Add URL date filter to Agent 3: reject source URLs with year <2025 in path |
| LOW | 1 out-of-scope entity (Dell) | Add entity allowlist enforcement in Agent 3 for demo scope |

---

## Sprint 7 Authoritative Report Fields (unchanged)

| Field | Value |
|---|---|
| report_id | `report_05aacb872fda` |
| quality_status | PARTIAL_PASS |
| quality_reason | fact_count 49 < 50 |
| pulse_score | 55.8 |
| pulse_status | stable |
| evidence_count | 49 |
| source_count | 23 URLs / 12 domains |
| suspicious_claims (fabrication check) | **0** |
| contradictions | **0** |
| avg_confidence | 0.931 |
| verified_claims | 8 |
| product_launch | 19 facts |
| investor_signal | 17 facts |
| strategic_messaging | 9 facts |
| pricing_pressure | 2 facts |
| supplier_risk | 2 facts |

---

## Rollback Status (Sprint 7.1)

No rollback. Sprint 7.1 is an offline audit. The only code change is the `extract_domain()` bug fix in `evidence_quality_audit.py` — a reporting tool, not the pipeline.

Sprint 7 `agent1_query_planner.py` changes remain authoritative.
