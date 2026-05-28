# Workspace Company Lens Report

## Files Changed

| File | Change |
|---|---|
| `frontend/src/modules/workspace/pages/companies-page.tsx` | **Created** — new dedicated Company Lens page |
| `frontend/src/modules/workspace/pages/workspace-page.tsx` | Replaced `CompaniesTab` with `CompaniesPage`; passes `facts`, `factsLoading`, `factsError` |

## Data Sources Used

All data flows from `WorkspacePage` props — no duplicate queries:

- `report` — from `fetchReport(latestReportId)` → `GET /api/report/{id}`
- `facts` — from `fetchReportFacts(latestReportId)` → `GET /api/report/{id}/facts`
- `factsLoading`, `factsError` — propagated from parent `WorkspacePage`
- Report ID sourced from `fetchLatestReportId()` → `GET /api/reports/latest`

No `localStorage` reads. No duplicate `useQuery` calls inside `CompaniesPage`.

## Company Metrics Derived

For each company in `report.company_narratives`:

| Metric | Derivation |
|---|---|
| Fact count | `facts.filter(matchEntity(company))` |
| SAFE-verified count | `.filter(f => f.safe_verified)` on company facts |
| Source domain count | `new Set(cFacts.map(sourceDomain)).size` |
| Average confidence | mean of `fact.confidence` over company facts |
| Top signal | signal_type with highest count in company facts |
| Latest published date | max `fact.published_date` in company facts |
| Signal distribution | `groupBy(signal_type)` counts, rendered as horizontal bars |

`report.company_narratives` fields used directly: `company`, `ticker`, `momentum`, `momentum_score`, `narrative`, `key_drivers`, `competitive_position`.

`report.signal_breakdown` is **not** used for fact counts.

## Entity Matching Approach

`matchEntity(entity, companyName, ticker)` — conservative:

- Compares `fact.entity` (lowercased) to company name and ticker (lowercased)
- Returns `false` immediately for `entity === "market"`, `"industry"`, `"sector"` — these are never attributed to a company
- Matches on exact equality or prefix overlap (e.g. `"nvidia"` → `"Nvidia"`)
- When uncertain, fact stays in "All" view only; never over-attributed to a company

## Interactions Added

- **Company selector pills** — All / per-company; toggles card highlight and evidence preview filter
- **Comparison table rows** — clickable; clicking a row toggles that company as the evidence preview filter
- **"View evidence" card button** — scrolls to evidence preview filtered to that company
- **Signal distribution bars** — visual proportion per signal type within each company's facts
- **"Clear ×"** on evidence preview header — resets to All

## No Hardcoded Live Metrics Confirmation

- All counts, percentages, dates, and domain lists are computed from live `facts` prop at render time
- No static fact arrays, no hardcoded counts, no hardcoded prices
- Company cards only show `key_drivers` from `report.company_narratives` — no invented drivers

## No Direct Supabase Call Confirmation

`companies-page.tsx` makes zero API calls. It only consumes props from `WorkspacePage`, which uses `fetchLatestReportId`, `fetchReport`, and `fetchReportFacts` — all FastAPI wrappers in `api-client.ts`.

## Navbar PulseLens Verification

`navbar.tsx` unchanged. Brand renders as:
```tsx
Pulse<span className="text-blue-600">Lens</span>
```
Visible text: `PulseLens` ✅

## Build Result

```
vite v6.4.2 building for production...
✓ 2302 modules transformed.
dist/index.html                   0.74 kB │ gzip:  0.42 kB
dist/assets/index-BcXanK_E.css   44.78 kB │ gzip:  8.56 kB
dist/assets/index-DQHcMm32.js   354.60 kB │ gzip: 101.06 kB
✓ built in 8.11s — Exit code: 0
```

## Remaining Limitations

1. **Entity matching is conservative by design** — facts with `entity = "market"` are never credited to a single company even if they mention a company name in the claim text. This avoids false attribution but means some relevant facts may only appear in "All" view.
2. **Evidence preview capped at 8 facts** — sorted by confidence descending. Full exploration remains in Evidence Explorer.
3. **No pagination** — works for current report sizes; large future reports may need pagination.
4. **`competitive_position` and `momentum`** come from `report.company_narratives`, which is an LLM synthesis; not independently verified from raw facts.
