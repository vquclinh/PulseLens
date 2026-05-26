# Authoritative Sprint 3 Artifacts

Sprint 3 goal: Evidence Quality & Signal Semantics Audit.
No full pipeline re-run was performed. All analysis read from existing Sprint 2 data.

---

## Authoritative Evidence Quality Audit Folder

**Folder:** `pipeline_audit_artifacts/evidence_quality_20260526T053621Z/`
**Run date:** 2026-05-26 05:36 UTC
**Cost:** Zero (DB read only — no BrightData calls)
**Source data:** Report `report_dfd5e69a3a42` from `backend/data/pulselens.db`

### Files in this folder

| File | Contents |
|---|---|
| `evidence_quality_summary.json` | High-level metrics: fact counts, confidence, pricing verdict, signal coverage |
| `signal_semantics_audit.json` | Per-signal breakdown: facts, claims, confidence, top domains, suspicious flags |
| `pricing_pressure_semantics_audit.json` | Per-fact pricing classification: strong/weak/misclassified/insufficient |
| `suspicious_claims.json` | Claims matching suspicious patterns (1 found: CEVA IR metadata) |
| `source_tier_quality_audit.json` | Per-domain quality ratings: authoritative/acceptable/weak/suspicious/reject |
| `evidence_quality_run.log` | Full console log of the audit run |

### Key metrics from this run

| Metric | Value |
|---|---|
| Total facts analyzed | 63 |
| Total verified claims | 10 |
| Average confidence | 0.921 |
| Pricing strong / weak / misclassified | 2 / 2 / 1 |
| Pricing verdict | WEAK (40% strong) |
| Suspicious claims confirmed | 1 (CEVA IR metadata) |
| Suspicious source domains | 1 (instagram.com) |
| Reject-next-time candidate domains | 1 (ceva-ip.com) |

---

## Rerun Demo Folder

No rerun was performed. Sprint 3 was audit-only. The Sprint 2 authoritative demo run
(`pipeline_audit_artifacts/demo_track2_20260526T040110Z/`) remains the active reference.

A rerun with the Agent 3 prompt fix is recommended as the first task of Sprint 4.

---

## Stale/Superseded Sprint 3 Folders

None — this was the first Sprint 3 audit run.

---

## Files to Send for External Review (ChatGPT or Peer)

Send these files together:

**Evidence quality artifacts:**
- `pipeline_audit_artifacts/evidence_quality_20260526T053621Z/evidence_quality_summary.json`
- `pipeline_audit_artifacts/evidence_quality_20260526T053621Z/pricing_pressure_semantics_audit.json`
- `pipeline_audit_artifacts/evidence_quality_20260526T053621Z/signal_semantics_audit.json`
- `pipeline_audit_artifacts/evidence_quality_20260526T053621Z/suspicious_claims.json`
- `pipeline_audit_artifacts/evidence_quality_20260526T053621Z/source_tier_quality_audit.json`

**Code changes made this sprint:**
- `backend/app/utils/url_scorer.py` (Instagram SOCIAL_MARKERS fix)
- `backend/app/pipeline/agent3_fact_extractors.py` (pricing_pressure negative examples)

**Reference reports:**
- `EVIDENCE_QUALITY_SPRINT_3_REPORT.md` (this sprint's full findings)
- `SPRINT_3_IMPLEMENTATION_PLAN.md` (plan and safety constraints)
- `AUTHORITATIVE_SPRINT_2_ARTIFACTS.md` (Sprint 2 baseline with documentation correction)

**Source data used:**
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/demo_report_summary.json`
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/web_collection_audit.json`
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/demo_scope_config.json`

---

## Sprint 2 Authoritative Artifacts (unchanged)

These remain intact and are NOT superseded by Sprint 3:

- `pipeline_audit_artifacts/pricing_pressure_20260526T033831Z/` — authoritative pricing retrieval
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/` — authoritative 3-company demo run
