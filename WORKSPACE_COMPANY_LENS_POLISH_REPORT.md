# Workspace Company Lens Polish Report

## Files Changed

| File | Change |
|---|---|
| `frontend/src/modules/workspace/pages/companies-page.tsx` | Implemented 7 UX/trust polish improvements without changing architecture. |

## 1. ID Stripping Behavior

Added a non-mutating display helper `stripIds(text: string)` that removes bracketed citations (e.g. `[claim_123]` or `[fact_456]`) and normalizes whitespace. This is applied at render time to:
- Company narrative text (`n.narrative`)
- Key drivers (`n.key_drivers`)
- Evidence card claim (`fact.claim`)
- Evidence card quote (`fact.evidence_quote`)

The underlying API data remains unchanged; raw strings with citations can still be copied via the system clipboard if needed by other components, but the visual text is clean.

## 2. Quick Summary Derivation

Added a "Quick insights" summary chip row directly below the header. It derives its data entirely from the dynamically computed `companyStats`:
- **Most evidence**: Shows the company with the highest total `cFacts.length`
- **Pricing pressure**: Shows the company with the highest `pricing_pressure` signal count
- **Product momentum**: Shows the company with the highest `product_launch` signal count

These chips are not hardcoded. They safely evaluate the arrays and will not render empty/invalid chips if the current report lacks facts matching those specific metrics.

## 3. Active Evidence Preview Context

The "Evidence Preview" section header now explicitly displays the currently active filter context:
- E.g., `Evidence Preview · All Companies` or `Evidence Preview · AMD`
- Added a fact count indicator: `· Showing X of Y facts` where `X` is the number of facts currently rendered (capped at 8) and `Y` is the total number of facts matched for that company in the report.
- The "Clear filter" button was restyled for better visibility.

## 4. Comparison Table Affordance

Added a final column to the comparison table with a distinct `Inspect →` button. 
- Clicking this button has the exact same behavior as clicking the row (which is preserved), setting the selected company and updating the evidence preview below.
- This provides an explicit call-to-action for the interactive row behavior, which was previously implicit.

## 5. Trust Note Added

Added the following disclaimer text right below the main header:
> *"Company reads are synthesized from the latest report. Evidence counts and signal distributions are computed from source-backed facts."*

This clearly establishes the boundary between LLM-synthesized narrative properties and hard metrics derived from verifiable facts.

## 6. Typography & Spacing Improvements

- Increased gap spacing between key driver pills to `gap-2` and improved padding for better legibility.
- Signal distribution bars: increased label width, improved font sizes (`text-xs`), and added a slightly darker text color for numerical counts to enhance scannability.
- Comparison table typography remains precise but gained improved padding in the new Inspect column.

## 7. Correctness Preservation

✅ No hardcoded live metrics.
✅ No hardcoded report IDs.
✅ No direct Supabase calls.
✅ Signal distributions strictly use fact filtering, not the LLM-generated `report.signal_breakdown`.
✅ Entity matching correctly ignores `market`, `industry`, and `sector`.
✅ All metrics are dynamically derived from the React Query `facts` prop.

## Build Result

```
✓ 2302 modules transformed.
dist/index.html                   0.74 kB │ gzip:   0.41 kB
dist/assets/index-C_eh0zAx.css   44.73 kB │ gzip:   8.55 kB
dist/assets/index-Q8LCG0Cn.js   357.10 kB │ gzip: 101.60 kB
✓ built in 8.32s — Exit code: 0
```

## Remaining Limitations

1. **Evidence Preview Cap**: Still visually caps at 8 items to keep the layout manageable. The newly added "Showing 8 of 27 facts" label accurately signals this cap, directing users to the full "Evidence Explorer" link for complete access.
2. **Citation Accuracy**: The `stripIds` regex assumes `[claim_xyz]` format. If backend citation styling changes (e.g., superscripts or different brackets), the regex will need updating.
