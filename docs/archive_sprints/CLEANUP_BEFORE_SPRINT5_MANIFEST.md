# Cleanup Before Sprint 5 Manifest

**Cleanup timestamp:** 2026-05-26T07:51:13Z
**Archive folder:** `pipeline_audit_artifacts/archive_before_sprint5_20260526T075113Z/`

---

## Moved Folders (Archived)

| Folder | Archive Destination | Reason |
|---|---|---|
| `evidence_quality_20260526T064101Z/` | `archive_before_sprint5_20260526T075113Z/` | Sprint 4 version; superseded by `evidence_quality_20260526T071826Z/` (pre-regression fresh audit) |
| `pricing_extraction_diagnosis_20260526T061730Z/` | `archive_before_sprint5_20260526T075113Z/` | Sprint 4 version; superseded by `pricing_extraction_diagnosis_20260526T071833Z/` (pre-regression fresh diagnosis) |

---

## Deleted Safe Cache Files

| Type | Count |
|---|---|
| `backend/**/__pycache__/` directories | 1798 directories |
| `backend/.pytest_cache/` | 1 directory |

No source code, database, .env, or markdown reports deleted.

---

## Kept Folders (Live Artifact Tree After Cleanup)

```
pipeline_audit_artifacts/
  README.md
  archive_before_sprint5_20260526T075113Z/      ← new Sprint 5 pre-archive
    evidence_quality_20260526T064101Z/           ← Sprint 4 evidence (superseded)
    pricing_extraction_diagnosis_20260526T061730Z/ ← Sprint 4 diagnosis (superseded)
  archive_before_full_regression_20260526T065615Z/  ← failed clean regression run
  archive_sprint2_stale/                         ← 9 stale Sprint 2 runs
  archive_sprint4_stale/                         ← 2 stale Sprint 4 runs
  demo_track2_20260526T040110Z/                  Sprint 2 baseline
  demo_track2_20260526T063140Z/                  Sprint 4 authoritative demo run
  evidence_quality_20260526T053621Z/             Sprint 3 audit (historical)
  evidence_quality_20260526T071826Z/             Pre-regression fresh audit — Sprint 5 baseline
  full_regression_20260526T065737Z/              Full regression folder + review bundle
  pricing_extraction_diagnosis_20260526T071833Z/ Pre-regression diagnosis — Sprint 5 baseline
  pricing_pressure_20260526T033831Z/             Sprint 2 pricing audit
```

---

## Ambiguous Files Not Touched

| File | Reason Not Touched |
|---|---|
| `backend/data/pulselens.db` | Database — never touch |
| `backend/.env` | Secrets — never touch |
| All `*.md` sprint reports | User-authored documentation — kept |
| All source code | Never delete |

---

**Status: CLEAN. Safe to proceed with Sprint 5 code changes and regression.**
