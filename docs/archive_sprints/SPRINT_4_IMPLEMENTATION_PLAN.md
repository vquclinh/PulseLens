# Sprint 4 Implementation Plan — Evidence Cleanup, Entity Scope Enforcement, Post-Fix Demo Rerun

**Date:** 2026-05-26
**Scope:** 3-company demo (Nvidia, AMD, Supermicro)
**Baseline:** `report_dfd5e69a3a42` from Sprint 2

---

## Problems Being Fixed

| # | Problem | Root Cause | Fix Location |
|---|---|---|---|
| 1 | CEVA IR page accepted via fallback | `/investor-relations` path from non-tracked domain passed `serp_news` relevance check | `url_scorer.py` |
| 2 | IR-page metadata extracted as financial fact | Agent 3 extracted "provides investor relations information" as `investor_signal` | `node_validate_and_split.py` |
| 3 | pricing_pressure 40% strong (2/5 facts genuine) | Agent 3 prompt ambiguity; no post-extraction sanity filter | `node_validate_and_split.py` (+ Agent 3 prompt fixed in Sprint 3) |
| 4 | Cloud pricing docs (CoreWeave, RunPod, GCP) yielded zero pricing facts | Unknown — needs diagnosis | `pricing_document_extraction_diagnosis.py` (new script) |

---

## Files Changed

| File | Change Type | What Changes |
|---|---|---|
| `backend/app/utils/url_scorer.py` | MODIFY | Add `COMPANY_IR_DOMAINS` frozenset + `/investor-relations` hard-rejection rule |
| `backend/app/pipeline/node_validate_and_split.py` | MODIFY | Add `_METADATA_NAV_PATTERNS` + pricing sanity patterns; change `validate_facts()` to return `tuple[list[FactObject], dict]` |
| `backend/app/pipeline/state.py` | MODIFY | Add `validation_audit: Dict[str, Any]` optional field |
| `backend/app/pipeline/graph.py` | MODIFY | Unpack `validate_facts()` tuple in `validate_fact` node; thread `validation_audit` into state |
| `backend/scripts/pricing_document_extraction_diagnosis.py` | NEW | Zero-cost audit classifying cloud pricing URL gaps |

**LangGraph DAG:** NO CHANGE — same nodes, same edges, same conditional routing.
**Node order:** NO CHANGE.
**Agent 3/4/5/6/7, SAFE, FinBERT, triangulation, signal scoring:** NO CHANGE.
**Report schema/types:** NO CHANGE — `validation_audit` stays in PipelineState only.
**Frontend:** NO CHANGE.

---

## Fix 1 — `url_scorer.py`: IR-nav rejection for non-tracked companies

Add at module level (after `COMPANY_PRODUCT_DOMAINS`):
```python
COMPANY_IR_DOMAINS = frozenset(
    urlparse(company.ir_url).netloc.lower().lstrip("www.")
    for company in COMPANIES
)
```

Add in `_hard_rejection_reason()` after the `SOCIAL_MARKERS` check:
```python
if (
    "/investor-relations" in urlparse(url).path.lower()
    and not _domain_in_family(domain, COMPANY_PRODUCT_DOMAINS)
    and not _domain_in_family(domain, COMPANY_IR_DOMAINS)
    and not _domain_in_family(domain, frozenset({"sec.gov"}))
):
    return "fallback_ir_metadata_wrong_entity"
```

**Safety:** Only rejects URLs with `/investor-relations` in path from non-tracked company domains.
Does not affect pricing query logic. sec.gov always allowed.

---

## Fix 2 — `node_validate_and_split.py`: Two new validation checks

**Module-level patterns:**
```python
_METADATA_NAV_PATTERNS = [7 regex patterns for IR-nav descriptions]
_PRICING_STRONG_PATTERNS = [6 regex patterns for explicit price signals]
_PRICING_REJECT_PATTERNS = [5 regex patterns for index launches, HBM shortage, etc.]
```

**New `validate_facts()` signature:** `(list[FactObject], dict) -> tuple[list[FactObject], dict]`

Check 5 (after entity check): discard if `claim` matches any `_METADATA_NAV_PATTERNS`.
Check 6 (pricing_pressure only): discard if `claim + evidence_quote` matches `_PRICING_REJECT_PATTERNS`
and does NOT match any `_PRICING_STRONG_PATTERNS`.

**Telemetry dict returned** (Sprint 4 only, not in report schema):
`discarded_nav_metadata`, `discarded_pricing_weak`, `pricing_sanity_checked_count`,
`pricing_sanity_rejected_count`, `rejected_metadata_navigation_facts` (list of fact_ids).

---

## Fix 3 — `state.py`: Add validation_audit field

```python
validation_audit: Dict[str, Any]    # telemetry from validate_fact gate
```

---

## Fix 4 — `graph.py`: Thread validation_audit through validate_fact node

```python
validated, audit = validate_facts(raw_facts, docs_by_id)
return {"raw_facts": validated, "validation_audit": audit}
```

---

## New Script — `pricing_document_extraction_diagnosis.py`

Zero-cost audit reading from:
- `pipeline_audit_artifacts/demo_track2_20260526T040110Z/web_collection_audit.json`
- `backend/data/pulselens.db` (report `report_dfd5e69a3a42`)

Classifies each accepted pricing URL as `direct_pricing_page`, `blog_or_guide`, `newsletter`, or `unknown`.
Maps zero-fact domains to gap cause: `likely_no_explicit_price_table`, `likely_comparison_guide_not_price_source`, `likely_paywall_partial_content`.

Outputs under `pipeline_audit_artifacts/pricing_extraction_diagnosis_<ts>/`.

---

## Safety Constraints

- LangGraph DAG, node order, quality thresholds: **unchanged**
- Full 8-company mode: **available but NOT run**
- Demo scope: **Nvidia, AMD, Supermicro only**
- All failures visible in telemetry (logged + `validation_audit` state field)
- PARTIAL_PASS after filtering weak facts is **acceptable and preferred** over misleading PASS

---

## Run Plan

| Step | Command | Cost |
|---|---|---|
| 1. Import checks | `python -c "import app.utils.url_scorer; ..."` × 4 modules | Zero |
| 2. Pricing gap diagnosis | `python backend/scripts/pricing_document_extraction_diagnosis.py` | Zero |
| 3. Demo pipeline rerun | `python backend/scripts/demo_track2_ai_hardware_audit.py` | ~108–120 BrightData + ~110 OpenRouter |
| 4. Evidence quality audit | `python backend/scripts/evidence_quality_audit.py --report-id <new>` | Zero |

---

## Expected Outcomes

| Item | Sprint 2 | Sprint 4 Expected |
|---|---|---|
| CEVA investor_signal fact | Present | Eliminated (Fix 1 + Fix 2) |
| SemiAnalysis "index launch" pricing fact | Present (conf=1.00) | Eliminated (Fix 3 pricing sanity) |
| HBM misclassified pricing fact | Present | Eliminated (Fix 3 pricing sanity) |
| pricing_pressure strong fraction | 2/5 = 40% | 2/2 = 100% of remaining |
| Suspicious confirmed claims | 1 | 0 |
| Quality status | PASS | PARTIAL_PASS (acceptable) |
