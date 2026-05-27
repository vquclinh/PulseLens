# Full Stage Pipeline Trace — Sprint 7

**Date:** 2026-05-27
**Report ID:** report_05aacb872fda
**Artifact directory:** `pipeline_audit_artifacts/demo_track2_20260526T165950Z/`
**Evidence quality dir:** `pipeline_audit_artifacts/evidence_quality_20260526T171620Z/`
**Review bundle:** `pipeline_audit_artifacts/sprint7_review_bundle_20260527T001729Z/`

---

## Stage 1 — Query Planning (Agent 1, Round 0)

**Sprint 7 changes active:** `_DEMO_SIGNAL_QUERY_MINIMUMS`, `_DEMO_SIGNAL_QUERY_CAPS`, domain rules prompt, balance rules prompt, Safety Fix 1 (unconditional cap), Safety Fix 2 (targeted regen priority+max).

### LLM-generated queries (Round 0)

| Signal type | LLM count | Min required | Cap | Status |
|---|---|---|---|---|
| investor_signal | 4 | 4 | 7 | MET |
| product_launch | 4 | 4 | — | MET |
| supplier_risk | 3 | 3 | — | MET |
| pricing_pressure (LLM) | 8 | — | — | LLM supplement |

### Deterministic queries (Round 0)

| Signal type | Count | Source |
|---|---|---|
| pricing_pressure | 13 | Pricing playbook (15 - 2 dedup) |

Playbook full count = 15; two queries deduped against LLM queries → 13 unique deterministic queries.

### Query counts before vs after trim

| Signal type | Before trim | After trim |
|---|---|---|
| pricing_pressure | 24 | 21 |
| investor_signal | 4 | 4 |
| product_launch | 4 | 4 |
| supplier_risk | 3 | 3 |
| **Total** | **35** | **32** |

Signal budget violations: none (investor_signal=4 < cap=7).
Targeted regeneration: none needed (all minimums already met).
Round 0 accepted: 32 queries (1 rejected: signal_type_outside_requested_set).

---

## Stage 2 — Web Collection (Round 0)

- Queries submitted: 32
- Documents collected: 43
- Zero-doc queries: ~29% (12 queries)
- Fetch error rate: 9%

---

## Stage 3 — Fact Extraction (Agent 3, Round 0)

Facts extracted from 43 documents. Sent to SAFE verification.

---

## Stage 4 — SAFE Verification + FinBERT (Round 0)

Round 0 SAFE + quality gate:
- Facts after extraction: ~34
- SAFE passed: 34
- Quality gate round=0: FAIL_EXPAND (34 < 50 MIN_FACTS) → expansion triggered

---

## Stage 5 — Query Planning (Agent 1, Round 1 — Expansion)

Expansion requested for missing signals: investor_signal, pricing_pressure, product_launch, supplier_risk.

LLM generated 6 raw queries, accepted 10 with playbook augmentation.

| Signal type | Expansion count |
|---|---|
| pricing_pressure | 7 |
| supplier_risk | 1 |
| product_launch | 1 |
| investor_signal | 1 |
| **Total** | **10** |

Note: expansion mode uses `None` minimums and `None` caps (gap-fill only). 6 rejected (signal_type_outside_requested_set).

---

## Stage 6 — Web Collection (Round 1)

Total cumulative docs: 61 (43 round 0 + 18 expansion).
Round 1 documents: 18 from 10 expansion queries.

---

## Stage 7 — Fact Extraction (Agent 3, Round 1)

Raw facts from combined 61 documents: 57.

---

## Stage 8 — SAFE Verification + FinBERT (Round 1)

- SAFE verification: 49/53 passed (92%); 4 failed
- FinBERT scored 49 facts: pos=16, neg=2, neu=31, errors=0
- Quality gate round=1: PARTIAL_PASS (49 < 50 MIN_FACTS — max rounds reached)

---

## Stage 9 — Triangulator (Agent 4)

- MiniCheck pass: 49/49 (0 fail)
- Verified claims: 8 from 15 claim groups
- Contradictions: 0

---

## Stage 10 — Contradiction Writer

- Flags: 0
- Notes written: 0

---

## Stage 11 — Signal Scorer (Agent 5)

- Pulse score: 55.8
- Status: stable
- Confidence: 0.732
- Claims processed: 8
- Contradicted: 0

---

## Stage 12 — Company Narratives (Agent 6)

- Companies built: 3 (AMD, Nvidia, Supermicro)
- Avg evidence count: 12.0

---

## Stage 13 — Narrative Synthesizer (Agent 7)

- Headline: "Semiconductor sector shows strong AI-driven product innovation and investor engagement"
- Anomalies: 0

---

## Stage 14 — Watch List Builder (Agent 8)

- Watch list items: 3
  1. Nvidia Q4/FY26 Financial Results Call (urgency: next_2_weeks)
  2. AMD Server Segment Growth Realization (urgency: this_month)
  3. Market Adoption of AI Mainstream Technologies (urgency: this_month)

---

## Stage 15 — Report Assembly

- Report saved: report_05aacb872fda
- Quality status: PARTIAL_PASS
- Quality reason: fact_count 49 < 50

---

## Final Evidence Distribution

| Signal type | Facts | Queries (R0) | Source domains |
|---|---|---|---|
| product_launch | 19 | 4 LLM | servethehome.com(4), tomshardware.com(2), amd.com(1) |
| investor_signal | 17 | 4 LLM | ir.amd.com(10), sec.gov(9), investor.nvidia.com(9), ir.supermicro.com(2) |
| strategic_messaging | 9 | 0 LLM (surfaced via expansion) | bloomberg.com(7) |
| supplier_risk | 2 | 3 LLM | bloomberg.com, ir.supermicro.com |
| pricing_pressure | 2 | 21 (8 LLM+13 det.) | blogs.oracle.com(2), runpod.io(1) |
| **Total** | **49** | **32 R0 + 10 R1** | **12 unique domains** |

---

## Evidence Quality Audit

- suspicious_claims: **0**
- average_confidence: 0.931
- strong_pricing_signals: 2
- weak_pricing_signals: 0
- pricing_verdict: ACCEPTABLE
- source tier breakdown: 4 authoritative, 6 acceptable, 1 suspicious, 1 unknown

Top domains by fact count:
| Domain | Tier | Facts |
|---|---|---|
| ir.amd.com | authoritative (1) | 10 |
| sec.gov | authoritative (1) | 9 |
| investor.nvidia.com | authoritative (1) | 9 |
| bloomberg.com | acceptable (2) | 7 |
| servethehome.com | acceptable (4) | 4 |
| blogs.oracle.com | acceptable (4) | 2 |
| ir.supermicro.com | authoritative (1) | 2 |
| tomshardware.com | acceptable (3) | 2 |

---

## Static Test Summary

All 15 tests passed (0 failures):
- test_14: Cap enforced when total≤max_queries (unconditional cap safety fix)
- test_15: Targeted regen max 2 calls, priority [product_launch, supplier_risk], strategic_messaging blocked
