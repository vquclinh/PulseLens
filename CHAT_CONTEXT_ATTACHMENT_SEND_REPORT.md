# Chat Context Attachment Send Report

**Date:** 2026-05-29  
**Frontend build:** ✅ PASS — `tsc -b && vite build` clean, 0 errors, 0 warnings, 5.92s  
**Backend syntax check:** ✅ PASS — `python -m py_compile` on all 5 backend files

---

## Files Changed

### Backend
| File | Change |
|------|--------|
| `backend/app/schemas/models.py` | Added `ContextAttachment` model; added `context_attachment` field to `ChatRequest` |
| `backend/app/chat/state.py` | Added `context_attachment: Optional[dict]` to `ChatState` |
| `backend/app/api/chat.py` | Serialises `request.context_attachment` into state |
| `backend/app/chat/agent8_analyst_chat.py` | Added `_build_attachment_block()`, updated `_SYSTEM` prompt, added `context_attachment` param to `answer_question` |
| `backend/app/chat/graph.py` | Passes `context_attachment` from state to both `analyst_chat` and `validate_citations` nodes |

### Frontend
| File | Change |
|------|--------|
| `frontend/src/types/index.ts` | Added `ContextAttachment` interface; updated `ChatRequest` with optional `context_attachment` and `session_id` |
| `frontend/src/hooks/use-chat.ts` | Added `AttachmentSnippet` + `MessageWithFacts` types; updated `sendMessage` to accept `attachmentSnippet` + `contextAttachment` |
| `frontend/src/modules/chat/components/chat-message.tsx` | Added `attachmentSnippet` prop; renders compact tag above user message bubble |
| `frontend/src/modules/chat/pages/chat-page.tsx` | Full rewrite: `buildContextAttachment()`, `buildAttachmentSnippet()`, `dismissAttachment()`, `handleSubmit` clears attachment after send, URL params cleared on dismiss/send |

---

## X/Remove Button Behavior

The X button appears on `watch_item` and `risk_alert` attachment cards (`isDismissible = true`).

Clicking it calls `dismissAttachment()`:
1. `setAttachmentDismissed(true)` — hides the attachment bar
2. `setSearchParams({}, { replace: true })` — clears all URL query params so the attachment does not reappear if the user copies/refreshes the URL

After dismissal: input area is clean, next message sends without any attached context.

---

## Attachment Rendered Above Input

`watch_item` and `risk_alert` contexts render inside an "attachment bar" section placed between the scrollable messages area and the chat input:
```
[scrollable messages]
[attachment bar: context card with X, details, prompt chips]  ← above input
[chat input textarea + Send button]
```

This remains visible as conversation grows. When the user sends a message, the attachment is consumed and the bar disappears.

---

## Compact Attachment in Submitted User Message

When the user sends a message with an active attachment, `buildAttachmentSnippet()` returns:
- `watch_item` → `{ label: 'Watch item', title: item.title }`
- `risk_alert` → `{ label: 'Risk alert', title: 'AMD · investor signal' }`

This snippet is stored in `MessageWithFacts.attachmentSnippet` (frontend-only, not sent to backend).

`ChatMessageBubble` renders it as a compact pill **above** the user's text bubble:
```
[Watch item · Monitor Nvidia Blackwell supply constraints]
Why does this matter?
```

The pill is: `rounded-full border border-blue-200 bg-blue-50 text-blue-700` — subtle, readable, truncates long titles.

Older messages without a snippet render exactly as before.

---

## Active Attachment Clearing After Send

In `handleSubmit`:
1. Message is sent via `sendMessage(userText, userText, snippet, contextAttachment)`
2. If an overview context was active: `dismissAttachment()` is called immediately
3. The attachment bar disappears
4. The next message has no attached context unless the user navigates back with params

---

## Frontend Request Includes `context_attachment`

`use-chat.ts` `sendChatMessage` call now includes:
```ts
context_attachment: contextAttachment,  // ContextAttachment | undefined
```

For `watch_item` the payload looks like:
```json
{
  "type": "watch_item",
  "title": "Monitor Nvidia Blackwell supply constraints",
  "urgency": "this_week",
  "rationale": "...",
  "trigger": "...",
  "summary": "Watch item: Monitor Nvidia Blackwell supply constraints (this_week)"
}
```

For `risk_alert`:
```json
{
  "type": "risk_alert",
  "entity": "AMD",
  "signal_type": "investor_signal",
  "summary": "...",
  "supporting_count": 3,
  "against_count": 2
}
```

---

## Backend Receives and Uses `context_attachment`

`ContextAttachment` is a new Pydantic model in `schemas/models.py`. The field is `Optional[ContextAttachment] = None` — fully backward compatible when absent.

`chat.py` serialises it with `model_dump(mode="json")` into `ChatState.context_attachment`.

In `agent8_analyst_chat.py`, the `_SYSTEM` prompt now includes:
```
Attached context (selected by the analyst from the PulseLens Overview):
{context_attachment_block}
```

`_build_attachment_block()` formats the dict into labelled lines:
```
Type: watch_item
Title: Monitor Nvidia Blackwell supply constraints
Urgency: this_week
Rationale: ...
Trigger: ...
```

When no attachment: `"None"` (the model ignores it).

Both `analyst_chat` and `validate_citations` graph nodes now pass `context_attachment` to `answer_question`.

---

## Streaming Compatibility

No streaming endpoint exists in this project. No streaming changes were needed.

---

## URL Clearing Behavior

| Action | URL effect |
|--------|-----------|
| User clicks X button | `setSearchParams({}, { replace: true })` — all params removed, no browser history entry |
| User sends message (attachment consumed) | `dismissAttachment()` called → same URL clear |
| Normal `/chat` without params | No change |
| Existing context types (fact, signal, etc.) | No URL clearing added — they don't have dismiss buttons |

---

## Data Correctness Confirmations

- ✅ Attachment data from `report.market_narrative.watch_list` / `report.contradictions` (live latest report)
- ✅ No fake card content
- ✅ No hardcoded report IDs
- ✅ No direct Supabase frontend calls
- ✅ Backend fully backward compatible — `context_attachment` is optional, defaults to `None`
- ✅ Existing contexts (`fact`, `company`, `signal`, `pricing`, `report`) unchanged
- ✅ Normal chat without attachment still works
- ✅ Navbar `PulseLens` unchanged

---

## Remaining Limitations

1. `context_attachment` is logged via `save_chat_message` as the full raw `query` field (which may include it if the prefix approach is still used). The structured field is separate and goes through the prompt system only — not stored in the chat DB table as a structured field.
2. After attachment is consumed (sent), the user would need to re-navigate via the Overview to re-attach the same card.
3. Prompt chips send only the chip text with the attachment — the attachment is included in the backend call but not shown as a separate visual prefix in the chip interaction.
