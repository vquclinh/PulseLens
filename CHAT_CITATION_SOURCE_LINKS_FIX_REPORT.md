# Chat Citation & Source Links Fix Report

**Date:** 2026-05-29  
**Backend syntax check:** ✅ BACKEND OK  
**Frontend build:** ✅ PASS — `tsc -b && vite build` clean, 0 errors, 6.11s

---

## Root Cause of Raw ID Display

The LLM was instructed to cite facts as `[fact_id]` (e.g. `[fact_8bad8be79ac0]`). The backend returned these raw IDs verbatim in the `response` field. The frontend's `renderWithCitations` extracted them and rendered them as `CitationChip` components showing the raw ID string. Users saw `[fcf22aae99ba]` directly in the chat prose.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/api/chat.py` | Added `_number_citations()` to replace `[fact_xxx]` → `[1]`, `[2]`, etc.; strip `[claim_xxx]`; applied before return |
| `frontend/src/modules/chat/components/chat-message.tsx` | Replaced `renderWithCitations` (raw IDs) with `renderWithNumberedCitations` (`[N]` superscripts); added "Sources used" section; removed `CitationChip` dependency |
| `frontend/src/modules/chat/pages/chat-page.tsx` | Added `citedFacts` prop pass to `ChatMessageBubble` |
| `frontend/src/modules/workspace/pages/evidence-explorer-page.tsx` | Added `isGenericSourceUrl()` helper; domain-only URLs styled differently with amber color and "Domain link" label |

---

## New Citation Display Behavior

### Backend post-processing (`_number_citations`)
After `chat_graph.ainvoke` returns `cited_fact_ids = ["fact_abc", "fact_def"]`:
1. Map built: `{ "fact_abc": "1", "fact_def": "2" }`
2. `[fact_abc]` → `[1]`, `[fact_def]` → `[2]` in response text
3. `[claim_xxx]` refs stripped entirely
4. Double spaces cleaned up
5. `cited_facts` list order preserved so index 0 → `[1]`, index 1 → `[2]`, etc.

### Frontend rendering
- `renderWithNumberedCitations` parses `[N]` (1–2 digit) and renders small blue superscript badges inline in the prose
- Below assistant messages with `citedFacts`, a "Sources used" section shows a compact card for each cited fact

### Sources used section per card
Each source card shows:
- Number badge `[N]`
- Claim (1-line clamp)
- Source domain · signal type · confidence %
- "domain-only link" warning in amber if applicable
- `ExternalLink` icon linking to `fact.source_url`

---

## Source Metadata Structure

The existing `ChatResponse.cited_facts: FactObject[]` is reused — the array order now matches citation numbers. No schema changes.

```
cited_facts[0] ↔ [1]
cited_facts[1] ↔ [2]
```

---

## Exact URL Behavior

- `fact.source_url` is used directly — never replaced with domain
- No fabricated URLs
- Homepage/domain-only URLs (path = `/`) are detected by `isGenericSourceUrl` and shown with amber styling and "domain-only link" label in both Chat sources section and Evidence Explorer

---

## Domain-Only Source Handling

`isGenericUrl(url)` / `isGenericSourceUrl(url)` — detects URLs where `pathname` is `/`, `""`, or `//`.

**Chat Sources section**: domain-only facts get `· domain-only link` label in amber text  
**Evidence Explorer**: "Source" button becomes amber "Domain link" with a tooltip explaining the limitation

Underlying `fact.source_url` is never mutated.

---

## Citation Validation Preservation

Citation validation in `graph.py` (`validate_citations` node) still operates on `[fact_xxx]` IDs internally — the LLM still cites with raw IDs during generation. The `_number_citations()` conversion happens in `chat.py` AFTER validation, so the validation logic is completely unchanged.

---

## Streaming Compatibility

No streaming endpoint exists. `_number_citations()` post-processing is in `chat.py` before the response is returned. When a streaming endpoint is added, the same function can be applied to the final response chunk.

---

## Evidence Explorer Source Link Behavior

The `Open source` button in `EvidenceCard` now:
- Exact URL: normal gray border with "Source" label
- Domain-only URL: amber border with "Domain link" label and tooltip `"Domain-only source link — may not link to the exact article"`

Both still use `fact.source_url` directly.

---

## Pipeline Source Quality Note

If many facts have domain-only source URLs, this is a **data quality issue in the scraper pipeline** — the final canonical page URL for each accepted document should be stored. This is outside the scope of this task. The frontend treatment (amber label) makes the quality signal visible to users and analysts without hiding or fabricating the actual URL.

---

## Build / Check Results

```
python -m py_compile backend/app/api/chat.py backend/app/chat/graph.py
                      backend/app/chat/agent8_analyst_chat.py
→ BACKEND OK

tsc -b && vite build  ✓  6.11s — 0 errors, 0 warnings
```

---

## Remaining Limitations

1. The `CitationChip` component (`citation-chip.tsx`) still exists in the codebase but is no longer imported. It can be removed in a future cleanup.
2. The numbered citation mapping assumes `cited_facts` order matches `cited_fact_ids` order, which is guaranteed by the current `chat.py` build loop. If that order ever changes, the mapping would misalign.
3. Domain-only detection uses only pathname length. Some URLs may have meaningful paths that still point to a homepage (e.g. `/en`). This is a conservative heuristic.
