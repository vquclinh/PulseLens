# Chat Overview Context Attachment Report

**Date:** 2026-05-29  
**Build result:** ✅ PASS — `tsc -b && vite build` clean, 0 errors, 0 warnings, 6.35s  
**Backend changes:** None — no backend files modified, no syntax check needed.

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/modules/workspace/pages/workspace-overview.tsx` | 4 URL updates + 1 button text rename |
| `frontend/src/hooks/use-chat.ts` | Added `displayContent` param to support hidden context prefix |
| `frontend/src/modules/chat/pages/chat-page.tsx` | Full rewrite — new context types, attachment bar, context prefix |

---

## `Chat` Renamed to `Ask Chat` in Overview Cards

In `WatchItemCard` (the marquee card body):
- Button text changed from `Chat` to `Ask Chat`
- Matches the label used in all other cards

---

## New Watch Item Chat Context

### URL
Clicking `Ask Chat` on a `What to monitor next` card navigates to:
```
/chat?context=watch_item&title=<encodeURIComponent(item.title)>
```

### Context card (Chat page)
- Finds the matching watch item from `report.market_narrative.watch_list` by title
- Shows: urgency badge, rationale (3-line clamp), trigger text, signal ref count
- Icon: `Eye` (lucide)
- Prompt chips: `Why should we monitor this?` · `What evidence supports this watch item?` · `What could change the market read?`
- If no match: `"Attached context was not found in the latest report. You can still ask about the report."`

### Context prefix sent to backend
```
[Attached watch item from PulseLens Overview — analyst context only]
Title: <item.title>
Urgency: <item.urgency>
Rationale: <item.rationale>
Trigger: <item.trigger>
Signal refs: <n>
---
User question: <typed text>
```

---

## New Risk Alert Chat Context

### URL
Clicking `Ask Chat` on a `Risk Alerts / Contradiction Review` card navigates to:
```
/chat?context=risk_alert&entity=<encodeURIComponent(c.entity)>&signal=<encodeURIComponent(c.signal_type)>
```

### Context card (Chat page)
- Finds the matching contradiction from `report.contradictions` by entity + signal_type
- Shows: entity badge, signal type badge, note (3-line clamp), supporting/against counts
- Icon: `AlertTriangle` (lucide, amber)
- Prompt chips: `Explain this contradiction` · `Which side has stronger evidence?` · `What should an analyst check next?`
- If no match: honest fallback message

### Context prefix sent to backend
```
[Attached risk alert from PulseLens Overview — analyst context only]
Entity: <entity>
Signal type: <signal_type>
Risk summary: <note>
Supporting facts: <n>
Against facts: <n>
---
User question: <typed text>
```

---

## Context Attachment UI Behavior

`watch_item` and `risk_alert` contexts render an **attachment bar** between the scrollable messages area and the chat input — not at the top of the message list. This means the attachment stays visible as messages accumulate.

All existing contexts (`fact`, `company`, `signal`, `pricing`, `report`) render at the top of the message area as before — no change to existing behavior.

### Attachment bar design
- Compact rounded border card (`rounded-xl border border-blue-200 bg-blue-50/30`)
- Shows title, details, prompt chips
- **Dismiss button** (×) — closes the attachment card and disables the context prefix for subsequent messages
- Non-dismissible for existing context types (backward compatible)

---

## How Attached Context Is Sent to Backend

**Approach used: prepend hidden context prefix to query string (alternative acceptable approach).**

Backend `ChatRequest`, `ChatState`, and `chat_graph` are **not modified**. The existing `/api/chat` endpoint remains fully backward compatible.

In `use-chat.ts`, `sendMessage` now accepts an optional `displayContent` parameter:
- `query` (string): full text sent to the API, including the hidden context prefix + user text
- `displayContent` (string, optional): what is shown in the chat UI (only the user's typed text)

In `handleSubmit` (ChatConsole), when a watch_item/risk_alert context is active and not dismissed:
1. `buildContextPrefix()` builds the labelled context block
2. `sendMessage(prefix + userText, userText)` is called
3. The backend receives the full context-enriched query → retrieves relevant facts → answers grounded in both the card context and the retrieved evidence
4. The chat UI displays only `userText` as the user message (no visible duplication of context)

---

## Streaming Compatibility

No streaming changes needed. The `sendMessage` / `useChat` hook only changes how arguments are structured internally. The API call to `sendChatMessage` is unchanged. Streaming (via `VITE_CHAT_STREAMING`) works at the API transport layer, which is untouched.

---

## Fallback Behavior

| Scenario | Behavior |
|----------|----------|
| `?context=watch_item&title=...` — title not found in report | "Attached context was not found in the latest report. You can still ask about the report." |
| `?context=risk_alert&entity=...&signal=...` — no match | Same fallback message |
| User dismisses attachment | Context prefix cleared; subsequent messages sent without prefix |
| Prompt chip clicked while attachment active | Chip text populates input; on submit, prefix is prepended to the chip text before sending |

---

## Data Correctness Confirmations

- ✅ Watch item context derived from `report.market_narrative.watch_list` (live latest report)
- ✅ Risk alert context derived from `report.contradictions` (live latest report)
- ✅ No fake card content
- ✅ No hardcoded report IDs
- ✅ No direct Supabase frontend calls
- ✅ No localStorage usage
- ✅ No backend schema / database changes
- ✅ Existing `/api/chat` endpoint backward compatible (no new required fields)
- ✅ Existing context types (fact, company, signal, pricing, report) unchanged
- ✅ Navbar `PulseLens` brand unchanged

---

## Remaining Limitations

1. **Title-based watch item lookup**: Uses `item.title` as the identifier in the URL. If two watch items have identical titles in the same report, the first match is used.
2. **Context prefix visible to LLM but not user**: The hidden prefix is part of the raw query sent to the backend. It is logged in `save_chat_message` as the full `query`. If chat history is inspected via the DB, the prefix will be visible there.
3. **No streaming-specific attachment**: Streaming mode receives the same context-enriched query. No special streaming UI changes were made.
4. **Context prefix in conversation history**: When the user sends follow-up messages, the `history` array sent to the backend contains the user's original visible text (not the prefixed version), since `onMutate` stores `displayContent`. This means subsequent turns don't re-send the prefix — correct behavior for conversation continuity.
