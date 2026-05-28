# Home Page Live Data Fix Report

**Date:** 2026-05-28  
**Scope:** Frontend Home Page only  
**Backend/Supabase changes:** None  
**Live pipeline run:** Not run

## Files Changed

- `frontend/src/modules/home/pages/home-page.tsx`
- `frontend/src/modules/home/lib/demo-baseline.ts`
- `frontend/src/modules/home/components/hero.tsx`
- `frontend/src/modules/home/components/market-snapshot.tsx`
- `frontend/src/modules/home/components/signal-coverage.tsx`
- `frontend/src/modules/home/components/fact-preview.tsx`
- `frontend/src/modules/home/components/how-it-works.tsx`

## Stale Values Removed

- Removed the Home hero's stale `"67 verified facts from 23 sources"` display.
- Removed hardcoded Market Snapshot text:
  - `"Avg confidence 0.905 · SAFE verified"`
  - `"0 suspicious claims · 0 false positives"`
- Removed How It Works stale metrics:
  - `"23 sources · 48 accepted docs"`
  - `"67 facts · 0 suspicious claims"`
  - `"10 verified claims · 52.7 pulse score"`
- Stopped using `report.signal_breakdown` as a fact-count source.
- Stopped passing `DEMO_FACTS` and stale `DEMO_REPORT_ID` unconditionally to Featured Insights.

## Live API Data Now Used

- `GET /api/reports/latest` resolves the current report ID.
- `GET /api/report/{latest_report_id}` loads the live `MarketPulseReport`.
- `GET /api/report/{latest_report_id}/facts` now loads live facts for Home Page evidence sections.

The following sections now use live backend data when available:

- **Hero:** `evidence_count`, `source_count`
- **Market Snapshot:** pulse score/status/confidence, evidence count, source count, quality status, average fact confidence, SAFE-verified fact count
- **Signal Coverage:** integer fact counts grouped from `/api/report/{id}/facts`
- **Featured Insights:** top live facts by confidence from `/api/report/{id}/facts`
- **How It Works:** source count, accepted document count, evidence count, SAFE-verified fact count, pulse score, quality status

## Trust Update: No Narrative-Derived Metrics

Removed the previous verified-claims inference from narrative text:

```ts
report?.grounded_brief?.strategic_implication?.match(...)
```

The Home Page no longer displays a `Verified Claims` metric because the current API does not expose a stable verified-claims count field. The previous card is now `SAFE-verified Facts`, computed directly from `/api/report/{id}/facts`:

```ts
facts.filter(f => f.safe_verified).length
```

If facts are loading, the card says it is checking fact-level verification. If facts are unavailable, it displays `—` and explains that fact-level verification is unavailable.

## Fallback Report ID Fix

Featured Insights now uses separate report IDs for live vs fallback evidence:

```ts
const previewReportId = factsFallback ? DEMO_REPORT_ID : displayReportId
```

This prevents fallback demo facts from appearing under a live report ID if `/api/report/{id}/facts` fails while `/api/report/{id}` succeeds.

## Signal Coverage Fix

`SignalCoverage` now receives integer fact counts computed from the `/facts` response:

```ts
facts.reduce((acc, f) => {
  acc[f.signal_type] = (acc[f.signal_type] ?? 0) + 1
  return acc
}, {})
```

It no longer treats `report.signal_breakdown` score floats as counts.

## Mock / Static Data Remaining

Static baseline data remains only in `demo-baseline.ts` and is used as a fallback when the backend API fails. The Home Page no longer shows fallback facts during normal live-data loading.

Fallback displays are labeled clearly:

- Page banner: `Demo baseline`
- Hero badge: `Demo baseline`
- Signal Coverage label: `fallback sample counts`
- Featured Insights label: `Demo baseline facts`
- Market Snapshot / How It Works: `Demo baseline`

Fallback company momentum values were corrected:

- `NVDA`: `mixed`
- `AMD`: `neutral`
- `SMCI`: `neutral`

No hardcoded live metrics remain on the Home Page. The remaining static values are fallback-only demo baseline values and are labeled as fallback/demo data.

## Navbar Verification

`frontend/src/shared/components/navbar.tsx` still renders visible brand text as:

```tsx
Pulse<span className="text-blue-600">Lens</span>
```

Visible text remains exactly `PulseLens`.

## Build Result

Command run:

```bash
cd frontend
npm run build
```

Result: **PASS** on the latest run after removing narrative-text verified-claim inference and switching to SAFE-verified fact counts.

Build completed successfully. Vite emitted a non-blocking chunk-size warning for the main JavaScript bundle.

## Remaining Limitations

- Verified-claim count is intentionally not displayed because the current `MarketPulseReport` API does not expose a dedicated stable `verified_claims_count` field.
- If the facts endpoint fails while the report endpoint succeeds, Home falls back to labeled sample fact/count data for evidence preview and signal coverage.
- Fact Preview displays the latest report ID and live facts, but the current app has no dedicated fact-detail route to deep-link individual facts.
