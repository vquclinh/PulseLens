# pipeline_audit_artifacts/

Each subfolder is a timestamped snapshot produced by a pipeline audit script.
Nothing is deleted — stale and failed runs are moved to `archive_sprint2_stale/`.

---

## Naming Convention

```
<scope>_<YYYYMMDD>T<HHMMSS>Z/
```

- `<scope>` — either a signal-type focus (e.g. `pricing_pressure`) or a named track
  (e.g. `demo_track2`). Legacy early-dev runs have no scope prefix and use the bare
  timestamp.
- Timestamp is UTC.

---

## Active (Authoritative) Folders

| Folder | Status | Notes |
|---|---|---|
| `pricing_pressure_20260526T033831Z/` | **AUTHORITATIVE** | Best pricing retrieval run — 46 docs, 6.7% zero-doc |
| `demo_track2_20260526T040110Z/` | **AUTHORITATIVE** | Full demo run — PASS, 63 facts, 23 sources, 4/4 signals |

Full metrics: see `../AUTHORITATIVE_SPRINT_2_ARTIFACTS.md`.

---

## Archived Folders

`archive_sprint2_stale/` contains all stale, failed, and superseded runs from
Sprint 2. They are preserved for audit history but should not be used as
references.

| Folder | Reason |
|---|---|
| `20260525T161551Z/` | Early dev — raw state dump only |
| `20260525T161644Z/` | Early dev — duplicate |
| `20260525T170228Z/` | Failed — connection error |
| `20260525T170331Z/` | Superseded (led to 171824Z) |
| `20260525T171824Z/` | Pre-Sprint2 PARTIAL_PASS — 93 facts, pulse 50.0 |
| `20260526T030015Z/` | Pre-Sprint2 pricing failure analysis |
| `pricing_pressure_20260526T031153Z/` | Failed — 0 accepted docs |
| `pricing_pressure_20260526T034324Z/` | Degraded — 13 docs, 20% zero-doc |
| `demo_track2_20260526T034920Z/` | Superseded — PARTIAL_PASS, 2 missing signals |
