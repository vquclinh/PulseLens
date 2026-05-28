# Chat Context Polish Report

## Files Changed

| File | Change |
|---|---|
| `frontend/src/modules/chat/pages/chat-page.tsx` | Redesigned to read `?context=` URL parameters, parse live backend `facts` and `report` data, and display dynamic Context Cards. |
| `frontend/src/modules/workspace/pages/companies-page.tsx` | Updated CTAs to pass `?context=company&company=[ticker]` and `?context=fact&fact_id=[id]`. |
| `frontend/src/modules/workspace/pages/signals-page.tsx` | Updated CTAs to pass `?context=signal&signal=[type]` and `?context=fact`. |
| `frontend/src/modules/workspace/pages/pricing-page.tsx` | Updated CTAs to pass `?context=pricing` and `?context=fact`. |
| `frontend/src/modules/workspace/pages/evidence-explorer-page.tsx` | Updated Evidence Card CTAs to pass `?context=fact&fact_id=[id]`. |
| `frontend/src/modules/workspace/pages/pipeline-audit-page.tsx` | Updated bottom CTA to pass `?context=report`. |
| `frontend/src/modules/workspace/pages/workspace-page.tsx` | Updated sidebar and shell CTAs to pass `?context=report`. |
| `frontend/src/modules/workspace/pages/workspace-overview.tsx` | Updated summary CTAs to pass `?context=report`. |

## Supported URL Contexts

The `/chat` endpoint now natively parses and acts upon 5 distinct contexts:
1. **Fact**: `/chat?context=fact&fact_id=fact_12345`
2. **Company**: `/chat?context=company&company=AMD`
3. **Signal**: `/chat?context=signal&signal=pricing_pressure`
4. **Pricing**: `/chat?context=pricing`
5. **Report**: `/chat?context=report`

## Context Card Behavior

If valid parameters are passed, a dynamic **Context Card** appears above the message history:
- It safely extracts the requested target from the live FastAPI `facts` array.
- It displays context-specific metrics (e.g., number of supporting facts for a company, the exact claim text and source domain for a fact).
- If the parameters are invalid, or if the specified target does not exist in the latest report, the UI gracefully falls back to a message: *"Context not found in the latest report. You can still ask about the report."*

## Suggested Prompt Behavior

- The Context Card renders three **suggested prompt chips** tailored to the active context (e.g., *"What other facts support this?"* for a Fact context).
- Clicking a prompt safely **populates the chat input box** (`setInput`) but does *not* automatically submit the message. This gives the user agency to edit or review the prompt before hitting send.

## Data Sources Used

All context derivations rely exclusively on:
- `fetchLatestReportId()`
- `fetchReport(reportId)`
- `fetchReportFacts(reportId)`
- Data is managed via React Query and passed securely to the UI without touching `localStorage` or making direct client-to-database connections.

## Correctness Affirmations

✅ **No hardcoded live metrics**: Fact counts, confidence scores, and valid tickers are computed dynamically from the live JSON payload.
✅ **No direct Supabase calls**: Data flow remains strictly routed through the FastAPI layer.
✅ **No hardcoded report IDs**: Displays `report.report_id`.
✅ **Navbar verification**: `navbar.tsx` is unmodified; brand text remains exactly `PulseLens`.

## Build Result

```
✓ 1664 modules transformed.
dist/index.html                   0.74 kB │ gzip:   0.42 kB
dist/assets/index-C0TYiF64.css   47.42 kB │ gzip:   8.92 kB
dist/assets/index-BuIzqoXq.js   394.56 kB │ gzip: 107.50 kB
✓ built in 5.99s — Exit code: 0
```

## Remaining Limitations

1. **Input Focus**: Clicking a suggested prompt chip populates the input state, but currently does not automatically set browser cursor focus to the input element.
2. **Entity Matching Strictness**: The Company context card utilizes the same string inclusion logic (`f.entity === company`) as the Company Lens. As such, slight entity name deviations in facts might not be counted perfectly towards the display total.
