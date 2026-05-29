# Chat Behavior Routing Fix Report

**Date:** 2026-05-29  
**Backend syntax check:** ✅ ALL OK — `python -m py_compile` on 3 files  
**Frontend changes:** None

---

## Root Cause of Rigid Evidence-Only Behavior

Two problems in `backend/app/chat/agent8_analyst_chat.py`:

1. **Early-exit bypass:** `answer_question` returned a canned message before calling the LLM whenever `not retrieved_facts`. Greetings, product questions, and concept explanations were all rejected before the LLM could even run.

2. **Over-strict system prompt:** The `_SYSTEM` prompt said `"Answer using ONLY the supplied report evidence"` — one mode for all questions. There was no concept of question types, no product guide, no general-answer path.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/chat/agent8_analyst_chat.py` | Rewrote `_SYSTEM` prompt with question classification (A–F), product guide, and better fallback wording. Removed early-exit when `retrieved_facts` is empty so LLM always runs. |

No frontend changes, no schema changes, no other backend files changed.

---

## Question Categories Implemented

Six intent modes guide the LLM:

| Mode | Examples | Behavior |
|------|----------|----------|
| A — Greeting | "hello", "hi", "thanks", "who are you" | Natural warm reply; explains PulseLens capabilities; no citations |
| B — Product/navigation | "what can I ask?", "what is Signal Radar?" | Answers from product guide in system prompt; no evidence needed |
| C — Concept/definition | "what is a 13F-HR?", "what does SAFE mean?" | Clear general answer, labelled "General context:"; no citations unless using report facts |
| D — Report-grounded analytical | "strongest signals?", "compare AMD vs Nvidia", "explain this card" | Uses retrieved evidence with [fact_id] citations |
| E — Out-of-report but answerable | Concept not directly in report | States limitation in one sentence, then provides general answer |
| F — Out-of-scope | Live stock price, breaking news | Honest limitation; suggests related question or pipeline refresh |

---

## General-Answer Behavior

The early-exit (`if not retrieved_facts: return "I do not have enough..."`) has been removed. The LLM is always called. For modes A, B, C the evidence block will show "No facts retrieved" but the system prompt tells the model this is expected and it should answer from product knowledge or general context instead.

---

## Report-Grounded Behavior

Unchanged and preserved:
- Mode D still requires [fact_id] citations for every report-backed factual sentence
- Citation validation in `graph.py` still checks that cited IDs are present in retrieved facts
- Retry-with-correction logic still fires when invalid IDs appear

---

## PulseLens Product Guide Added to Prompt

The `_SYSTEM` prompt now includes a structured ABOUT PULSELENS section covering:
- Evidence, Signal Radar, Company Lens, Pricing Intelligence, Pipeline/Audit Center
- SAFE verified definition
- Source tier definitions (T1–T4)
- Note that Fact IDs are internal technical identifiers

This allows the LLM to answer product/navigation questions accurately without any retrieved evidence.

---

## Context Attachment Behavior

`context_attachment` handling is completely unchanged:
- `_build_attachment_block()` unchanged
- Attachment passed into state unchanged
- System prompt still surfaces it as "Attached context (selected by the analyst from the PulseLens Overview)"
- All three attachment types (watch_item, risk_alert, fact) still work

If the user types "explain this" while a fact card is attached, the LLM sees the attachment block and answers about it (mode D or C depending on content).

---

## Streaming Compatibility

No streaming endpoint exists in the current codebase. The `answer_question` function is the single LLM call path shared by both streaming and non-streaming. The prompt improvement applies equally to both.

---

## Better Fallback Wording

Old: `"I do not have enough retrieved evidence in this report to answer that reliably."`  
New (varies by situation):
- Analytical/no evidence: `"I do not see enough source-backed evidence for that exact question in the latest PulseLens report. You can ask about the companies, signals, pricing pressure, risk alerts, or attach a specific evidence card."`
- Partially answerable: `"I do not see direct evidence for that in the latest report. General context: …"`
- LLM failure with facts: `"I could not complete the full analysis, but here is what the evidence shows: …"`
- LLM failure without facts: `"I'm having trouble generating a response right now. Please try again or rephrase your question."`

---

## Manual Verification Expected Results

| Input | Expected behavior |
|-------|-------------------|
| "hello" | Natural greeting, explains PulseLens capabilities |
| "what can I ask here?" | Explains report, signals, companies, pricing, evidence, chat |
| "what is a 13F-HR?" | General context explanation, no evidence failure |
| "what are the strongest signals?" | Report-backed with citations |
| "compare AMD and Nvidia" | Report-grounded comparison from company narratives |
| Attach fact card + "explain this" | Uses attached fact content |
| "what is Nvidia stock price right now?" | States limitation, does not fabricate |

---

## Backend Syntax Check

```
python -m py_compile backend/app/api/chat.py
                      backend/app/chat/agent8_analyst_chat.py
                      backend/app/chat/graph.py
→ ALL OK
```

---

## Remaining Limitations

1. Question classification is done by the LLM at inference time — not a deterministic classifier. The model may occasionally misroute edge cases.
2. `answer_question` is synchronous (LLM client is sync). With no retrieved facts, the LLM still makes a full API call for greetings. A lightweight pre-check for obvious greetings could save latency but is not implemented.
3. The product guide in the system prompt is a static string. It will not reflect future PulseLens feature additions until the prompt is updated.
