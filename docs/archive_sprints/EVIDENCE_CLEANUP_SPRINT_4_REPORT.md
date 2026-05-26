# Evidence Cleanup & Entity Scope Enforcement — Sprint 4 Report

**Date:** 2026-05-26
**Sprint 4 artifact:** `pipeline_audit_artifacts/demo_track2_20260526T063140Z/`
**Report ID:** `report_3dfb4b94068b`
**Scope:** 3-company demo (Nvidia, AMD, Supermicro), `demo_scope_enabled: true`

---

## Files Changed

| File | Change Type | Change |
|---|---|---|
| `backend/app/utils/url_scorer.py` | MODIFY | Added `COMPANY_IR_DOMAINS` frozenset + IR-nav path rejection rule |
| `backend/app/pipeline/node_validate_and_split.py` | MODIFY | Added `import re`; `_METADATA_NAV_PATTERNS` (7 regexes); `_PRICING_STRONG_PATTERNS` (6); `_PRICING_REJECT_PATTERNS` (5); changed `validate_facts()` to return `tuple[list[FactObject], dict]` |
| `backend/app/pipeline/state.py` | MODIFY | Added `validation_audit: Dict[str, Any]` optional field |
| `backend/app/pipeline/graph.py` | MODIFY | Updated `validate_fact` node to unpack tuple, log new counters, return `validation_audit` |
| `backend/scripts/pricing_document_extraction_diagnosis.py` | NEW | Zero-cost audit script classifying cloud pricing URL gap |
| `SPRINT_4_IMPLEMENTATION_PLAN.md` | NEW | Plan document |
| `SPRINT_4_BEFORE_AFTER_COMPARISON.md` | NEW | Before/after comparison |
| `EVIDENCE_CLEANUP_SPRINT_4_REPORT.md` | NEW | This report |
| `AUTHORITATIVE_SPRINT_4_ARTIFACTS.md` | NEW | Artifact index |

**LangGraph DAG changed:** NO
**Node order changed:** NO
**Report schema/types changed:** NO
**Frontend changed:** NO

---

## Fix 1 — `url_scorer.py`: IR-nav page rejection for non-tracked companies

**File:** `backend/app/utils/url_scorer.py`
**Lines added:**
- `COMPANY_IR_DOMAINS` frozenset built from `company.ir_url` for all 8 COMPANIES
- Hard-rejection rule in `_hard_rejection_reason()` after SOCIAL_MARKERS check:
  ```python
  if (
      "/investor-relations" in urlparse(url).path.lower()
      and not _domain_in_family(domain, COMPANY_PRODUCT_DOMAINS)
      and not _domain_in_family(domain, COMPANY_IR_DOMAINS)
      and not _domain_in_family(domain, frozenset({"sec.gov"}))
  ):
      return "fallback_ir_metadata_wrong_entity"
  ```

**Effect:** `ceva-ip.com/investor-relations/` → rejected at retrieval stage with reason `fallback_ir_metadata_wrong_entity`.
**Verified:** No CEVA facts in Sprint 4 run. 0 suspicious confirmed claims.
**Risk:** Minimal. Only affects `/investor-relations` path from non-tracked company domains.

---

## Fix 2 — `node_validate_and_split.py`: Metadata guard + pricing sanity filter

**File:** `backend/app/pipeline/node_validate_and_split.py`

### Check 5 — Metadata/navigation claim guard
Seven regex patterns targeting IR/nav page descriptions:
- `provides? investor relations information`
- `includes? (financial results|sec filings|earnings webcasts)`
- `(website|page|portal) provides?`
- `contains? links? to`
- `offers? information about`
- `investor relations (page|portal|section|information)`
- `(financial results|press releases|sec filings) (are|can be) (found|accessed|viewed)`

**Effect:** CEVA-type metadata claims discarded before SAFE verification. Defense-in-depth with Fix 1.

### Check 6 — Pricing sanity filter
Applied to `pricing_pressure` facts only. Rejects if `claim + evidence_quote` matches `_PRICING_REJECT_PATTERNS` AND does NOT match `_PRICING_STRONG_PATTERNS`.

Rejected in Sprint 4 run:
- SemiAnalysis "index launch" fact — matched `launched.*price index` pattern
- HBM shortage claim — matched `hbm.*price` pattern (should be `supplier_risk`)
- "available with a starting price" (no $) — matched `available with a starting price(?!\s+of\s+\$)` pattern

**Effect:** 3 bad pricing_pressure facts removed. Pricing verdict improved from WEAK (40%) → ACCEPTABLE (100%).

### Return type change
`validate_facts()` now returns `tuple[list[FactObject], dict]`. The dict contains:
- `discarded_verbatim`, `discarded_length`, `discarded_confidence`, `discarded_entity`
- `discarded_nav_metadata`, `pricing_sanity_rejected_count`, `pricing_sanity_checked_count`
- `rejected_metadata_navigation_facts` (list of fact_ids)

---

## Fix 3 — `state.py`: validation_audit field

```python
validation_audit: Dict[str, Any]    # telemetry from validate_fact gate
```

Not surfaced in `MarketPulseReport` schema. Pipeline-internal only.

---

## Fix 4 — `graph.py`: Thread validation_audit

```python
validated, audit = validate_facts(raw_facts, docs_by_id)
return {"raw_facts": validated, "validation_audit": audit}
```

New log line in `validate_fact` node includes `nav_meta=N pricing_weak=N`.

---

## Pricing Gap Diagnosis Results

**Script:** `backend/scripts/pricing_document_extraction_diagnosis.py`
**Artifact:** `pipeline_audit_artifacts/pricing_extraction_diagnosis_20260526T061730Z/`

27 pricing_pressure URLs were accepted in Sprint 2. Only 3 produced facts.

| Domain | Zero-fact URLs | Classified As | Gap Cause |
|---|---|---|---|
| runpod.io | 6 | blog_or_guide | comparison guides, not pricing pages |
| dell.com | 3 | blog_or_guide | comparison articles |
| cloud.google.com | 3 | unknown | likely JS-rendered pricing tables |
| coreweave.com | 2 | direct_pricing_page | JS-rendered pricing tables |
| semianalysis.com | 1 | newsletter | paywall/partial content |
| others | 9 | various | unknown |

**Key finding:** `coreweave.com/pricing` and `coreweave.com/pricing/classic` are direct pricing pages that yielded zero facts because BrightData scrapes the HTML shell without executing JavaScript — the actual price tables are JS-rendered. RunPod's pricing page (`runpod.io/pricing`) is server-side rendered, explaining why it produced a fact (`$1.99/hr H100`) in Sprint 4.

---

## Sprint 4 Run Results

| Metric | Value |
|---|---|
| `quality_status` | PARTIAL_PASS |
| `quality_reasons` | `fact_count 43 < 50` |
| `pulse_score` | 57.0 (vs 44.3 Sprint 2) |
| `evidence_count` | 43 |
| `source_count` | 17 |
| `pricing_pressure` verdict | ACCEPTABLE (4/4 = 100% strong) |
| Suspicious confirmed claims | 0 (vs 1 CEVA in Sprint 2) |
| `covered_signal_types` | ALL 6 (vs 4 in Sprint 2) |
| `company_coverage` | 100% |
| `query_expansion_rounds` | 1 |

---

## Remaining Weaknesses

1. **fact_count 43 < 50 threshold.** The quality gate requires 50 facts. Sprint 4 has 43 after filtering. This is the correct outcome — the 63 Sprint 2 facts included noise. Lowering the threshold to pass would be wrong. Options: improve retrieval depth (more queries, more domains) or lower threshold deliberately with documented rationale.

2. **CoreWeave/GCP pricing still zero-fact.** Both use JS-rendered price tables that BrightData cannot parse without browser execution. Fix requires Playwright/Puppeteer-based scraping or a fallback to structured API pricing endpoints (e.g., GCP Pricing API).

3. **investor_signal dominates at 26/43 facts (60%).** Signal distribution is skewed toward Supermicro/Nvidia IR. Round 2 expansion helped but the core signal balance could be improved with tighter query planning for non-IR signals.

4. **news_sentiment still 0 facts.** Optional signal, acceptable for demo scope. Should be targeted in full 8-company run.

5. **pricing_pressure has 0 verified claims** (4 facts but 0 passed triangulation). This is because triangulation requires ≥2 corroborating sources for a claim — the 4 pricing facts come from only 2 domains (runpod.io + thinkmate.com). Not a data quality issue; a triangulation threshold issue for pricing signals.

---

## Next Recommended Sprint

**Sprint 5: Retrieval Depth + Pricing Signal Triangulation**

1. Raise query count for `investor_signal` ceiling or add a dedicated per-company `pricing_pressure` sub-query ensuring ≥2 independent pricing sources.
2. Add Playwright/headless-browser fallback for JS-rendered pricing pages (CoreWeave, GCP).
3. Consider dynamic `pricing_pressure` triangulation threshold: 1 corroborating source sufficient for OEM/cloud pricing (not just 2), since each pricing page is independently authoritative.
4. Full 8-company run after single-company pricing triangulation gap is resolved.
5. Investigate `distillintelligence.com` and `aiweekly.co` (unknown domain rating) — accept or reject for future runs.
