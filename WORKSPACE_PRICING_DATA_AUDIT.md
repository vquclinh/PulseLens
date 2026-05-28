# Workspace Pricing Data Audit

Audit of `/workspace/pricing` for data correctness, hardcoded/mock values, and display-layer scraper artifact risks.

---

## 1. Data Flow Verification

| Question | Result |
|---|---|
| Does `/workspace/pricing` receive `report`/`facts` from `WorkspacePage`? | ✅ YES — `PricingPage` accepts `{ report, facts, factsLoading, factsError }` as props |
| Does `WorkspacePage` load latest report ID from `fetchLatestReportId()`? | ✅ YES — `queryFn: fetchLatestReportId` via React Query |
| Does it load report from `fetchReport(latestReportId)`? | ✅ YES — `queryFn: () => fetchReport(latestReportId!)` |
| Does it load facts from `fetchReportFacts(latestReportId)`? | ✅ YES — `queryFn: () => fetchReportFacts(latestReportId!)` |
| Does `PricingPage` avoid duplicate/stale network queries? | ✅ YES — it makes no `useQuery` calls; data flows entirely from parent props |
| Does `PricingPage` avoid `localStorage` as source of truth? | ✅ YES — no `localStorage.getItem` present in `pricing-page.tsx` |
| Does `PricingPage` avoid hardcoded report IDs? | ✅ YES — `report.report_id` is the live dynamic value displayed |

**`localStorage.setItem`** is called once in `workspace-page.tsx` (line 143) to *cache* the latest report ID for dashboard interop, but it is never read back inside pricing. This is safe.

---

## 2. User-Visible Values Inventory

| Displayed Element | Source Classification |
|---|---|
| Page title: `Pricing Intelligence` | ✅ Static UI label |
| Section subtitle copy | ✅ Static UI label |
| Report ID in header | ✅ Live: `{report.report_id}` from `fetchLatestReportId()` → `fetchReport()` |
| Report ID in empty-state message | ✅ Live: `{report.report_id}` |
| Total pricing facts count | ✅ Live facts derived: `pricingFacts.length` |
| SAFE-verified facts count | ✅ Live facts derived: `pricingFacts.filter(f => f.safe_verified).length` |
| Unique source domains count | ✅ Live facts derived: `new Set(pricingFacts.map(f => sourceDomain(f.source_url))).size` |
| Tier 1/2 pricing facts count | ✅ Live facts derived: `pricingFacts.filter(f => f.source_tier <= 2).length` |
| Filter: Company options | ✅ Live facts derived: base list ∪ `new Set(pricingFacts.map(f => f.entity))` |
| Filter: Source domain options | ✅ Live facts derived: `new Set(pricingFacts.map(f => sourceDomain(...)))` |
| Filter: Tier options (All/1/2/3/4) | ✅ Static UI labels for UI controls — values used for filtering live data |
| Filter: SAFE options (All/SAFE Only) | ✅ Static UI labels for UI controls |
| Matching facts count label | ✅ Live facts derived: `filteredFacts.length` |
| Provider summary: domain | ✅ Live facts derived: `sourceDomain(fact.source_url)` per fact |
| Provider summary: facts count | ✅ Live facts derived: aggregate of matching pricing facts |
| Provider summary: best tier | ✅ Live facts derived: `Math.min(...source_tier values)` |
| Provider summary: avg confidence | ✅ Live facts derived: mean of `fact.confidence` values |
| Card: entity badge | ✅ Live: `fact.entity` |
| Card: SAFE badge | ✅ Live: `fact.safe_verified` |
| Card: confidence % | ✅ Live: `(fact.confidence * 100).toFixed(0)` |
| Card: tier badge | ✅ Live: `fact.source_tier` |
| Card: sentiment badge | ✅ Live: `fact.sentiment` |
| Card: claim heading | ✅ Live: `fact.claim` |
| Card: evidence quote | ✅ Live: `displayQuote(fact.evidence_quote)` (display-only sanitization, raw fact preserved) |
| Card: source domain | ✅ Live: `sourceDomain(fact.source_url)` |
| Card: published date | ✅ Live: `formatDate(fact.published_date)` |
| Card: fact ID (truncated) | ✅ Live: `fact.fact_id.substring(0, 12)` |
| GPU/product badges | ✅ Text-derived from `fact.claim` + `fact.evidence_quote`, labeled `Detected in evidence` |
| Price snippet badges | ✅ Text-derived from `fact.claim` + `fact.evidence_quote`, labeled `Detected in evidence` |
| CTA copy: "all signal types in the latest report" | ✅ Static UI label (was `60+`, now corrected — see §3) |
| CTAs: links to `/workspace/evidence`, `/chat`, `/workspace/signals` | ✅ Static navigation labels |

---

## 3. Hardcode / Stale Search Results

### Stale Report IDs in `frontend/src`
```
frontend/src/modules/home/lib/demo-baseline.ts
3: export const DEMO_REPORT_ID = 'report_e68e7289fc30'
```
> ⚠️ **Present in `demo-baseline.ts`, but SAFE**: This file is only imported by `home-page.tsx` as an explicit labeled fallback when the live API is unavailable. It is displayed with a yellow "Demo baseline" banner saying *"Start the backend to load live data"*. It is **not imported anywhere in the workspace module**, not in `workspace-page.tsx`, not in `pricing-page.tsx`. The workspace pricing tab does not use it in any code path.

No stale IDs found in:
- `frontend/src/modules/workspace/**`
- `frontend/src/lib/**`

### Hardcoded Prices
None found in workspace or library code.

`demo-baseline.ts` line 70–71 contains `"$68.80/hr"` — but this is confined to the Home page demo fallback and never surfaces in the workspace pricing tab.

### Hardcoded Provider/Domain Lists
None in workspace pricing. The domain filter dropdown is 100% derived from live pricing facts.

### Hardcoded GPU Names
`GPU_MODELS` constant in `pricing-page.tsx` (line 37) contains:
```ts
['H100', 'H200', 'B200', 'Blackwell', 'MI300X', 'MI325X', 'MI355X', 'L40S', 'A100']
```
> ✅ **Allowed**: This is a detection vocabulary, not a display list. It is used only to scan `claim` and `evidence_quote` text — no GPU badge is ever shown unless the term is found in the live fact text. No GPU names are rendered without a matching live fact.

### Mock/Static/Demo Pricing Facts
None in workspace. `DEMO_FACTS` in `demo-baseline.ts` is isolated to the Home page demo fallback.

### Hardcoded Fact Count
- **Found**: `"60+ verified facts"` in a CTA description (line 615). This was an approximate count from the original report that was inadvertently hardcoded as UI copy.
- **Fixed**: Replaced with `"all signal types in the latest report"` — now purely descriptive, no count.

---

## 4. Pricing Fact Derivation

Confirmed at line 234–237:
```ts
const pricingFacts = useMemo(
  () => facts.filter(fact => fact.signal_type === 'pricing_pressure'),
  [facts]
)
```
- All 4 summary cards, all filter options, all fact cards, the provider summary table, and the filtered count are derived **exclusively** from `pricingFacts`.
- `facts` itself comes from `fetchReportFacts(latestReportId)` via props from `WorkspacePage`.
- There is no secondary query, no localStorage read, no static fact array used in the workspace pricing tab.

---

## 5. Derived Metadata Correctness

### GPU/Product Detection
```ts
function detectGPUs(claim: string, quote: string): string[] {
  const combined = `${claim} ${quote}`
  return GPU_MODELS.filter(model => {
    const regex = new RegExp(`\\b${model}(?:s)?\\b`, 'i')
    return regex.test(combined)
  })
}
```
- ✅ Only scans `fact.claim` and `fact.evidence_quote`.
- ✅ Uses word boundaries — `L40S` in `"L40S pricing"` matches, but `"L40Sxyz"` does not.
- ✅ Labeled `Detected in evidence` in the UI, not presented as structured database fields.
- ✅ Nothing is shown if no GPU is matched — fact is still displayed normally.
- ✅ No GPU is invented if absent from text.

### Price Snippet Extraction
```ts
const PRICE_REGEX = /\$\d+(?:,\d{3})*(?:\.\d+)?\s*(?:k|K|...)(...)?/gi
```
- ✅ Only extracts exact substrings already present in `claim` + `evidence_quote`.
- ✅ No normalization, conversion, comparison, or arithmetic is performed.
- ✅ Duplicates are de-duplicated via `Array.from(new Set(...))`.
- ✅ Trailing whitespace removed via `.trim()`.
- ✅ **FIXED**: `$0` and `$0.00` junk results (CSS/JS artifact false positives) are now filtered out:
  ```ts
  .filter(snippet => !/^\$0(?:\.0+)?\s*$/.test(snippet))
  ```
- ✅ Labeled `Detected in evidence` in UI — not presented as canonical structured data.
- ✅ Nothing shown if no price found — fact still displayed normally.
- ✅ No missing prices invented.

### Evidence Quote Display
- **FIXED**: A `displayQuote()` function is applied to the rendered blockquote only.
- Raw `fact.evidence_quote` is preserved for: copy-quote clipboard, search indexing.
- `displayQuote()` strips: `<script>`, `<style>`, HTML tags, CSS `.class-name { }` fragments, JS patterns (`function()`, `var x`, `document.`, `window.`, `DOMScript`).

---

## 6. Artifact/Quote Cleanup

### Scraper artifacts in evidence_quote display
**Issue found and fixed**: The PRICE_REGEX matched `$0` from JavaScript scraper artifacts (e.g., CSS properties or JS variables containing `$0`). This would have produced a false `$0` price badge.

**Fix applied (display-only)**: 
1. `extractPriceSnippets` now filters out `$0`/`$0.00` snippets.
2. `displayQuote()` helper strips HTML tags, CSS fragments, and JS function/variable patterns from the rendered blockquote text.

No HTML is injected — quotes are always rendered as React text content (safe from XSS), but scraper artifacts render as visible noise to analysts.

---

## 7. Issues Found and Fixes Applied

| # | Issue | Severity | Fix |
|---|---|---|---|
| 1 | `$0` false positive from PRICE_REGEX on scraper artifacts | Medium | Added `.filter(snippet => !/^\$0(?:\.0+)?\s*$/.test(snippet))` to `extractPriceSnippets` |
| 2 | Raw `evidence_quote` rendered without display cleanup | Low | Added `displayQuote()` helper; applied to blockquote render only; raw fact preserved |
| 3 | Hardcoded `"60+"` fact count in CTA copy | Low | Changed to `"all signal types in the latest report"` |

**File changed**: `frontend/src/modules/workspace/pages/pricing-page.tsx` only.

No backend changes. No other pages modified.

---

## 8. Build Result

```bash
cd frontend && npm run build
```

```
vite v6.4.2 building for production...
✓ 2301 modules transformed (after fixes: same module count)
dist/index.html                   0.74 kB │ gzip:  0.42 kB
dist/assets/index-bQ7TuJYm.css   41.65 kB │ gzip:  8.20 kB
dist/assets/index-0EUFMxT9.js   340.71 kB │ gzip: 99.04 kB
✓ built in 8.03s

Exit code: 0
```

---

## 9. Final Confirmations

| Check | Result |
|---|---|
| No hardcoded report IDs in pricing tab | ✅ Confirmed |
| No hardcoded prices in pricing tab | ✅ Confirmed |
| No hardcoded providers/domains in pricing tab | ✅ Confirmed |
| GPU vocabulary is detection-only, not display list | ✅ Confirmed |
| No mock/static/demo pricing facts in workspace | ✅ Confirmed |
| `PricingPage` uses only live backend facts | ✅ Confirmed |
| No direct Supabase calls in frontend | ✅ Confirmed |
| Navbar brand text is exactly `PulseLens` | ✅ Confirmed (unchanged) |
| Build passes after fixes | ✅ Exit code 0 |

## Remaining Limitations

1. **`displayQuote()` is a best-effort heuristic**: It removes common patterns, but unusual scraper artifacts not matching the strip patterns will still render as visible text. If the backend scraping quality is improved, display-layer cleanup becomes unnecessary.
2. **`$30,000 ` trailing-space edge case**: The `.trim()` call handles this correctly, but the trailing-space match in the regex is a minor imprecision. Not a data correctness issue.
3. **Client-side only**: All filtering/aggregation is in the browser. Large report histories would benefit from server-side pagination, but this is a scalability concern not a correctness concern.
4. **`demo-baseline.ts` stale report ID**: `report_e68e7289fc30` exists in the codebase but is scoped entirely to the Home page's labeled fallback mode. It does not reach the workspace pricing tab in any code path. No fix needed, but the file should be documented as a deliberate demo baseline.
