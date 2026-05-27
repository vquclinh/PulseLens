# Static Safety Scan Results

**Scan directory:** `backend/app/`  
**Timestamp:** 2026-05-27T06:24:00Z  
**Verdict:** ✅ CLEAN — no risky runtime code found

---

| Pattern | Matches | Flagged? |
|---|---|---|
| `force_pass` | 0 | ✅ clean |
| `bypass_quality` | 0 | ✅ clean |
| `skip_gate` | 0 | ✅ clean |
| `fake_evidence` | 0 | ✅ clean |
| `PULSELENS_FORENSIC_TRACE.*true` (hardcoded default) | 0 | ✅ clean |
| `forensic_tracer` in `app/` runtime | 0 | ✅ clean |
| `report_[0-9a-f]{8,}` in `pipeline/` or `config/` | 0 | ✅ clean |
| `test_*.py` files in `app/pipeline/` | 0 | ✅ clean |

All 8 patterns returned zero matches. No bypass mechanisms, no hardcoded report IDs, and no forensic instrumentation detected in runtime code.

**Safe to proceed with live pipeline.**
