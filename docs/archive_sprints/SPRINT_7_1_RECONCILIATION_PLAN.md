# Sprint 7.1 — Evidence Quality Reconciliation + Judge Readiness Audit Plan

**Date:** 2026-05-27
**Report under audit:** report_05aacb872fda (Sprint 7, PARTIAL_PASS, 49 facts)
**Audit type:** Offline only — no live APIs, no pipeline rerun, no Bright Data calls.

---

## Objective

Determine whether Sprint 7 is safe to declare the authoritative demo baseline, and produce
a judge-ready assessment of what can and cannot be claimed at demo time.

---

## Files Read

| File | Purpose |
|---|---|
| `sprint7_review_bundle_20260527T001729Z/evidence_quality_summary.json` | Top-level quality metrics |
| `sprint7_review_bundle_20260527T001729Z/signal_semantics_audit.json` | Per-signal fact-level vocabulary checks |
| `sprint7_review_bundle_20260527T001729Z/suspicious_claims.json` | Claim-level fabrication check output |
| `sprint7_review_bundle_20260527T001729Z/source_tier_quality_audit.json` | Domain tier classification |
| `sprint7_review_bundle_20260527T001729Z/pricing_pressure_semantics_audit.json` | Pricing fact classification |
| `sprint7_review_bundle_20260527T001729Z/quality_gate_audit.json` | Quality gate round decisions |
| `sprint7_review_bundle_20260527T001729Z/final_report_quality_summary.json` | Report metadata, watch list |
| `sprint7_review_bundle_20260527T001729Z/query_planner_audit.json` | Query telemetry |
| `sprint7_review_bundle_20260527T001729Z/web_collection_audit.json` | Fetch stats |
| All four Sprint 7 report documents | Prior analysis |

---

## Investigation Questions

1. **Suspicious count mismatch**: `evidence_quality_summary.suspicious_claim_count = 0` but
   `signal_semantics_audit` shows per-signal suspicious counts totaling 17. Are these the same
   check or two different checks? Is there a bug?

2. **product_launch fact quality**: 9 of 19 product_launch facts are flagged by
   `signal_semantics_audit`. How many are genuinely misclassified vs. vocabulary-check false positives?

3. **pricing_pressure = 2 facts**: Is this thin coverage acceptable for demo, or misleading?

4. **supplier_risk = 2 facts**: Is coverage adequate? One fact from `sj.com` (unknown domain).

5. **PARTIAL_PASS at 49/50**: How to present this honestly without underselling the pipeline.

6. **Domain classification anomaly**: `sj.com` classified as unknown when the source URL
   is from WSJ. Root cause?

---

## Tasks

1. Create `SPRINT_7_1_RECONCILIATION_PLAN.md` (this file)
2. Investigate and document the suspicious count mismatch
3. Document the `extract_domain()` lstrip bug (if real)
4. Patch the bug (if it is a real reporting error)
5. Create `SPRINT_7_EVIDENCE_RECONCILIATION_REPORT.md`
6. Create `JUDGE_READINESS_ASSESSMENT_SPRINT_7.md`
7. Create `AUTHORITATIVE_SPRINT_7_1_ARTIFACTS.md`

---

## Key Finding (from pre-read)

A real code bug was found in `evidence_quality_audit.py`:

```python
# BUGGY — lstrip strips individual chars in set {'w','.'}
def extract_domain(url: str) -> str:
    return urlparse(url).netloc.lower().lstrip("www.")
```

`"www.wsj.com".lstrip("www.")` = `"sj.com"` — because `lstrip` strips any leading chars in
the SET `{'w', '.'}`, so it strips the leading `w` in `wsj` as well.

Consequence: WSJ's supplier_risk fact is classified as `unknown` domain instead of `acceptable`.
The actual news content (Microsoft pushing to revise AI chip export restrictions) is legitimate.

Fix: `removeprefix("www.")` → correct result `"wsj.com"` → classified as `acceptable`.

---

## Rollback Posture

Sprint 7 pipeline is NOT rerun. Code fix is only to `evidence_quality_audit.py`. The DB and
pipeline artifacts remain as-is. No new pipeline run is triggered.
