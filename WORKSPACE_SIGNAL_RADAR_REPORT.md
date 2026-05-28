# Workspace Signal Radar Report

## Files Changed

| File | Change |
|---|---|
| `frontend/src/modules/workspace/pages/signals-page.tsx` | **Created** — new dedicated Signal Radar page |
| `frontend/src/modules/workspace/pages/workspace-page.tsx` | Replaced `SignalsTab` with `SignalsPage`; passes `facts`, `factsLoading`, `factsError` |

## Data Sources Used

All data flows securely from `WorkspacePage` props:
- `report` — from `fetchReport(latestReportId)`
- `facts` — from `fetchReportFacts(latestReportId)`
- `factsLoading`, `factsError` — propagated from parent `WorkspacePage`

No duplicate queries, no `localStorage` reads, no direct Supabase calls.

## Signal Metrics Derived

For each signal present in either `report.top_signals` or the `facts` array:

| Metric | Derivation |
|---|---|
| Evidence fact count | `facts.filter(f => f.signal_type === sig)` |
| SAFE-verified count | `.filter(f => f.safe_verified)` on signal facts |
| Source domain count | `new Set(sFacts.map(sourceDomain)).size` |
| Average confidence | Mean of `fact.confidence` over signal facts |
| Top entity | Entity with highest frequency count in signal facts |
| Sentiment mix | Count of `positive`, `neutral`, `negative` in signal facts |

## Signal Breakdown Handling

- **`report.signal_breakdown`** is used *only* as a normalized "Score Contribution" (if available). It is explicitly labeled as such in the UI (e.g., `Score: 8.5`).
- It is **not** used as a fact count. Fact counts are securely derived by filtering the raw `facts` array.
- A trust note was added to explicitly clarify this distinction:
  > *Trust Note: Evidence counts are computed directly from source-backed facts. Signal scores are normalized report contributions and should not be read as fact counts.*

## Interactions Added

- **Signal selector pills**: All / specific signals; toggles card highlight and filters evidence preview.
- **Comparison table rows**: Clickable rows update the selected signal (with a clear `Inspect →` affordance).
- **Summary Cards**: Clickable cards (when viewing "All Signals") update the selected signal.

## Evidence Preview Behavior

- Displays the top facts (capped at 8) sorted by confidence descending.
- Header explicitly states the active context (e.g., `Evidence Preview · Product Launch`).
- Header shows the total matching facts versus the displayed subset (e.g., `Showing 8 of 15 facts`).
- Each evidence card preserves the `stripIds` implementation for clean claim/quote text while retaining copy functionality.

## Correctness Affirmations

✅ **No hardcoded live metrics**: All counts, percentages, and entities are computed from the live `facts` array.
✅ **No direct Supabase calls**: Data relies entirely on the FastAPI backend wrapper.
✅ **No hardcoded report IDs**: Displays `report.report_id`.
✅ **Navbar verification**: `navbar.tsx` is unmodified; brand text remains exactly `PulseLens`.

## Build Result

```
✓ 1664 modules transformed.
dist/index.html                   0.74 kB │ gzip:   0.41 kB
dist/assets/index-BLe1N0o3.css   45.66 kB │ gzip:   8.66 kB
dist/assets/index-BmHsRIqz.js   373.22 kB │ gzip: 103.05 kB
✓ built in 5.99s — Exit code: 0
```

## Remaining Limitations

1. **Entity Normalization**: The "Top Entity" derivation uses simple string trimming. If facts contain slight variations (e.g., "Nvidia" vs "Nvidia Corp"), they will be counted as distinct.
2. **Evidence Preview Cap**: The preview is capped at 8 items. Full exploration requires navigating to the Evidence Explorer.
3. **Score Contribution Guarantee**: `report.signal_breakdown` is treated as an optional map. If a pipeline run omits it, the "Score" badge degrades gracefully to `—`, but this could look slightly incomplete compared to a full report.
