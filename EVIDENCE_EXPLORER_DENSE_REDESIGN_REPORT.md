# Evidence Explorer Dense Redesign Report

**Date:** 2026-05-29  
**Build result:** ✅ PASS — `tsc -b && vite build` clean, 0 errors, 0 warnings, 6.04s

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/modules/workspace/pages/evidence-explorer-page.tsx` | Full redesign |

No other files modified.

---

## Compact Card Behavior

`CompactFactCard` (~90px per card, was ~300px):

- **Row 1:** Signal badge · Entity badge · SAFE badge (if verified) — right side: Tier badge · Sentiment badge · Confidence % · Domain · Date
- **Row 2:** Claim (1-line clamp, bold)
- **Row 3:** Evidence quote (1-line italic clamp) — right side: Copy icon · Open source icon · Ask Chat icon

Cards are clickable (`role="button"`, `tabIndex`, keyboard Enter/Space). Clicking toggles the right-side detail panel open/closed. CTAs (copy, source, chat) call `e.stopPropagation()` so clicking them doesn't toggle the card selection.

At a typical 900px viewport height, ~6–8 compact facts are visible vs ~1–2 with the old layout.

---

## Detailed View Behavior

`DetailedFactCard` — cleaned-up version of the old card:
- Signal/entity/SAFE badges at top
- Claim bold heading
- Full evidence quote as blockquote
- Metadata row (domain · confidence · date · fact_id muted)
- Actions: Copy quote · Open source · Ask Chat (same as before)

Switching to Detailed mode clears any selected fact (detail panel not used in detailed mode).

---

## Selected Fact Detail Panel

`FactDetailPanel` — sticky right-side column, only in Compact mode:

- Appears when a compact card is clicked; disappears on close (X) or re-clicking the same card
- Layout: `flex gap-5` — list takes `flex-1 min-w-0`, panel takes `w-[400px] shrink-0 sticky top-[88px]`
- Panel scrolls internally (`max-height: calc(100vh - 200px)`, `overflow-y: auto`)
- Shows:
  - Selected fact label with signal/entity/SAFE badges
  - Full claim
  - Full evidence quote
  - 2×3 metadata grid: Source · Confidence · Tier · Sentiment · Published · SAFE status
  - Fact ID (muted, monospace, break-all)
  - Actions: Copy quote · Open source · Ask Chat (full size buttons)

---

## View Mode Toggle

Simple segment control added to the filter row:
- Default: **Compact**
- Toggle: **Detailed**
- Switching to Detailed clears the selected fact
- Filter state is not reset when toggling view mode

---

## Summary Stats (Header)

Replaced the 4 large cards with compact inline chips in the page header. Shows: total facts · SAFE-verified · source domains · Tier 1/2 sources — all from the live facts payload, no hardcoded values.

---

## Query Param Filter Preservation

All existing deep-link behavior unchanged:
- `?signal=pricing_pressure` → `signalFilter` initialized to `pricing_pressure`
- `filterAreaRef` scroll anchor preserved between summary chips and linked-filter banner
- Linked filter banner with "Clear linked filter" button unchanged
- `clearFilters()` and `clearLinkedFilter()` unchanged
- All URL param logic (`setSearchParams`) unchanged

---

## Ask Chat Fact Attachment Behavior

Every fact card (compact and detailed) links to:
```
/chat?context=fact&fact_id=<fact_id>
```

The Chat page's `fact` context type:
- Shows the fact as an attachment card above the input (added in a prior session — `fact` is now in `isOverviewContext`)
- Has a dismiss button (X)
- When the user sends while the fact is attached, backend receives `context_attachment` with the full fact data
- The compact card's Ask Chat icon also uses this same URL

---

## Confirmation: No Fake Data / No Hardcoded IDs

- All facts come from `GET /api/report/{report_id}/facts` via `WorkspacePage.fetchReportFacts`
- Report ID comes from `GET /api/reports/latest` — not hardcoded
- No demo/placeholder facts added
- `report.report_id` displayed as secondary metadata in page header

---

## Build Result

```
tsc -b && vite build  ✓  6.04s — 0 errors, 0 warnings
```

---

## Remaining Limitations

1. **Detail panel on small screens:** The side panel layout (`flex gap-5`) uses `w-[400px]` fixed width. On screens narrower than ~800px, this may be tight. The panel still renders but may compress the list. A future improvement could hide the panel on mobile and show an inline expansion instead.
2. **Detail panel persistence:** If the user changes filters and the selected fact is filtered out, the panel stays open (showing the old fact). This is intentional — the user can still close it — but a future improvement could auto-close when the selected fact is no longer in `filteredFacts`.
3. **Compact card date/domain visibility:** The date and domain in row 1 are hidden on small screens (`hidden sm:inline` / `hidden md:inline`) to prevent wrapping. Users on small screens can click the card to see the detail panel with full metadata.

---

## Selected Evidence Detail Interaction Fix (2026-05-29)

### Root cause of global card resizing
The original side-panel implementation used a conditional CSS class on the **outer container** of the fact list. When `showDetailPanel` was true (any card selected), the outer `<div>` switched from no class → `flex gap-5 items-start`, and the fact list `<div>` switched from no class → `flex-1 min-w-0`. This caused every single card in the list to reflow into a narrower column simultaneously.

### Selected detail pattern chosen: Inline expand (Option A)
The selected card expands in place. All other cards are completely unaffected:
- Non-selected cards: same compact 3-row layout (~90px), unchanged
- Selected card: expands inline to show full claim, full blockquote, metadata grid, fact ID, and action buttons
- Clicking the meta row of the expanded card collapses it back
- Clicking another card collapses the previous selection and expands the new one

### Confirmation non-selected cards no longer resize
The outer list container is now a static `<div className="flex flex-col gap-2">` — its class never changes based on which card is selected. The `showDetailPanel` conditional wrapper and the `FactDetailPanel` side column have been removed entirely. Only the single clicked card changes its rendering branch.

### Confirmation Compact/Detailed view mode remains independent
- `viewMode` state is controlled only by the view toggle buttons
- `selectedFact` state is controlled only by card clicks
- Switching to Detailed mode calls `setSelectedFact(null)` (clears any expanded compact card), but does NOT affect `viewMode`
- Selecting a card in Compact mode does NOT change `viewMode`

### Confirmation filters and Ask Chat still work
All filters, search, sort, linked filter banner, query param deep-link, and scroll-to-filter behavior unchanged. Every card's Ask Chat icon still links to `/chat?context=fact&fact_id=<fact_id>`.

### Files changed
- `frontend/src/modules/workspace/pages/evidence-explorer-page.tsx` — 3 targeted edits:
  1. `CompactFactCard` rewritten with separate collapsed/expanded render branches sharing a common `metaRow`
  2. Main render: `showDetailPanel` conditional outer wrapper removed; fact list is always `<div className="flex flex-col gap-2">`
  3. `showDetailPanel` const removed (no longer needed)

### Build result
```
tsc -b && vite build  ✓  6.10s — 0 errors, 0 warnings
```

### Remaining limitations
1. `FactDetailPanel` component (originally the side panel) remains in the file as dead code since it is no longer rendered. It can be removed in a future cleanup pass.
2. The expanded card does not animate open/closed. A future improvement could add a smooth height transition.

---

## 2-Column Richer Card Layout (2026-05-29)

### Files changed
- `frontend/src/modules/workspace/pages/evidence-explorer-page.tsx` — full rewrite to single `EvidenceCard` component + 2-column grid

### New card design
`EvidenceCard` replaces both `CompactFactCard` and `DetailedFactCard`:

**Default state (all cards):**
- Top row: signal badge · entity badge · SAFE badge · Tier badge · Sentiment badge
- Claim: `line-clamp-2` — 2 lines visible, enough to understand the evidence
- Quote: `line-clamp-2` — blockquote with blue left border
- Meta: `domain · confidence · published date`
- Fact ID: muted monospace, truncated
- Footer: Copy · Source · Ask Chat

**Selected/expanded state (clicked card only):**
- Blue border ring (`border-blue-400 ring-2 ring-blue-100`)
- Claim: full text, no clamp
- Quote: full text, no clamp
- All other structure identical

### Grid layout
```
grid grid-cols-1 md:grid-cols-2 gap-4 items-start
```
- `grid-cols-1` on mobile
- `md:grid-cols-2` on desktop (≥768px) — 2 cards per row
- `items-start` — each card is only as tall as its content; cards never force-stretch each other
- Expanding one card makes only that card taller; the sibling in the same grid row stays at its natural height; other rows are completely unaffected

### Compact/Detailed toggle removed
The `ViewMode` type, `viewMode` state, `handleViewMode` function, and the view mode toggle in the filter bar have all been removed. A single richer `EvidenceCard` replaces both modes. The card shows enough information by default that users can scan without needing a separate "detailed" mode.

### Selection behavior unchanged
`selectedFact` state drives inline expand/collapse. Clicking the claim heading or anywhere on the expanded card header toggles the selection. Clicking another card collapses the previous and expands the new one. Other grid cards are visually unaffected.

### All filters, Ask Chat, and query params preserved
- All search/signal/entity/tier/SAFE/sort controls unchanged
- `?signal=` deep-link, scroll anchor, linked filter banner unchanged
- Every card's Ask Chat links to `/chat?context=fact&fact_id=<fact_id>`

### Build result
```
tsc -b && vite build  ✓  6.16s — 0 errors, 0 warnings
```

### Remaining limitations
1. In the 2-column grid, if one card expands significantly, the sibling in the same row gets extra whitespace at the bottom (its row height matches the taller card). This is standard CSS Grid behavior and is not jarring. The `items-start` alignment ensures no forced stretching.
2. On screens between `md` breakpoint and ~900px, two cards per row may be slightly tight. Cards remain readable at 110% browser zoom on standard laptop widths.

---

## Equal-Height Evidence Card Grid (2026-05-29)

### Files changed
- `frontend/src/modules/workspace/pages/evidence-explorer-page.tsx` — 3 targeted edits

### How equal-height cards were implemented
Three coordinated changes:

| Element | Change | Effect |
|---------|--------|--------|
| Grid container | `items-start` removed → default `items-stretch` | All cards in a row stretch to the same row height |
| `<article>` element | Added `h-full` to className | Article fills the full grid cell height |
| Footer `<div>` | Already had `mt-auto` | Footer sits at the bottom of the card regardless of content height |

The `flex flex-col gap-3` on `<article>` was already present. With `h-full`, the flex container fills the cell, and `mt-auto` on the footer pushes it to the bottom.

### Content clamp behavior
- Claim: `line-clamp-2` (unchanged) — ensures no card grows taller just because of a long claim
- Quote: `line-clamp-2` (unchanged) — ensures consistent mid-card height
- Source domain: `truncate` via `font-mono … truncate` on fact_id line
- No internal scrollbars added

### Footer alignment behavior
`mt-auto` on the footer `<div>` (already present) pushes Copy/Source/Ask Chat buttons to the bottom of every card. With equal-height cells, this means all action buttons in the same row align on the same horizontal line.

### Full detail access behavior
Clicking the claim heading expands that card (removes `line-clamp-2` from claim and quote). Only that card expands; because of `items-stretch`, its row-sibling stretches to match height, but with `mt-auto` its footer still sits at the bottom. No other rows change.

### Responsive behavior
- `grid-cols-1` on mobile: single column, equal-height is less relevant
- `md:grid-cols-2`: 2-column equal-height grid on desktop

### Confirmation: filters/search/sort, Ask Chat all work
No logic or behavior changes — only CSS class changes to the grid container and article element.

### Build result
```
tsc -b && vite build  ✓  6.11s — 0 errors, 0 warnings
```

### Remaining limitations
When a selected card expands (unclamped content), its grid row-sibling stretches to match the expanded height. This is standard CSS Grid behavior and keeps the equal-height invariant. The sibling card's content stays at the top with whitespace below; the footer stays at the bottom via `mt-auto`.

---

## Fact ID Display Cleanup (2026-05-29)

### Files changed
- `frontend/src/modules/workspace/pages/evidence-explorer-page.tsx` — 1 edit

### fact_id display cleanup
The `<p>` element rendering `{fact.fact_id}` as a visible muted monospace line on every card was removed. It has been replaced with a comment noting that the value is still used internally.

### fact_id remains available internally
`fact.fact_id` is still used in:
- `key={fact.fact_id}` — React list key
- `isSelected={selectedFact?.fact_id === fact.fact_id}` — selection tracking
- `to={\`/chat?context=fact&fact_id=${fact.fact_id}\`}` — Ask Chat link

The ID was never removed from the data object — only the visual rendering was removed.

### Ask Chat still works
Every card's Ask Chat button still navigates to `/chat?context=fact&fact_id=<fact_id>`. The Chat page reads `fact_id` from the URL param to identify and attach the correct fact as context. No behavior change.

### Build result
```
tsc -b && vite build  ✓  6.08s — 0 errors, 0 warnings
```
