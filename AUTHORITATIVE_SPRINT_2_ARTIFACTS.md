# Authoritative Sprint 2 Pipeline Audit Artifacts

Two runs are the official Sprint 2 references. All others are moved to
`pipeline_audit_artifacts/archive_sprint2_stale/`.

---

## 1. Pricing Pressure Retrieval Audit

**Folder:** `pipeline_audit_artifacts/pricing_pressure_20260526T033831Z/`
**Run date:** 2026-05-26 03:38 UTC
**Purpose:** Isolated audit of `pricing_pressure` signal retrieval quality.

| Metric | Value |
|---|---|
| Queries issued | 15 |
| Total docs fetched | 46 |
| Full-text docs (accepted) | 25 |
| Zero-doc query rate | 1 / 15 = **6.7%** |
| Fetch error rate | 0% |
| Source tiers | Mixed tier 2–3 |

**Verdict:** Best pricing-pressure retrieval run of the sprint. Zero-doc rate dropped
from 100% (031153Z, broken BrightData session) to 6.7%. Used as the reference
benchmark for pricing signal coverage going forward.

---

## 2. Demo Track 2 — Full AI Hardware Pipeline

**Folder:** `pipeline_audit_artifacts/demo_track2_20260526T040110Z/`
**Run date:** 2026-05-26 04:01 UTC
**Purpose:** Full 8-company pipeline run for demo/judge presentation.

| Metric | Value |
|---|---|
| Quality status | **PASS** |
| Pulse score | — (see report) |
| Evidence count (facts) | **63** |
| Source count | **23** |
| Core signal types covered | **4 / 4** |
| Missing signal types | 0 |
| Zero-doc query rate | 3 / 36 = **8.3%** |
| `pricing_pressure` document count | **18** |
| Expansion rounds | 1 |

**Verdict:** Authoritative demo artifact. Achieves full PASS quality gate with all
four core signal types covered. Used as the reference for judge demo and as the
stored report in `data/pulselens.db`.

---

## Superseded / Archived Runs

See `pipeline_audit_artifacts/archive_sprint2_stale/` for all prior runs.

| Folder | Reason archived |
|---|---|
| `20260525T161551Z` | Stale early dev — raw state dump, no quality metrics |
| `20260525T161644Z` | Stale early dev — duplicate structure |
| `20260525T170228Z` | Failed run — connection error, 13-line log only |
| `20260525T170331Z` | Superseded — FAIL_EXPAND, led to the 171824Z run |
| `20260525T171824Z` | Superseded pre-Sprint2 — PARTIAL_PASS, 93 facts, pulse 50.0 |
| `20260526T030015Z` | Stale pre-Sprint2 — single pricing failure analysis, zero_doc_rate 0.5 |
| `pricing_pressure_20260526T031153Z` | Failed — 0 accepted docs, 100% zero-doc rate (broken BrightData session) |
| `pricing_pressure_20260526T034324Z` | Superseded/degraded — 13 docs, 20% zero-doc (worse than T033831Z) |
| `demo_track2_20260526T034920Z` | Superseded — PARTIAL_PASS, 48 facts, 2 missing core signals |
