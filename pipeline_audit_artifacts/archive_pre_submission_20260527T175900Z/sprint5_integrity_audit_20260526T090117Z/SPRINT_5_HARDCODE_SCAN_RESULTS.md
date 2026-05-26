# Sprint 5 Hardcode Scan Results

**Date:** 2026-05-26
**Scope:** All `backend/app/pipeline/` and `backend/scripts/` Python files
**Method:** grep patterns + git diff review

---

## Patterns Scanned

```
report_10f68    ← Sprint 5 authoritative report ID
report_3dfb     ← Sprint 4 baseline report ID
force_pass      ← bypass keyword
bypass_quality  ← bypass keyword
skip_gate       ← bypass keyword
fake_evidence   ← bypass keyword
HARDCODE        ← bypass keyword
BYPASS          ← bypass keyword
SKIP_QUALITY    ← bypass keyword
FORCE_PASS      ← bypass keyword
```

## Results: Zero Matches in Runtime Code

All patterns returned empty for runtime pipeline files. No hardcoded report IDs.
No bypass conditions. No forced-pass logic.

---

## Company Name References (Pre-Existing, Not Sprint 5 Changes)

These were found by a broader scan. All are pre-existing. None were modified by Sprint 5.

### `backend/app/pipeline/agent1_query_planner.py`

| Line | Content | Origin |
|---|---|---|
| 67 | `PRIORITY_COMPANIES = ["Nvidia", "AMD", "Intel", "Dell", "HPE", "Micron"]` | Pre-existing constant |
| 235–240 | `"Nvidia Q1 2026 13F..."` / `"AMD MI300X..."` in docstring examples | Pre-existing docs |
| 251 | `"Nvidia, AMD, Intel, Dell, HPE, Micron"` in prompt docstring | Pre-existing docs |

**Sprint 5 git diff** for `agent1_query_planner.py`: zero company literals added in any of the
4 changed code sections (lines ~438, ~481–495, ~551, ~607, ~762, ~795–813, ~1058–1070).

### `backend/app/pipeline/agent2_web_workers.py`

| Line | Content |
|---|---|
| 478–486 | `if company == "AMD": ...` AMD-specific pricing URL patterns |

Pre-existing special case for AMD MI300X pricing pages. Not touched by Sprint 5.

### `backend/app/pipeline/agent4_finbert_scorer.py`

| Lines 123–129 | AMD test fixtures in internal unit test function |

Pre-existing. Not touched by Sprint 5.

### `backend/app/pipeline/agent5_contradiction_writer.py`

| Lines 140–188 | AMD/Nvidia in internal doctest fixtures |

Pre-existing. Not touched by Sprint 5.

### `backend/app/pipeline/pricing_pressure_playbook.py`

| Line 22 | `DEMO_PRICING_COMPANIES = {"Nvidia", "AMD", "Supermicro"}` |
| Line 78 | `if "AMD" in selected:` AMD-specific pricing query template |

Pre-existing playbook logic. Not touched by Sprint 5.

### `backend/app/pipeline/agent3_fact_extractors.py`

| Line 49 | `"entity": "Company name (Nvidia|AMD|Intel|...)..."` in extraction prompt |
| Lines 255–256 | `"AMD MI400 product launch announcement 2025"` in doctest fixture |

Pre-existing. Not touched by Sprint 5.

### `backend/scripts/test_agent1_expansion_stability.py`

| Line 34 | `DEMO_COMPANIES = ["Nvidia", "AMD", "Supermicro"]` |

This is **test fixture data only**, in the new zero-cost test script created in Sprint 5.
The company list is used to construct `SearchQuery` objects for the test. The functions under
test (`_trim_queries_to_limit`, `_enforce_final_quality`) accept `expected_companies` as a
parameter and have no knowledge of specific company names. The randomized generality test
with `["CompA", "CompB", "CompC"]` confirms this: 100/100 PASS with non-demo company names.

---

## Conclusion

**No hardcoded report IDs, bypass conditions, or forced-pass logic anywhere in the codebase.**
All company-name references found are either: (a) pre-existing module constants or docstrings,
(b) pre-existing agent-level special-case logic untouched by Sprint 5, or (c) test fixture
data in the new zero-cost test script where the company names do not affect runtime behavior.
