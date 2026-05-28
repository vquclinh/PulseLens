# Workspace Pipeline Audit Center Report

## Files Changed

| File | Change |
|---|---|
| `frontend/src/modules/workspace/pages/pipeline-audit-page.tsx` | Completely rewritten to accept live `report` and `facts` props and dynamically render data provenance, quality gates, and live metrics. |
| `frontend/src/modules/workspace/pages/workspace-page.tsx` | Updated `PipelineAuditPage` invocation to explicitly pass `report`, `facts`, `factsLoading`, and `factsError`. |

## Data Sources Used

All data is securely passed down from the `WorkspacePage` components, which sources data strictly from:
- `GET /api/reports/latest`
- `GET /api/report/{id}`
- `GET /api/report/{id}/facts`

## Live Report / Fact Metrics Shown

- **Quality Status**: `report.quality_status`
- **Evidence Facts**: Computed length of the `facts` array.
- **SAFE Verified**: Derived by counting facts where `safe_verified === true`.
- **Source Domains**: Derived by extracting and deduplicating root hostnames from `fact.source_url`.
- **Pulse Score**: `report.pulse_score`
- **Generated At**: Formatted from `report.generated_at`
- **Source Quality Breakdown**: Computed percentage mix of tiers `1`, `2`, `3`, `4`.
- **Top Domains**: Extracted frequency counts of source domains.
- **Average Confidence**: Computed mean of `fact.confidence`.

## Pipeline Stages Rendered

A polished timeline section has been added detailing the 8-stage PulseLens pipeline:
1. Query planning
2. Web collection
3. Fact extraction
4. SAFE verification
5. Signal scoring
6. Narrative synthesis
7. Report assembly
8. Database persistence

This section explains the *methodology* and data flow at each stage rather than injecting fake metrics.

## Audit Fields Used

The "Pipeline Quality Gate" section surfaces data from `report.audit_summary` (if available in the payload):
- `query_count`
- `accepted_doc_count`
- `missing_signal_types`
- It also iterates over `report.quality_reasons` to surface warnings directly to the user.

## Fallback / Unavailable Audit Handling

- If `report.audit_summary` is missing (e.g. not exposed by the current FastAPI payload for this specific run), the UI degrades gracefully, showing an honest message:
  > *"Detailed audit artifacts are not exposed through the current frontend API payload for this report. This page displays live report/fact-derived quality indicators and process transparency."*
- A "Data Provenance" section explicitly states that the workspace pages only use the live FastAPI backend, and mock fallback data is strictly confined to the Home page marketing view.

## Correctness Affirmations

✅ **No hardcoded live metrics**: All numbers (safe counts, tier counts, domains) are evaluated dynamically from the `facts` payload.
✅ **No direct Supabase calls**: Data flow explicitly states and relies entirely on standard `/api/` fetch requests. Postgres persistence is a backend concern.
✅ **No fake audit numbers**: Unavailable audit details result in an empty state, not mock integers.
✅ **Navbar verification**: `navbar.tsx` is unmodified; brand text remains exactly `PulseLens`.

## Build Result

```
✓ 1664 modules transformed.
dist/index.html                   0.74 kB │ gzip:   0.41 kB
dist/assets/index-CL1ATnf3.css   46.95 kB │ gzip:   8.86 kB
dist/assets/index-BB0UWmk6.js   388.16 kB │ gzip: 105.84 kB
✓ built in 6.05s — Exit code: 0
```

## Remaining Limitations

1. **Static Stage Explanations**: The 8-step pipeline timeline describes the process statically. In the future, if the backend emits discrete timing metadata per stage (e.g., "Web collection took 14s"), that could be integrated here.
2. **Domain Parsing**: Uses a lightweight `URL().hostname` `try/catch` block for domain extraction. It strips `www.` but does not normalize complex subdomains (e.g., `news.ycombinator.com` is distinct from `ycombinator.com`).
