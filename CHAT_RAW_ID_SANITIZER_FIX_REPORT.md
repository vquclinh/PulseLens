# Chat Raw ID Sanitizer Fix Report

**Date:** 2026-05-29  
**Backend syntax check:** ✅ BACKEND OK  
**Frontend build:** ✅ PASS — `tsc -b && vite build` clean, 0 errors, 5.86s

---

## Root Cause of Raw ID Leakage

The previous `_number_citations()` function only handled single `[fact_xxx]` patterns via a simple regex. Four additional leakage patterns were not covered:

1. **Comma-separated multi-fact brackets** — LLM sometimes cites `[fact_abc, fact_def]` in a single bracket. The old regex only matched single-ID brackets and left these untouched.
2. **Report ID refs** — LLM sometimes wrote `[report_264d6be13e24]` when citing the report source. No regex covered this.
3. **Bare hex hashes** — Fact IDs in the Evidence block are displayed as `[fcf22aae99ba]` (short hex without the `fact_` prefix). These appeared as bare hex strings in citations.
4. **Prompt didn't forbid multi-ID brackets or report refs** — The system prompt only said to cite as `[fact_id]` without explicitly forbidding `[fact_abc, fact_def]` or `[report_xxx]`.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/api/chat.py` | Rewrote `_number_citations` → `_sanitize_response` with 5-step comprehensive pattern coverage |
| `backend/app/chat/agent8_analyst_chat.py` | CITATION RULES updated to forbid multi-ID brackets, report refs, and plain-text fact IDs |
| `frontend/src/modules/chat/components/chat-message.tsx` | Added `sanitizeDisplayText()` safety net; applied before `renderWithNumberedCitations` |

---

## Backend Sanitizer Behavior (`_sanitize_response`)

Five steps in order:

| Step | Pattern | Action |
|------|---------|--------|
| 1 | `[fact_abc, fact_def, ...]` | Expand to `[N][M]` — each ID mapped to its citation number |
| 2 | `[fact_xxx]` | Map to `[N]` or remove if not in cited list |
| 3 | `[claim_xxx, ...]` | Remove entirely |
| 4 | `[report_xxx]` | Remove entirely |
| 5 | `[fcf22aae99ba]` (bare hex ≥8 chars) | Remove (negative lookahead preserves markdown `[text](url)`) |

Then: collapse double spaces, fix space-before-punctuation artifacts, strip.

---

## Frontend Safety Sanitizer Behavior (`sanitizeDisplayText`)

Applied in `renderWithNumberedCitations` before any rendering. Mirrors all 5 backend patterns as a last line of defence. Display-only — never mutates the `message` object or `citedFacts` metadata.

Patterns removed by frontend:
- `[fact_xxx]` (single and multi)
- `[claim_xxx]`
- `[report_xxx]`
- `[bare_hex ≥ 8 chars]` not followed by `(`

---

## Patterns Removed

```
[fact_a8c08784debf, fact_76a3efce7d7b]  → [1][2]  (or removed if not in cited list)
[fact_a8c08784debf]                     → [1]
[claim_ed0785494287]                    → (removed)
[report_264d6be13e24]                   → (removed)
[fcf22aae99ba]                          → (removed)
```

---

## Numbered Citations Preserved

`[1]`, `[2]`, `[3]` patterns are not matched by any sanitizer rule. Markdown links `[text](url)` are also preserved (negative lookahead `(?!\()`).

---

## Report IDs Hidden from Prose

`[report_xxx]` refs are stripped entirely. The system prompt now explicitly says: "refer to the report as 'this report', 'the latest report', or 'the current PulseLens report' — never by internal ID."

---

## Prompt Updates (agent8_analyst_chat.py)

Added to CITATION RULES:
- Cite each fact separately: `[fact_abc][fact_def]` — never `[fact_abc, fact_def]`
- Never include `[claim_xxx]` or `[report_xxx]` in the visible answer
- Never show raw report ID — refer as "this report" or "the latest report"
- Never paste raw `fact_id` values as plain text

---

## Streaming Compatibility

No streaming endpoint exists. `_sanitize_response` runs in `chat.py` before the `ChatResponse` is returned. When a streaming endpoint is added, the same function must be applied to the final response delta.

---

## Build / Check Results

```
python -m py_compile backend/app/api/chat.py
                      backend/app/chat/agent8_analyst_chat.py
                      backend/app/chat/graph.py
→ BACKEND OK

tsc -b && vite build  ✓  5.86s — 0 errors, 0 warnings
```

---

## Remaining Limitations

1. The bare-hex removal pattern (`[a-f0-9]{8,}`) could theoretically strip a legitimate markdown link with an all-hex anchor text (e.g. `[deadbeef00ff](url)`). The negative lookahead `(?!\()` prevents removing markdown links, so this is safe.
2. If the LLM embeds a raw `fact_id` as plain text without brackets (e.g. `fact_a8c08784debf` without `[...]`), neither sanitizer catches it. The prompt now explicitly forbids this. If it still appears, a word-boundary regex for `fact_[a-f0-9]{12}` could be added.
3. The `_sanitize_response` function is only called in `chat.py` for the non-streaming path. Any future streaming implementation must apply the same sanitizer before emitting the final text delta.
