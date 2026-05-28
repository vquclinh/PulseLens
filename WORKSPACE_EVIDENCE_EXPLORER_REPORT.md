# Workspace Evidence Explorer Report

## Files Changed

- `frontend/src/modules/workspace/pages/workspace-page.tsx`
- `frontend/src/modules/workspace/pages/evidence-explorer-page.tsx`

## Evidence Explorer Layout

`/workspace/evidence` now renders a dedicated Evidence Explorer instead of the reused dashboard evidence tab.

The page includes:

- Page title: `Evidence Explorer`
- Explanation that facts are source-backed and loaded from the latest report
- Report ID shown as secondary metadata
- Summary cards for:
  - total facts
  - SAFE-verified facts
  - unique source domains
  - Tier 1/2 source domains

All metrics are derived from live facts loaded from FastAPI.

## Filters Implemented

Client-side filters:

- Signal type:
  - all
  - pricing_pressure
  - product_launch
  - investor_signal
  - strategic_messaging
  - supplier_risk
  - news_sentiment
  - hiring_momentum
- Entity/company:
  - all
  - Nvidia
  - AMD
  - Supermicro
  - market
  - any additional live entities present in facts
- Source tier:
  - all
  - Tier 1
  - Tier 2
  - Tier 3
  - Tier 4
- SAFE verified:
  - all
  - SAFE only

## Search Implemented

Client-side search covers:

- claim
- evidence quote
- entity
- source URL
- source domain
- signal type

## Sort Modes Implemented

- confidence descending
- source tier ascending
- newest published date
- signal type

## Evidence Fields Displayed

Each evidence card shows:

- claim
- evidence quote
- source domain
- source tier
- confidence
- sentiment
- signal type
- entity
- published date when available
- SAFE badge when `safe_verified === true`
- source URL link
- fact ID as secondary metadata only

## Interactions Added

- Clear filters button
- Copy evidence quote button
- Open source button
- Ask Chat link to `/chat`
- Search and filter controls update results client-side

The current chat route does not support deep-linked fact context yet, so `Ask Chat` keeps the interaction simple and routes to the grounded chat page.

## Empty, Loading, and Error States

Implemented honest states:

- loading latest evidence
- facts endpoint failed
- no evidence facts found
- no facts match active filters

Workspace Evidence does not fall back to demo/static facts.

## Data Source Verification

- `/workspace` still loads latest report ID from `GET /api/reports/latest`.
- `/workspace` still loads report data from `GET /api/report/{report_id}`.
- `/workspace/evidence` facts come from `GET /api/report/{report_id}/facts` through `fetchReportFacts`.
- Evidence uses the `['workspaceFacts', latestReportId]` query key.
- No frontend code calls Supabase directly.

## Hardcoded Live Data Check

- No hardcoded live metrics were added.
- No hardcoded report IDs were added.
- No stale `report_6a411aa14263` appears in workspace code.
- No stale `report_e68e7289fc30` appears in workspace live UI code.

## Navbar PulseLens Verification

Navbar visible brand remains exactly:

```txt
PulseLens
```

Implementation remains:

```tsx
Pulse<span className="text-blue-600">Lens</span>
```

## Build Result

Command:

```bash
cd frontend
npm run build
```

Result: PASS.

Output summary:

- TypeScript build passed.
- Vite production build passed.

## Remaining Limitations

- Evidence Explorer filtering is client-side. This is fine for the current demo-sized report, but server-side search/filtering may be needed for much larger report histories.
- `Ask Chat` links to `/chat` without passing the selected fact as deep-link context because the chat route does not yet accept URL/query fact context.
- There is no pagination yet. The current card layout renders all filtered facts.
