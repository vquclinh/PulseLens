# Chat Context Attachment QA Report

**Date:** 2026-05-29  
**Frontend build:** ✅ PASS — `tsc -b && vite build` clean, 0 errors, 0 warnings, 6.16s  
**Backend syntax check:** ✅ PASS — `python -m py_compile` on 3 backend files

---

## Files Changed

### Backend
| File | Change |
|------|--------|
| `backend/app/schemas/models.py` | Added 5 evidence-fact fields to `ContextAttachment` model |
| `backend/app/chat/agent8_analyst_chat.py` | Updated `_build_attachment_block` to include new evidence fields |

### Frontend
| File | Change |
|------|--------|
| `frontend/src/types/index.ts` | Added 5 evidence-fact fields to `ContextAttachment` |
| `frontend/src/hooks/use-chat.ts` | Redesigned `AttachmentSnippet` with richer display fields |
| `frontend/src/modules/chat/components/chat-message.tsx` | Renders full attachment card (not just a pill) |
| `frontend/src/modules/chat/pages/chat-page.tsx` | Added `fact` to `isOverviewContext`; richer `buildAttachmentSnippet`; richer `buildContextAttachment` for all 3 types |

---

## No-Card Send Behavior (Case A — dismissed attachment)

After clicking X/dismiss:
1. `dismissAttachment()` sets `attachmentDismissed = true` and calls `setSearchParams({}, { replace: true })` — URL params cleared
2. On next render: `contextType = null` (URL cleared), `isOverviewContext = false`
3. `buildContextAttachment()` returns `undefined` (checked via `attachmentDismissed` and `!isOverviewContext`)
4. `buildAttachmentSnippet()` returns `undefined` (same guards)
5. `sendMessage(userText, userText, undefined, undefined)` → message stored with no snippet
6. API payload: `context_attachment` is `undefined` → not serialised into JSON
7. Backend receives no `context_attachment` — clean message to LLM ✓

---

## With-Card Send Behavior (Case B — active attachment)

When attachment is active and user presses Enter:
1. `buildContextAttachment()` returns the full structured object (type-specific fields)
2. `buildAttachmentSnippet()` returns the richer display card fields
3. `sendMessage(userText, userText, snippet, attachment)` called
   - Backend receives `context_attachment` with full structured data
   - `MessageWithFacts` stored with `attachmentSnippet` → rendered in bubble
4. `dismissAttachment()` called immediately after send:
   - `attachmentDismissed = true` — attachment bar disappears
   - URL cleared — no re-hydration on subsequent renders
5. Second message: `contextType = null`, `isOverviewContext = false` → no attachment ✓

---

## Submitted Message Compact Card Design

`AttachmentSnippet` redesigned with 7 fields:

| Field | Purpose |
|-------|---------|
| `label` | Pill badge: 'Watch item' / 'Risk alert' / 'Evidence fact' |
| `title` | Primary title (2-line clamp) |
| `badgeText` | Secondary badge (urgency, signal type) |
| `body` | Main text (rationale / note / evidence quote — 2-line clamp) |
| `body2` | Secondary text (trigger / detail — 1-line clamp) |
| `body2Label` | Prefix for `body2` (e.g. 'Trigger:') |
| `meta` | Footer: counts / entity+signal / domain+confidence |

Rendered as a rounded card with `border-blue-200 bg-blue-50` above the user bubble. No internal scroll. All fields clamped. Works at 110% zoom.

**Watch item card:**
```
[WATCH ITEM] [This Week]
Monitor Nvidia Blackwell supply constraints
Supply chain bottleneck detected as Blackwell ramp...
Trigger: If Q3 shipment guidance drops below 50k units...
```

**Risk alert card:**
```
[RISK ALERT] [investor signal]
AMD
Contradiction between earnings narrative and actual filings...
4 supporting · 2 against
```

**Evidence fact card:**
```
[EVIDENCE FACT]
AMD committed $10 billion investment in Taiwan semiconductor manufacturing
"$10 billion investment commitment in Taiwan"
AMD · investor signal · ir.amd.com · 94% conf
```

---

## Overview Evidence Preview Ask Chat Behavior (Case D)

`FactCard` in `workspace-overview.tsx` already links to `/chat?context=fact&fact_id=<fact_id>`.

**Before this fix:** `fact` context was NOT in `isOverviewContext` → showed at top of messages as a passive card with no attachment send behavior.

**After this fix:**
- `isOverviewContext` now includes `fact` (`contextType === 'fact'`)
- `isDismissible` in `ContextCard` now includes `fact` → X button appears
- `buildContextAttachment()` handles `fact` → sends full evidence data to backend:
  - `type`, `title` (claim), `entity`, `signal_type`, `summary`, `evidence_quote`, `confidence`, `source_domain`, `source_tier`, `fact_id`
- `buildAttachmentSnippet()` handles `fact` → rich card with claim, quoted evidence, and meta footer
- Attachment shows in the bar above input; auto-clears after first message sent

---

## Backend Context Attachment Handling

`ContextAttachment` Pydantic model now has 5 additional fields: `evidence_quote`, `confidence`, `source_domain`, `source_tier`, `fact_id`.

`_build_attachment_block` updated to iterate over new fields:
- String fields: `evidence_quote`, `source_domain`, `fact_id`
- Integer fields: `source_tier`
- Float field: `confidence` (formatted as percentage)

Backend prompt now includes a clearly labelled section:
```
Attached context (selected by the analyst from the PulseLens Overview):
Type: fact
Title: AMD committed $10 billion...
Entity: AMD
Signal type: investor_signal
Evidence quote: $10 billion investment commitment in Taiwan
Confidence: 94%
Source domain: ir.amd.com
Source tier: 1
Fact id: fact_abc123
```

---

## Stale Attachment Prevention

| Case | Guard mechanism |
|------|-----------------|
| X clicked before send | `attachmentDismissed = true` → both build functions return `undefined` |
| After send | `dismissAttachment()` clears URL → `contextType = null` → `isOverviewContext = false` |
| Second message | `isOverviewContext = false` → no attachment built |
| No context URL | `contextType = null` → `isOverviewContext = false` → normal chat |

The `attachmentDismissed` state acts as the immediate in-render guard. The URL clear acts as the durable cross-render guard. Both are required because React state updates are async.

---

## Streaming Compatibility

No streaming endpoint exists in this project. No changes needed.

---

## Build Result

```
tsc -b && vite build  ✓  6.16s — 0 errors, 0 warnings
python -m py_compile ... → OK
```

---

## Remaining Limitations

1. If facts haven't loaded yet when the user sends (e.g. slow connection), the `fact` attachment will not be included in the first message (returns `undefined` gracefully — clean fallback).
2. After attachment is consumed, re-attaching the same card requires re-navigating from the Overview.
3. `company`, `signal`, `pricing`, `report` contexts remain in the legacy "top of messages" display mode — they do not become sendable attachments. This is intentional to avoid breaking existing behavior.
