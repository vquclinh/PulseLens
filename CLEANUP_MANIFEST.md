# Cleanup Manifest

**Cleanup timestamp:** 2026-05-26T06:56:15Z
**Pre-regression archive folder:** `pipeline_audit_artifacts/archive_before_full_regression_20260526T065615Z/`

---

## Moved Folders

No folders required moving. All stale artifacts were already archived in a prior step.

Previously archived (already in `pipeline_audit_artifacts/archive_sprint4_stale/`):
| Folder | Archived When | Reason |
|---|---|---|
| `demo_track2_20260526T061824Z/` | During Sprint 4 session | Timeout-killed during round 1; only `pipeline_run.log`, no report saved |
| `pricing_extraction_diagnosis_20260526T061051Z/` | During Sprint 4 session | Empty first run due to DB schema bug (wrong column name) |

---

## Kept Folders (live artifact tree)

| Folder | Keep Reason |
|---|---|
| `demo_track2_20260526T040110Z/` | Sprint 2 authoritative baseline — required for before/after comparison |
| `demo_track2_20260526T063140Z/` | Sprint 4 authoritative complete run — COMPLETE, EXIT_CODE:0 |
| `evidence_quality_20260526T053621Z/` | Sprint 3 authoritative evidence audit — historical baseline |
| `evidence_quality_20260526T064101Z/` | Sprint 4 evidence audit — COMPLETE |
| `pricing_extraction_diagnosis_20260526T061730Z/` | Sprint 4 pricing gap diagnosis — COMPLETE |
| `pricing_pressure_20260526T033831Z/` | Sprint 2 pricing retrieval audit — historical |
| `archive_sprint2_stale/` | 9 stale Sprint 2 runs already archived |
| `archive_sprint4_stale/` | 2 stale Sprint 4 runs already archived |
| `archive_before_full_regression_20260526T065615Z/` | This regression's pre-flight archive (empty — nothing to move) |
| `README.md` | Artifact folder naming convention and index |

---

## Deleted Temp Files

None. No safe temp files identified for deletion.
`/tmp/sprint4_demo_run.log` left intact (not repo-managed, 808 lines, EXIT_CODE:0 confirmed).

---

## Ambiguous Files Not Touched

| File | Reason Not Touched |
|---|---|
| `backend/data/pulselens.db` | Database — never touch |
| `backend/.env` | Secrets — never touch |
| All `*.md` sprint reports | User-authored documentation — kept |

---

## Live Artifact Tree (after cleanup)

```
pipeline_audit_artifacts/
  README.md
  archive_before_full_regression_20260526T065615Z/   (empty — pre-flight record)
  archive_sprint2_stale/                             (9 folders)
  archive_sprint4_stale/                             (2 folders)
  demo_track2_20260526T040110Z/                      Sprint 2 baseline
  demo_track2_20260526T063140Z/                      Sprint 4 complete run
  evidence_quality_20260526T053621Z/                 Sprint 3 audit
  evidence_quality_20260526T064101Z/                 Sprint 4 audit
  pricing_extraction_diagnosis_20260526T061730Z/     Sprint 4 gap diagnosis
  pricing_pressure_20260526T033831Z/                 Sprint 2 pricing
```

**Status: CLEAN. Safe to proceed with full regression run.**
