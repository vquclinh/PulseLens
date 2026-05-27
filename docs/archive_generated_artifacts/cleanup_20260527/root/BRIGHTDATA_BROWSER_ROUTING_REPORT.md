# BrightData Browser Routing Implementation Report

**Date:** 2026-05-27  
**Motivation:** System evaluation (report_5760ae7b9861) showed 27 accepted pricing URLs → 3 produced facts (92.6% zero-fact rate). coreweave.com pricing pages had no price tables in scraped HTML (JS-rendered). This implements Web Unlocker as the primary scraper for pricing pages and Browser API as an automatic fallback for pages with thin content.

---

## Files Changed

| File | Change |
|---|---|
| `backend/.env` | Added `BRIGHTDATA_BROWSER_ZONE` + 4 `PRICING_*` config vars |
| `backend/.env.example` | Added same 4 `PRICING_*` config vars |
| `backend/app/utils/brightdata_client.py` | Added `_explicit_browser_zone` + `has_browser_zone` property |
| `backend/app/pipeline/agent2_web_workers.py` | Added pricing escalation logic (helpers + routing + telemetry) |
| `backend/scripts/pricing_document_extraction_diagnosis.py` | Added `load_browser_escalation_stats()` + console report |
| `backend/tests/pipeline/test_pricing_browser_routing.py` | New — 12 zero-cost tests |

---

## Environment

### Backup created
**Path:** `backend/.env.backup_before_brightdata_browser_config`  
API keys were preserved unchanged. Secret values were never printed.

### Vars added/updated in backend/.env

| Variable | Value |
|---|---|
| `BRIGHTDATA_BROWSER_ZONE` | `pulselens_browser` |
| `PRICING_USE_UNLOCKER` | `true` |
| `PRICING_USE_BROWSER_FALLBACK` | `true` |
| `PRICING_UNLOCKER_MIN_CONTENT_CHARS` | `1500` |
| `PRICING_MIN_PRICE_PATTERN_COUNT` | `1` |

Existing vars preserved: `OPENROUTER_API_KEY`, `BRIGHTDATA_API_KEY`, `BRIGHTDATA_SERP_ZONE`, `BRIGHTDATA_SCRAPER_ZONE`, `BRIGHTDATA_UNLOCKER_ZONE`, `ALPHA_VANTAGE_API_KEY`.

Secrets were NOT printed at any point during implementation.

---

## BrightDataClient Changes

Added to `__init__` (`brightdata_client.py:59`):
```python
self._explicit_browser_zone: bool = browser_zone is not None
```

Added property (`brightdata_client.py:68`):
```python
@property
def has_browser_zone(self) -> bool:
    """True only when BRIGHTDATA_BROWSER_ZONE was explicitly configured."""
    return self._explicit_browser_zone
```

- `from_env()` unchanged — already passes `browser_zone=os.getenv("BRIGHTDATA_BROWSER_ZONE") or None`
- `scrape_page`, `scrape_protected_page`, `scrape_dynamic_page` signatures unchanged
- `has_browser_zone` returns `True` after adding `BRIGHTDATA_BROWSER_ZONE=pulselens_browser`

---

## Agent 2 Routing Changes

### New module constants
```python
_PRICING_USE_UNLOCKER = True          # route pricing_pages to scrape_protected_page
_PRICING_USE_BROWSER_FALLBACK = True   # enable browser escalation fallback
_PRICING_UNLOCKER_MIN_CONTENT_CHARS = 1500   # escalate if content < 1500 chars
_PRICING_MIN_PRICE_PATTERN_COUNT = 1   # escalate if 0 price patterns found
```

### `_scrape_by_source_type` routing change
`pricing_pages` now routes to `scrape_protected_page` (Web Unlocker zone) instead of `scrape_page` (basic scraper):
```python
if source_type == "pricing_pages" and _PRICING_USE_UNLOCKER:
    return await client.scrape_protected_page(url)
```
All other source types unchanged.

### New helper functions (deterministic, zero I/O)
- `count_pricing_patterns(content)` — counts `$N.NN/hr`, `NNN USD`, `per N hour/month` patterns
- `should_allow_browser_pricing_domain(url)` — allowlist check (coreweave, runpod, lambdalabs, lambda.ai, aws, azure, gcp, oracle, supermicro, thinkmate) + blocklist (sec.gov, ir.*, investor.*)
- `should_escalate_pricing_page(content, url, source_type, price_count)` → (bool, reason_str) — escalates on snippet_only / content_too_short / no_pricing_patterns
- `choose_better_pricing_payload(normal, browser)` — prefers browser only if more price patterns or 20% longer content

### Browser escalation flow in `collect_documents_for_query`
After initial fetch (Web Unlocker), if `source_type == "pricing_pages"` and `client.has_browser_zone` and domain is in allowlist:
1. Call `_maybe_browser_escalate_pricing(client, url, payload, query_audit)`
2. Function checks escalation conditions — records telemetry regardless
3. If escalation needed: calls `client.scrape_dynamic_page(url)` (Browser API, render_js=True)
4. Runs `choose_better_pricing_payload` — only adopts browser result if it improved content
5. On browser exception: keeps original payload, records error in telemetry, does NOT crash

Browser escalation is **not** applied in `_run_per_query_fallbacks` (already a last resort).

### Non-pricing retrieval unchanged
SEC filings, IR pages, press releases, serp_news, job_pages — all unaffected.

---

## Telemetry Fields Added

### Per-query `pricing_escalations` list (in web_collection_audit.json)
Each element:
```json
{
  "url": "...",
  "normal_scrape_content_length": 450,
  "normal_scrape_content_quality": "full_text",
  "normal_scrape_price_pattern_count": 0,
  "escalated_to_browser": true,
  "browser_content_length": 4200,
  "browser_price_pattern_count": 8,
  "browser_error": null,
  "final_scrape_method": "browser",
  "pricing_escalation_reason": "no_pricing_patterns",
  "pricing_escalation_improved_content": true
}
```

### Summary counters (in web_collection_audit.json root)
```json
{
  "pricing_browser_escalation_attempts": 0,
  "pricing_browser_escalation_successes": 0,
  "pricing_browser_escalation_failures": 0,
  "pricing_browser_improved_docs": 0
}
```

---

## Pricing Diagnosis Script Changes

Added `load_browser_escalation_stats(artifact_dir)` function that reads `web_collection_audit.json` and aggregates browser escalation telemetry.

In `run_diagnosis()`: the summary JSON now includes a `browser_escalation` key with:
- `browser_escalated_count`
- `browser_improved_count`
- `browser_failed_count`
- `top_domains_browser_helped`
- `top_domains_browser_did_not_help`

Console output includes a new "Browser escalation stats" section.

---

## Tests Added

**File:** `backend/tests/pipeline/test_pricing_browser_routing.py`

12 zero-cost tests (no API calls, no BrightData calls):
| Test | Description | Result |
|---|---|---|
| T1 | snippet_only → should_escalate=True | ✅ PASS |
| T2 | short content (200 chars) → content_too_short | ✅ PASS |
| T3 | long content, 0 price patterns → no_pricing_patterns | ✅ PASS |
| T4 | long content with price patterns → no escalation | ✅ PASS |
| T5 | sec.gov → not allowed (never escalate) | ✅ PASS |
| T6 | ir.amd.com → not allowed (never escalate) | ✅ PASS |
| T7 | serp_news source_type → not_pricing_pages | ✅ PASS |
| T8 | coreweave.com → allowed | ✅ PASS |
| T9 | example.com → not allowed | ✅ PASS |
| T10 | choose_better: browser more patterns → returns browser | ✅ PASS |
| T11 | browser exception → returns original, error recorded | ✅ PASS |
| T12 | count_pricing_patterns regex matching | ✅ PASS |

---

## All Zero-Cost Checks

| Check | Result |
|---|---|
| `BrightDataClient` import | ✅ PASS |
| `pipeline` import | ✅ PASS |
| `test_pricing_browser_routing.py` (12 tests) | ✅ 12/12 PASS |
| `test_agent1_expansion_stability.py` (4 tests) | ✅ 4/4 PASS |
| `test_agent1_signal_balance.py` (15 tests) | ✅ 15/15 PASS |

**No live API calls were made during implementation.**  
**No secrets were printed at any point.**

---

## Live Evaluation Command (run only after explicit approval)

```bash
cd /mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens/backend
PULSELENS_DEMO_SCOPE=true python scripts/demo_track2_ai_hardware_audit.py
```

Expected improvements vs. baseline (report_5760ae7b9861):
- coreweave.com pricing pages: Browser API renders JS price tables → should increase pricing fact yield
- runpod.io blog pages: These are comparison guides, NOT primary price sources — browser rendering will not help (content is still a guide, not a price table). These are expected to remain zero-fact.
- Overall: pricing_pressure signal may improve from 4 facts toward 5–10 facts if coreweave/lambda render correctly

---

## Rollback

```bash
cp backend/.env.backup_before_brightdata_browser_config backend/.env
git checkout backend/app/utils/brightdata_client.py
git checkout backend/app/pipeline/agent2_web_workers.py
git checkout backend/scripts/pricing_document_extraction_diagnosis.py
rm backend/tests/pipeline/test_pricing_browser_routing.py
```
