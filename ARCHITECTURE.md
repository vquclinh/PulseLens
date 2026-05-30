# PulseLens — System Architecture

> **Version:** 2.0 (updated to reflect Sprint 8 codebase)  
> **Purpose:** Architecture reference with full research paper methodology mapping  
> **Principle:** Every non-trivial component is grounded in a peer-reviewed method
> from a top-tier venue (EMNLP, ACL, NeurIPS, Google DeepMind, Stanford).
> Hand-rolled heuristics only where no better method exists.

---

## Why research methods matter here

A system that scrapes the web and asks an LLM to summarize it is not hard to build.
The hard problem is **trustworthiness** — making every claim traceable,
every score explainable, every output verifiable by the user.

Each paper applied here solves a specific failure mode:

| Failure mode | Paper that solves it |
|---|---|
| Queries miss 80% of signals | Multi-HyDE — non-equivalent query fan-out |
| LLM summarizes instead of extracting | RASG — schema-constrained extraction as tool use |
| LLM invents quotes not in source | SAFE — atomic claim verification against evidence |
| Single-source claims distort scores | ClaimCheck — cross-source corroboration |
| Claims partially supported pass through | MiniCheck — lightweight per-fact validation |
| All claims weighted equally | FActScore — atomic precision scoring |
| Narrative blends everything into vague prose | STORM — multi-perspective synthesis |
| Chat answers confidently from irrelevant context | Self-RAG — self-reflective retrieval |
| Multi-hop answers drift from evidence mid-generation | FLARE — sentence-level active retrieval |
| Financial sentiment misread by general LLM | FinBERT — domain-specific financial model |

---

## Table of Contents

1. [System overview](#1-system-overview)
2. [Pipeline graph — full DAG](#2-pipeline-graph--full-dag)
3. [Agent 1 — Query Planner](#3-agent-1--query-planner)
4. [Agent 2 — Web Collection Workers](#4-agent-2--web-collection-workers)
5. [Agent 3 — Fact Extractors](#5-agent-3--fact-extractors)
6. [Node — SAFE Atomic Verification](#6-node--safe-atomic-verification)
7. [Agent 4 — FinBERT Scorer](#7-agent-4--finbert-scorer)
8. [Node — Quality Gate](#8-node--quality-gate)
9. [Node — M4 Triangulator](#9-node--m4-triangulator)
10. [Node — Contradiction Writer](#10-node--contradiction-writer)
11. [Node — M5 Signal Scorer](#11-node--m5-signal-scorer)
12. [Node — Company Narratives](#12-node--company-narratives)
13. [Agent 6 — Narrative Synthesizer](#13-agent-6--narrative-synthesizer)
14. [Agent 7 — Watch List Builder](#14-agent-7--watch-list-builder)
15. [Node — Report Assembler](#15-node--report-assembler)
16. [Pricing Nodes — Pre-extractor and Playbook](#16-pricing-nodes--pre-extractor-and-playbook)
17. [Database Adapter Layer](#17-database-adapter-layer)
18. [Chat Graph — Analyst Chat](#18-chat-graph--analyst-chat)
19. [Data flow diagram](#19-data-flow-diagram)
20. [Paper reference index](#20-paper-reference-index)

---

## 1. System overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  FRONTEND  TypeScript + Vite 6 + React 18 + TailwindCSS 4          │
│  /            Home page                                             │
│  /workspace   Intelligence Workspace (6 URL-driven views):         │
│               Overview · Evidence · Pricing · Signals ·            │
│               Companies · Pipeline                                  │
│  /chat        Standalone analyst chat page                         │
└────────────────────────┬────────────────────────────────────────────┘
                         │ REST (no SSE streaming in current release)
┌────────────────────────▼────────────────────────────────────────────┐
│  API LAYER  FastAPI + Uvicorn  (port 8000)                         │
│  POST /api/run  ·  GET /api/report/{id}  ·  GET /api/report/{id}/facts │
│  POST /api/chat  ·  GET /api/reports/latest  ·  GET /api/stock/{ticker} │
└────────────────────────┬────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│  PIPELINE GRAPH  LangGraph StateGraph  (ainvoke, MemorySaver)       │
│  14 sequential nodes with 1 conditional quality-gate loop           │
│  Agent 2 batches internally (no Send API fan-out in current release)│
└────────────────────────┬────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│  CHAT GRAPH  Separate LangGraph StateGraph  (ainvoke, per-session)  │
│  4 nodes: retrieve_facts → build_prompt → analyst_chat →            │
│           validate_citations  (one built-in retry inside last node)  │
│  Synchronous request/response — no token streaming.                 │
└────────────────────────┬────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│  DATABASE ADAPTER  (selected by DATABASE_BACKEND env var)           │
│  SQLite    aiosqlite  →  backend/data/pulselens.db  (default)       │
│  Postgres  asyncpg   →  Supabase or any Postgres instance           │
│                                                                     │
│  EXTERNAL SERVICES                                                  │
│  Bright Data (SERP API · Web Unlocker · Browser API)               │
│  OpenRouter API  ·  HuggingFace  ·  Alpha Vantage                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Why LangGraph — not plain Python, not LangChain

LangChain is built for linear chains (A → B → C).
PulseLens is a DAG with conditional cycles and checkpointing.
LangChain handles this poorly. LangGraph handles it natively.

| Requirement | LangGraph capability |
|---|---|
| Resume after failure without restarting | Built-in checkpointing (MemorySaver in current release; SqliteSaver planned) |
| Re-query when signal coverage is low | Conditional edges with cycle support |
| Persistent chat conversation history | StateGraph with thread-level state |
| Typed state shared across all nodes | `TypedDict` — enforced at every node boundary |

> **Note on fan-out:** Agent 2 batches URL fetches internally using `asyncio.gather`
> rather than LangGraph `Send` API fan-out. The same applies to Agent 3 fact extraction.
> True Send-based fan-out is architecturally planned but not yet wired in the graph edges.

**Critical:** LangGraph does not require LangChain abstractions.
Every LLM call in PulseLens uses the **OpenRouter API via `LLMClient`**.
LangGraph is only the graph wiring — not the LLM interface.

---

## 2. Pipeline graph — full DAG

```
START
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│  Agent 1 — Query Planner              [LLM: OpenRouter]  │
│  Step-Back Prompting + Multi-HyDE                        │
│  arXiv:2310.06117 + arXiv:2509.16369                     │
│  Also injects 15 deterministic pricing playbook queries  │
└──────────────────────────┬───────────────────────────────┘
                           │ 22–50 SearchQuery[]
                           │ (includes pricing playbook queries)
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Agent 2 — Web Workers             [Non-LLM: Bright Data]│
│  Batches internally via asyncio.gather (10 concurrent)   │
│  SERP API · Web Unlocker · Browser API                   │
│  Output: RawDocument[] (~100–200 docs)                   │
└──────────────────────────┬───────────────────────────────┘
                           │ RawDocument[]
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Agent 3 — Fact Extractor             [LLM: OpenRouter]  │
│  RASG schema extraction   arXiv:2405.20245               │
│  Batches internally; also runs pricing_pre_extractor     │
│  (regex extractor for full pricing documents)            │
│  Output: FactObject[] (raw, ~500)                        │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Node — validate_fact                     [Pure Python]  │
│  evidence_quote must exist verbatim in source.content    │
│  Discard: hallucinated quote / confidence < 0.6          │
│  → ~200 validated FactObject[]                           │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Node — validate_and_split (SAFE)    [LLM: OpenRouter]   │
│  SAFE: Search-Augmented Factuality Evaluator             │
│  arXiv:2403.18802  (Google DeepMind, 2024)               │
│  Decompose claim → atomic sub-claims                     │
│  Verify each atomic claim against evidence_quote         │
│  Discard fact if < 50% atomic claims supported           │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Agent 4 — FinBERT Scorer        [HuggingFace, no LLM]   │
│  FinBERT: ProsusAI/finbert                               │
│  Batch sentiment scoring on every fact.claim             │
│  Output: sentiment label + score (-1.0 to 1.0)           │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Node — Quality Gate                      [Pure Python]  │
│  Conditional edge: pass → triangulator                   │
│              fail → loop back to Agent 1 (max 2×)        │
│  Fail if: facts < 50 OR source_count < 15               │
│           OR signal coverage < 4 types                   │
└──────────────┬─────────────────────────┬─────────────────┘
          expand_queries             proceed
               │                         │
               ▼                         ▼
         Agent 1 again       ┌───────────────────────────────────────┐
         (round 2 max)       │  Node — M4 Triangulator  [Pure Python]│
                             │  ClaimCheck  ACL 2025                 │
                             │  MiniCheck   arXiv:2404.10774         │
                             │  FActScore   arXiv:2305.14251         │
                             │  Also calls write_contradiction_notes │
                             │  (async, bounded semaphore, ≤5 conc.) │
                             │  → VerifiedClaim[] + ContradictionFlag│
                             └──────────────────┬────────────────────┘
                                                │
                                                ▼
                             ┌───────────────────────────────────────┐
                             │  Node — M5 Signal Scorer  [Pure Python│
                             │  Weighted formula:                    │
                             │    tier × recency × factscore ×       │
                             │    corroboration                      │
                             │    × 0.5 if contradicted              │
                             │  Pulse score 0–100                    │
                             │  Per-company breakdown for narratives │
                             └──────────────────┬────────────────────┘
                                                │
                                                ▼
                             ┌───────────────────────────────────────┐
                             │  Node — Company Narratives            │
                             │                   [LLM: OpenRouter]   │
                             │  Per-company analyst card builder     │
                             │  asyncio.gather (all companies conc.) │
                             │  → CompanyNarrative[] with:           │
                             │    narrative, key_events, key_drivers │
                             │    competitive_position, momentum     │
                             └──────────────────┬────────────────────┘
                                                │
                                                ▼
                             ┌───────────────────────────────────────┐
                             │  Agent 6 — Narrative Synthesizer      │
                             │                   [LLM: OpenRouter]   │
                             │  STORM multi-perspective synthesis    │
                             │  arXiv:2402.14207  (Stanford, 2024)   │
                             │  → MarketNarrative                    │
                             └──────────────────┬────────────────────┘
                                                │
                                                ▼
                             ┌───────────────────────────────────────┐
                             │  Agent 7 — Watch List Builder         │
                             │                   [LLM: OpenRouter]   │
                             │  Forward indicators from developing   │
                             │  signals → WatchItem[]                │
                             └──────────────────┬────────────────────┘
                                                │
                                                ▼
                             ┌───────────────────────────────────────┐
                             │  Node — Report Assembler  [Pure Python│
                             │  Assembles MarketPulseReport          │
                             │  Saves via db_adapter.save_report()   │
                             │  PARTIAL_PASS: caps confidence 0.5,  │
                             │  prepends warning to narrative_body   │
                             └──────────────────┬────────────────────┘
                                                │
                                               END
```

---

## 3. Agent 1 — Query Planner

**File:** `app/pipeline/agent1_query_planner.py`  
**Type:** LLM — OpenRouter via `LLMClient` (`google/gemini-2.5-flash` default)  
**LangGraph node:** `query_planner`

### Research methods applied

#### [PAPER 1] Step-Back Prompting
```
Authors:  Zheng et al.
Venue:    Google DeepMind, 2023
Citation: arXiv:2310.06117
```

**What it does:**
Before generating queries, the LLM takes a "step back" to identify the
correct level of abstraction. Instead of immediately searching for
"Nvidia hiring surge", the model first asks: *"What would the evidence
look like if AI infrastructure demand is accelerating?"* — then generates
queries from that higher-level frame.

**Why it matters here:**
Direct query generation from company names produces surface-level queries.
Step-Back identifies the underlying signal patterns first, then generates
queries that would surface evidence for or against each pattern.
This prevents the common failure of fetching articles that mention the
company but contain no useful signal.

**Applied at:**
First reasoning step in the Query Planner prompt — before Multi-HyDE
query generation begins.

---

#### [PAPER 2] Multi-HyDE-inspired query fan-out (adapted from arXiv:2509.16369)
```
Authors:  Srinivasan et al., IIT Madras
Venue:    EMNLP 2025
Citation: arXiv:2509.16369
Results:  +11.2% accuracy, -15% hallucination on financial QA benchmarks
```

**What the paper does (full algorithm):**
Multi-HyDE generates N non-equivalent hypothetical queries, synthesizes a
hypothetical document for each, embeds those documents, retrieves real
documents by vector similarity, concatenates results, and reranks with
a cross-encoder.

**What PulseLens implements (adapted):**
Step 1 only — diverse, non-equivalent query generation per signal dimension.
Steps 2–5 (hypothetical document synthesis, embedding, vector retrieval,
reranking) are not implemented because PulseLens uses Bright Data web
collection, not a vector store. The core insight — generate queries that
would each retrieve *different* hypothetical documents — still applies and
improves signal coverage vs. single-query generation.

**Why it matters here:**
A single query "Nvidia AI hardware news" returns generic articles.
The adapted fan-out generates: "Nvidia AI infrastructure job postings Q2 2025",
"Nvidia data center engineering headcount expansion", "Nvidia GPU compute
workforce site:linkedin.com" — each targeting a different facet of the
same signal, collectively recovering evidence that no single query finds.

**Applied at:**
Main query generation loop in `agent1_query_planner.py`. Every
`(company, signal_type, source_type)` triple spawns 2–3 non-equivalent queries.

Agent 1 also merges in the 15 deterministic queries from
`pricing_pressure_playbook.py` for pricing signal coverage
(see [Section 16](#16-pricing-nodes--pre-extractor-and-playbook)).

---

### Prompt design

```python
SYSTEM_PROMPT = """
You are a financial intelligence research planner.

STEP 1 — STEP BACK (arXiv:2310.06117):
Before writing any queries, identify the abstract signals that would
confirm or deny whether this market is accelerating.
Ask yourself: what would the evidence look like if the hypothesis were true?

STEP 2 — MULTI-HYDE DECOMPOSITION (arXiv:2509.16369):
Generate {target_count} search queries across 3 dimensions:
  - company dimension:      1 query per company
  - signal type dimension:  2–3 queries per signal type
  - source type dimension:  news SERP / job pages / IR pages / pricing pages

Rules:
  - Non-redundant: no two queries should retrieve the same documents
  - Prioritize Tier 1 (SEC, IR pages) and Tier 2 (Reuters, Bloomberg)
  - Each query targets exactly ONE (company × signal_type × source_type)
  - On expansion round 2: focus on low-coverage signal types: {low_signal_types}

Return ONLY valid JSON: List[SearchQuery]. No prose.
"""
```

### Quality constraints

```python
MIN_QUERIES          = 40
MIN_SIGNAL_TYPES     = 7      # must cover all 7 signal types
MAX_EXPANSION_ROUNDS = 2      # hard stop to prevent infinite loops
```

---

## 4. Agent 2 — Web Collection Workers

**File:** `app/pipeline/agent2_web_workers.py`  
**Type:** Non-LLM — async Python + Bright Data API  
**LangGraph node:** `web_worker`  
**Research methods applied:** None — pure engineering

### Source tiering (assigned at collection time, never retroactively)

```python
TIER_1_DOMAINS = {                      # weight: 1.0
    "sec.gov", "ir.nvidia.com", "ir.amd.com", "investor.intel.com",
    "investors.broadcom.com", "ir.supermicro.com", "ir.dell.com",
    "investor.hpe.com", "investor.micron.com"
}
TIER_2_DOMAINS = {                      # weight: 0.8
    "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
    "apnews.com", "businesswire.com", "prnewswire.com"
}
TIER_3_DOMAINS = {                      # weight: 0.5
    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
    "semianalysis.com", "tomshardware.com", "anandtech.com"
}
# Tier 4 = default for job boards, pricing pages, company blogs  # weight: 0.4
```

### Bright Data product mapping

```python
TOOL_MAPPING = {
    "serp_news":     "SERP API",       # news and general web search
    "job_pages":     "Web Unlocker",   # LinkedIn, Glassdoor, Indeed
    "ir_pages":      "Web Unlocker",   # SEC EDGAR, investor relations pages
    "pricing_pages": "Browser API",   # JavaScript-rendered pricing pages
    "dynamic_pages": "Browser API",   # other JS-heavy sites
    "protected":     "Web Unlocker",  # anti-bot protected sites
}
# Zone configuration via: BRIGHTDATA_SERP_ZONE, BRIGHTDATA_UNLOCKER_ZONE,
#                         BRIGHTDATA_BROWSER_ZONE
```

### Parallelism and resilience

```python
MAX_CONCURRENT_BATCHES = 10
QUERIES_PER_BATCH      = 5
RETRY_DELAYS           = [1, 2, 4]    # exponential backoff in seconds
TIMEOUT_PER_REQUEST    = 15           # seconds
CACHE_KEY              = lambda url, date: f"{url}:{date}"
```

Retry strategy: 3× with exponential backoff. On final failure: log error,
skip document, continue pipeline. A failed URL never blocks the run.

Cache: keyed by `(url, date)` via diskcache. The same URL is never
fetched twice in a single pipeline run.

---

## 5. Agent 3 — Fact Extractors

**File:** `app/pipeline/agent3_fact_extractors.py`  
**Type:** LLM — OpenRouter via `LLMClient`  
**LangGraph node:** `fact_extractor`  
**Research methods applied:** RASG-inspired schema extraction

This node also invokes `pricing_pre_extractor.extract_pricing_facts_from_document()`
on every document before the LLM step, to capture price/rate data from full
document content that would otherwise be truncated (see
[Section 16](#16-pricing-nodes--pre-extractor-and-playbook)).

### [PAPER 3] RASG — Retrieval Augmented Structured Generation
```
Authors:  Cesista et al.
Venue:    2024
Citation: arXiv:2405.20245
```

**What it does:**
Frames information extraction as a **tool-use task**, not a text generation
task. The LLM is given a strict JSON schema as a "tool definition" and must
fill the schema fields. It cannot generate text outside the schema.
This eliminates the primary failure mode of free-form extraction:
vague, unauditable, inconsistently structured summaries that are hard
to validate downstream.

**What PulseLens implements (RASG-inspired):**
Prompt-enforced JSON schema extraction — the system prompt instructs the LLM
to return only schema-valid JSON matching the FactObject fields. This is not
true function/tool calling (which enforces schema at the API level and
prevents non-JSON output entirely). It applies RASG's schema-constraint
insight via prompt engineering. The output format is structurally equivalent;
the enforcement mechanism is softer.

**Why it matters here:**
Without RASG-inspired extraction: LLM writes "Nvidia seems to be expanding
its AI workforce significantly" — no quote, no date, no confidence, no entity
structure. With RASG-inspired extraction: LLM fills
`{entity: "Nvidia", signal_type: "hiring_momentum",
claim: "Nvidia opened 23 AI infra roles this week",
evidence_quote: "Nvidia has opened more than 20 positions...",
confidence: 0.91}` — fully structured, auditable, downstream-ready.

**Applied at:**
Extraction system prompt and output schema definition in `agent3_fact_extractors.py`.

---

### Extraction prompt

```python
SYSTEM_PROMPT = """
You are a financial market intelligence extraction system.

Method: RASG-inspired schema extraction (arXiv:2405.20245)
Extract ONLY facts EXPLICITLY STATED in the provided text.
Do NOT infer, interpret, or add information not in the text.
Return ONLY a valid JSON array. If no relevant facts, return [].

Schema for each fact object:
{
  "entity":         "Company name or 'market'",
  "signal_type":    "one of: hiring_momentum | product_launch | pricing_pressure
                     | strategic_messaging | investor_signal
                     | news_sentiment | supplier_risk",
  "claim":          "1 factual sentence, max 150 chars, no interpretation",
  "evidence_quote": "exact verbatim quote from the text, max 200 chars",
  "published_date": "ISO 8601 or null",
  "confidence":     0.0–1.0
}

Context:
  query:           {query}
  expected_signal: {signal_type}

Text:
{document_content}
"""
```

### Post-LLM validation (pure Python — most critical correctness gate)

```python
def validate_fact(fact: FactObject, source: RawDocument) -> bool:
    """
    CRITICAL: evidence_quote must appear VERBATIM in source.content.
    If it doesn't, the LLM invented the quote — discard the entire fact.
    This is the single most important anti-hallucination gate in the system.
    """
    if fact.evidence_quote not in source.content:
        return False    # hallucinated quote
    if len(fact.claim) > 150:
        return False
    if fact.confidence < 0.6:
        return False
    if fact.entity not in KNOWN_ENTITIES:
        return False
    return True
```

Any fact failing this validation is silently discarded before it enters
the rest of the pipeline. No downstream component ever sees a hallucinated fact.

---

## 6. Node — SAFE Atomic Verification

**File:** `app/pipeline/node_validate_and_split.py`  
**Type:** LLM call via `LLMClient` + pure Python logic  
**LangGraph node:** `validate_and_split`

### [PAPER 4] SAFE — Search-Augmented Factuality Evaluator
```
Authors:  Wei et al., Google DeepMind
Venue:    2024
Citation: arXiv:2403.18802
```

**What it does:**
After extracting each fact, SAFE decomposes the `claim` into atomic,
independently verifiable sub-claims. It then checks whether each atomic
claim is actually supported by the `evidence_quote`.
Facts where fewer than 50% of atomic claims are supported are discarded.

This catches a failure mode that the evidence_quote presence check cannot:
the quote is real, but the LLM's `claim` goes further than what the quote
actually says. Example:

- Evidence quote: *"Nvidia opened 20+ AI infra positions"*
- Claim: *"Nvidia is aggressively expanding its AI infrastructure team and expects to double headcount"* ← the "double headcount" part is not in the quote

SAFE catches this by splitting the claim into atomics:
1. "Nvidia opened 20+ AI infra positions" ✓ supported
2. "Nvidia expects to double headcount" ✗ not supported → downgrade

**Why it matters here:**
This is the strongest anti-hallucination mechanism in the system.
Evidence quote presence only checks that the quote exists.
SAFE checks that the claim accurately represents what the quote says.

**Applied at:**
Between `validate_fact` and FinBERT scoring. Every validated FactObject
goes through SAFE before its sentiment is scored.

---

### Implementation

```python
def atomic_split_and_verify(fact: FactObject, llm) -> Optional[FactObject]:
    # Step 1: decompose claim into atomic sub-claims
    atomic_prompt = f"""
    Decompose this claim into atomic, independently verifiable facts.
    Each atomic fact must be a single assertion that cannot be split further.
    Return a JSON array of strings only.

    Claim: "{fact.claim}"
    """
    atomic_claims: List[str] = llm.call(atomic_prompt, output_type="json")

    # Step 2: verify each atomic claim against evidence_quote
    supported = []
    for atomic in atomic_claims:
        support_prompt = f"""
        Is this atomic claim directly supported by the evidence quote?
        Answer ONLY "yes" or "no".

        Atomic claim:   "{atomic}"
        Evidence quote: "{fact.evidence_quote}"
        """
        answer = llm.call(support_prompt).strip().lower()
        if answer == "yes":
            supported.append(atomic)

    # Step 3: discard fact if support ratio < 50%
    support_ratio = len(supported) / max(len(atomic_claims), 1)
    if support_ratio < 0.5:
        return None     # discard

    fact.atomic_claims  = supported
    fact.safe_verified  = True
    return fact
```

---

## 7. Agent 4 — FinBERT Scorer

**File:** `app/pipeline/agent4_finbert_scorer.py`  
**Type:** Non-LLM — HuggingFace inference  
**LangGraph node:** `finbert_scorer`

### [PAPER 5] FinBERT
```
Authors:  Yang et al.
Venue:    2020
Source:   HuggingFace — ProsusAI/finbert
```

**What it does:**
BERT model fine-tuned on financial corpora: earnings call transcripts,
analyst reports, financial news articles. Outputs sentiment classification
(positive / negative / neutral) + confidence score per claim.

**Why not use a general LLM for sentiment:**
- FinBERT is faster: <1ms per claim on CPU vs ~500ms per LLM call
- FinBERT is free: no API cost
- FinBERT is more accurate on financial jargon: understands domain-specific
  phrases like "guidance raised", "margin compression", "channel inventory
  digestion" that general LLMs sometimes misclassify
- Deterministic: same claim always produces the same score

**Applied at:**
Runs on every FactObject after SAFE verification.
Scores are used in M4 triangulation weighted sentiment and M5 pulse scoring.

---

### Implementation

```python
from transformers import pipeline

finbert = pipeline(
    "sentiment-analysis",
    model="ProsusAI/finbert",
    tokenizer="ProsusAI/finbert",
    device="cpu",           # set to "cuda" if GPU available
)

def score_batch(facts: List[FactObject], batch_size: int = 32) -> List[FactObject]:
    claims  = [f.claim for f in facts]
    results = finbert(claims, batch_size=batch_size, truncation=True)

    for fact, result in zip(facts, results):
        label = result["label"]     # "positive" | "negative" | "neutral"
        score = result["score"]     # 0.0–1.0 confidence from FinBERT

        fact.sentiment = label
        fact.sentiment_score = (
             score if label == "positive" else
            -score if label == "negative" else
             0.0
        )
    return facts
```

---

## 8. Node — Quality Gate

**File:** `app/pipeline/node_quality_gate.py`  
**Type:** Pure Python — conditional edge  
**LangGraph node:** `quality_gate`  
**Research methods applied:** None

```python
def quality_gate(state: PipelineState) -> Literal["expand_queries", "proceed"]:
    facts           = state["scored_facts"]
    covered_signals = {f.signal_type for f in facts}
    rounds          = state["query_expansion_rounds"]

    if rounds >= 2:
        # Hard stop — prevent infinite loop
        return "proceed"

    if len(facts) < 50 or len(covered_signals) < 4:
        # Signal coverage insufficient — identify gaps and loop back
        state["low_signal_types"] = [
            st for st in SignalType if st not in covered_signals
        ]
        state["query_expansion_rounds"] += 1
        return "expand_queries"

    return "proceed"
```

On `expand_queries`: routes back to Agent 1 with `low_signal_types`
injected into state. Agent 1 generates 5–10 gap-filling queries targeting
only the underrepresented signal types.

---

## 9. Node — M4 Triangulator

**File:** `app/pipeline/node_triangulator.py`  
**Type:** Pure Python + async contradiction writing  
**LangGraph node:** `triangulator`

### [PAPER 6] ClaimCheck
```
Authors:  Putta et al.
Venue:    ACL / KnowledgeNLP Workshop 2025
Results:  62.6% verdict prediction accuracy on AVeriTeC benchmark
```

**What it does:**
Two-strategy corroboration pipeline:
1. Claim-matching: checks if the claim is corroborated by established
   fact-check sources with known verdicts
2. Novel claim processing: generates verification questions → retrieves
   web evidence → assigns a verdict

**Applied here (adapted):**
The corroboration logic: a claim is only raised as a VerifiedClaim if
it is supported by ≥2 independent source domains.
A Tier 1 source (SEC, IR page) alone is sufficient to override
the corroboration requirement — these are authoritative by definition.

---

### [PAPER 7] MiniCheck
```
Authors:  Tang et al.
Venue:    2024
Citation: arXiv:2404.10774
Results:  F1 equivalent to GPT-4, 400× faster
```

**What it does:**
Lightweight fact-checking model. For each FactObject, checks whether the
extracted claim is actually supported by the source document it came from.
Catches cases where: the evidence_quote is present in the document, but
the LLM's claim misrepresents or overstates what the quote says.

**Applied here:**
Pre-triangulation validation step. Every FactObject is run through
MiniCheck before being grouped for corroboration analysis.
Facts not supported by their source are discarded.

---

### [PAPER 8] FActScore — Fine-grained Atomic Evaluation
```
Authors:  Min et al.
Venue:    EMNLP 2023
Citation: arXiv:2305.14251
```

**What it does:**
Scores the precision of a generated text by breaking it into atomic facts
and checking the fraction that are independently supported.
A VerifiedClaim with FActScore = 0.9 has 90% of its atomic facts supported.

**Applied here:**
After triangulation, each VerifiedClaim is assigned a `factscore`.
This is used in M5 as a quality multiplier in the pulse score formula:
high factscore claims contribute more to the final score than low
factscore claims. Prevents low-quality claims from inflating the score.

---

### Triangulation logic

```python
def triangulate(
    facts: List[FactObject],
) -> tuple[List[VerifiedClaim], List[tuple]]:

    # Step 1: MiniCheck validation (arXiv:2404.10774)
    validated = [f for f in facts if minicheck_validate(f)]

    # Step 2: Group by (entity, signal_type) — ClaimCheck grouping
    groups = defaultdict(list)
    for fact in validated:
        groups[(fact.entity, fact.signal_type)].append(fact)

    verified_claims = []
    contradiction_pairs = []

    for (entity, signal_type), group in groups.items():
        unique_domains = {extract_domain(f.source_url) for f in group}
        has_tier1      = any(f.source_tier == 1 for f in group)

        # ClaimCheck corroboration requirement (ACL 2025)
        if len(unique_domains) < 2 and not has_tier1:
            continue    # insufficient corroboration — skip

        # Contradiction detection
        sentiments     = {f.sentiment for f in group}
        is_contradicted = "positive" in sentiments and "negative" in sentiments

        # FActScore: atomic precision (arXiv:2305.14251)
        all_atomics = [a for f in group for a in (f.atomic_claims or [])]
        supported   = [a for a in all_atomics if is_atomic_supported(a, group)]
        factscore   = len(supported) / max(len(all_atomics), 1)

        # Recency-weighted sentiment (tier × recency)
        weighted_sent = calculate_weighted_sentiment(group)
        recency       = calculate_recency_score(group)
        confidence    = calculate_final_confidence(
            corroboration_count = len(unique_domains),
            source_tiers        = {f.source_tier for f in group},
            recency_score       = recency,
            factscore           = factscore,
        )

        verified_claims.append(VerifiedClaim(
            entity               = entity,
            signal_type          = signal_type,
            summary              = generate_summary(group),
            supporting_facts     = [f.fact_id for f in group],
            corroboration_count  = len(unique_domains),
            source_tiers_present = sorted({f.source_tier for f in group}),
            weighted_sentiment   = weighted_sent,
            recency_score        = recency,
            final_confidence     = confidence,
            factscore            = factscore,
            is_contradicted      = is_contradicted,
            contradiction_note   = None,  # written by write_contradiction_notes
        ))

        if is_contradicted:
            contradiction_pairs.append((entity, signal_type, group))

    return verified_claims, contradiction_pairs


def recency_weight(published_date: str, window_days: int = 7) -> float:
    age = days_since(published_date)
    return 0.0 if age > window_days else 1.0 / (age + 1)
    # Day 0 = weight 1.0 · Day 3 = 0.25 · Day 6 = 0.14


def calculate_weighted_sentiment(facts: List[FactObject]) -> float:
    tier_w = {1: 1.0, 2: 0.8, 3: 0.5, 4: 0.4}
    total  = sum(tier_w[f.source_tier] * recency_weight(f.published_date)
                 for f in facts)
    wmean  = sum(f.sentiment_score * tier_w[f.source_tier]
                 * recency_weight(f.published_date) for f in facts)
    return wmean / total if total > 0 else 0.0
```

### Contradiction rule

When contradiction is detected, the system does **NOT** blend the signals
into a neutral statement. Both sides are preserved explicitly as
`ContradictionFlag` and surfaced in the UI as-is. Users must make their
own judgment. Blending contradictory signals is a form of misinformation.

---

## 10. Node — Contradiction Writer

**File:** `app/pipeline/agent5_contradiction_writer.py`  
**Type:** LLM — OpenRouter via `LLMClient`; called from within the `triangulator` node  
**Research methods applied:** None — requires LLM judgment

> **Implementation note:** The contradiction writer is NOT a separate LangGraph
> node in the current implementation. `write_contradiction_notes()` is an async
> function called at the end of the `triangulator` node using `asyncio.gather`
> with a bounded semaphore (`MAX_CONCURRENT = 5`). Each call wraps the sync
> LLM via `asyncio.to_thread`. This is equivalent to parallel fan-out behavior
> without using the LangGraph `Send` API.

**Why a separate function:**
Contradiction *detection* is pure Python (comparing sentiment labels across
domains). Writing a precise, analyst-grade note that accurately and
symmetrically represents both sides requires language understanding.
Separating these ensures the detection step is deterministic and the
note-writing step is isolated and independently testable.

**System prompt:**

```
You are writing a contradiction note for a financial intelligence report.
Present BOTH sides accurately and symmetrically.
Do NOT lean toward either interpretation.
Do NOT blend the conflicting signals into a neutral statement.
Do NOT editorialize or add your own interpretation.
End with: "Recommend manual review before acting on this signal."

Entity:            {entity}
Signal type:       {signal_type}
Positive evidence: {positive_facts_json}
Negative evidence: {negative_facts_json}

Return: a single paragraph, max 100 words.
```

---

## 11. Node — M5 Signal Scorer

**File:** `app/pipeline/node_signal_scorer.py`  
**Type:** Pure Python — deterministic formula  
**LangGraph node:** `signal_scorer`  
**Research methods applied:** None — domain-specific weighted formula

### Signal weights

```python
SIGNAL_WEIGHTS = {
    "investor_signal":      0.25,   # highest — direct financial impact
    "news_sentiment":       0.20,
    "pricing_pressure":     0.18,   # direct margin impact
    "strategic_messaging":  0.15,
    "hiring_momentum":      0.12,
    "product_launch":       0.07,
    "supplier_risk":        0.03,   # low weight but triggers status override
}
```

### Scoring formula

```python
def calculate_signal_score(
    claims:      List[VerifiedClaim],
    signal_type: str,
) -> float:
    """
    signal_score incorporates:
      - weighted_sentiment (from FinBERT + tier + recency)
      - final_confidence   (corroboration depth)
      - factscore          (FActScore atomic precision — arXiv:2305.14251)
      - source tier        (Tier 1 evidence contributes more)
      - contradiction penalty: contradicted claims are weighted at 50%
    """
    relevant = [c for c in claims if c.signal_type == signal_type]
    if not relevant:
        return 0.0

    tier_rank = {1: 4, 2: 3, 3: 2, 4: 1}

    total_w, weighted_sum = 0.0, 0.0
    for c in relevant:
        base_w = (
            c.final_confidence
            * c.factscore
            * max(tier_rank.get(t, 1) for t in c.source_tiers_present)
        )
        w = base_w * (0.5 if c.is_contradicted else 1.0)
        weighted_sum += c.weighted_sentiment * w
        total_w      += w

    return weighted_sum / total_w if total_w > 0 else 0.0


def calculate_pulse_score(claims: List[VerifiedClaim]) -> tuple[float, float]:
    signal_scores = {st: calculate_signal_score(claims, st) for st in SIGNAL_WEIGHTS}
    raw           = sum(signal_scores[st] * w for st, w in SIGNAL_WEIGHTS.items())
    pulse         = (raw + 1) / 2 * 100   # normalize [-1,1] → [0,100]
    confidence    = mean([c.final_confidence * c.factscore for c in claims])
    return round(pulse, 1), round(confidence, 2)


def classify_pulse_status(
    score:             float,
    has_supplier_risk: bool,
    contradiction_rate: float,
) -> PulseStatus:
    if contradiction_rate > 0.4:         return PulseStatus.VOLATILE
    if has_supplier_risk and score < 55: return PulseStatus.RISK_RISING
    if score >= 70:                      return PulseStatus.HEATING_UP
    if score >= 45:                      return PulseStatus.STABLE
    return PulseStatus.COOLING_DOWN
```

The scorer also produces a **per-company breakdown** (pulse_score, pulse_status,
signal_scores, contradiction_rate per company) that feeds the Company Narratives
node downstream.

---

## 12. Node — Company Narratives

**File:** `app/pipeline/node_company_narratives.py`  
**Type:** LLM — OpenRouter via `LLMClient` (agent_name `"agent6"`)  
**LangGraph node:** `company_narratives`  
**Position in DAG:** After M5 Signal Scorer, before Narrative Synthesizer

This node was not present in the original architecture design. It was added to
produce structured per-company analyst cards that are consumed by both the
Narrative Synthesizer (Agent 6) and surfaced directly in the Company Lens
workspace tab.

### What it produces

For each tracked company, the node generates a `CompanyNarrative` object:

```python
@dataclass
class CompanyNarrative:
    company:              str
    ticker:               str
    momentum:             MomentumLabel     # strong_positive | positive | neutral
                                            #   | mixed | negative | elevated_risk
    momentum_score:       float             # -1.0 to 1.0
    narrative:            str               # analyst prose with [claim_id] citations
    key_events:           List[str]         # max 3 events from evidence
    key_drivers:          List[str]         # max 3 signal drivers
    competitive_position: str               # "gaining" | "holding" | "losing"
    supporting_claim_ids: List[str]
    evidence_count:       int
    price_current:        Optional[float]   # from Alpha Vantage if available
    price_change_7d_pct:  Optional[float]
    signal_lead_days:     Optional[int]
```

### Concurrency model

```python
# All companies are processed concurrently
narratives = await asyncio.gather(
    *[build_company_narrative(company, claims, signal_scores) for company in companies]
)
```

### Validation and retry

The LLM output is validated: citation IDs in `narrative` must exist in
`supporting_claim_ids`, and `competitive_position` must be one of the three
allowed values. On validation failure, the node sends a correction prompt
once before falling back to a pure-Python deterministic fallback narrative.

---

## 13. Agent 6 — Narrative Synthesizer

**File:** `app/pipeline/agent6_narrative_synthesizer.py`  
**Type:** LLM — OpenRouter via `LLMClient`  
**LangGraph node:** `narrative_synthesizer`

### [PAPER 9] STORM — Synthesis Through Outline, Research, and Multi-perspective
```
Authors:  Shao et al., Stanford University
Venue:    NAACL 2024
Citation: arXiv:2402.14207
```

**What it does:**
STORM generates long-form, grounded intelligence by:
1. Identifying distinct perspectives that need to be addressed
2. Reasoning through each perspective independently using its evidence
3. Synthesizing where perspectives agree, where they diverge, and why

This prevents the most common failure of single-pass generation:
LLM averages all signals into vague, uncommitted prose like
"the market shows mixed signals across several dimensions."

**Applied here:**
Each of the 4 signal layers (hiring, pricing, product, investor) is treated
as a distinct perspective. Agent 6 reasons through each independently, then
synthesizes the interactions — where they confirm each other, where they
create tension, and what that tension means for the market outlook.
Company narratives produced by the previous node are also provided as context.

---

### System prompt

```
You are a senior market analyst writing for buy-side investment teams.

Method: STORM multi-perspective synthesis (arXiv:2402.14207)

STEP 1 — ANALYZE EACH PERSPECTIVE INDEPENDENTLY:
For each signal type, reason through what the evidence shows on its own.
What does hiring data say? What does pricing data say? What does investor
signal data say? What does product activity say?

STEP 2 — IDENTIFY AGREEMENTS AND TENSIONS:
Where do perspectives point in the same direction? Where do they conflict?
What is unusual compared to what you would normally expect?

STEP 3 — SYNTHESIZE:
narrative_headline: 1 analyst-grade sentence. No filler language.
narrative_body:     3–5 sentences. Explain cross-signal causality.
                    Each sentence must cite ≥1 [claim_id].
anomalies:          patterns that don't fit normal expectations.

Rules:
- Never predict stock prices
- If signals conflict, state it explicitly — do not smooth it over
- Separate "what evidence shows" from "what it may mean"
- Inferences must start with "This may suggest..." or "Based on..."

Return ONLY valid JSON matching the MarketNarrative schema.

Verified claims:       {verified_claims_json}
Signal scores:         {signal_scores_json}
Company narratives:    {company_narratives_json}
```

### Post-generation validation

```python
def validate_narrative(
    narrative: MarketNarrative,
    valid_claim_ids: set[str],
) -> list[str]:
    errors = []
    cited = re.findall(r'\[claim_[a-z0-9]+\]', narrative.narrative_body)
    for cid in cited:
        if cid.strip('[]') not in valid_claim_ids:
            errors.append(f"Invalid claim_id: {cid}")
    for anomaly in narrative.anomalies:
        for fid in anomaly.fact_ids:
            if fid not in valid_fact_ids:
                errors.append(f"Anomaly references non-existent fact: {fid}")
    return errors

# On validation failure: one retry with errors injected into prompt
```

---

## 14. Agent 7 — Watch List Builder

**File:** `app/pipeline/agent7_watch_list_builder.py`  
**Type:** LLM — OpenRouter via `LLMClient`  
**LangGraph node:** `watch_list_builder`  
**Research methods applied:** None — forward-looking synthesis

Runs after Agent 6 so it has the completed market narrative as context.

**System prompt:**

```
Based on the evidence and the market narrative above, identify 3–5
forward indicators to monitor next week.

Focus ONLY on signals that are currently developing but not yet resolved.
Do not invent items not supported by evidence.

For each WatchItem:
  title:                   what to watch (max 10 words)
  rationale:               why it matters to a buy-side analyst (2 sentences)
  trigger:                 the specific condition that would confirm or deny this
  signals_pointing_there:  fact_ids or claim_ids pointing toward this developing
  urgency:                 one of: this_week | next_2_weeks | this_month

Return ONLY a valid JSON array of WatchItem objects.

Market narrative:  {market_narrative_json}
Verified claims:   {verified_claims_json}
```

---

## 15. Node — Report Assembler

**File:** `app/pipeline/node_report_assembler.py`  
**Type:** Pure Python  
**LangGraph node:** `report_assembler`  
**Research methods applied:** None

Assembles all pipeline outputs into a single `MarketPulseReport` object
and persists it via the database adapter.

```python
def assemble_report(state: PipelineState) -> MarketPulseReport:
    quality_status = _quality_status(state.get("quality_status", ...))

    # PARTIAL_PASS handling:
    # Cap pulse_confidence at 0.5 and prepend a warning to narrative_body
    pulse_confidence = float(scores.get("pulse_confidence", 0.0))
    if quality_status == QualityStatus.PARTIAL_PASS:
        pulse_confidence = min(pulse_confidence, 0.5)
        market_narrative = _mark_partial_narrative(market_narrative, quality_reasons)

    report = MarketPulseReport(
        report_id   = generate_uuid(),
        market      = state["market"],
        time_window = state["time_window"],
        generated_at= now_iso(),

        # Layer 1
        pulse_score         = state["signal_scores"]["pulse_score"],
        pulse_status        = state["signal_scores"]["pulse_status"],
        pulse_confidence    = pulse_confidence,
        trend_vs_previous   = None,   # no historical data in current release

        # Layer 2
        top_signals         = build_top_signals(verified_claims, scores, facts),
        company_narratives  = state["company_narratives"],
        news_items          = build_news_items(facts),

        # Layer 3 + 4
        market_narrative    = state["market_narrative"],
        contradictions      = state["contradictions"],
        grounded_brief      = build_grounded_brief(claims, quality_status, reasons),

        # Meta
        evidence_count  = len(facts),
        source_count    = len({f.source_url for f in facts}),
        signal_breakdown= state["signal_scores"]["breakdown"],
        quality_status  = quality_status,
        quality_reasons = quality_reasons,
        audit_summary   = _build_audit_summary(state, facts),
    )

    await db_adapter.save_report(report, facts, claims)
    return report
```

---

## 16. Pricing Nodes — Pre-extractor and Playbook

These two modules are not agents (no LLM calls) but provide specialized pricing
signal coverage that Agent 3 alone would miss.

### `pricing_pre_extractor.py` — Regex extractor for full pricing documents

**Problem it solves:**
Agent 3 truncates `doc.content` to ~8000 characters before sending to the LLM.
Cloud GPU pricing pages can be 50–100 KB and their price tables often fall
outside the truncation window, so Agent 3 extracts zero pricing facts from
them.

**How it works:**
Runs regex patterns (`_PRICE_AMOUNT_RE`) over the **full** `doc.content` before
truncation. For each price/rate match:
1. Extracts a ±400-character context window around the match
2. Infers GPU model from the window (H100, H200, B200, MI300X, A100, L40S, etc.)
3. Infers entity (Nvidia, AMD, Supermicro, or "market")
4. Rejects vague patterns via `_PRICING_REJECT_RE`
5. Deduplicates by `(url, gpu_model, normalized_price)`
6. Produces `FactObject` with `signal_type=pricing_pressure`, `safe_verified=False`
7. Caps at 8 facts per document

**Entry point:** `extract_pricing_facts_from_document(doc: RawDocument) -> List[FactObject]`

Called from `agent3_fact_extractors.py` for every document before the LLM
extraction step. Resulting facts are merged into the fact pool alongside
LLM-extracted facts.

---

### `pricing_pressure_playbook.py` — Deterministic pricing query generator

**Problem it solves:**
Agent 1 generates queries via LLM, which may underweight specific cloud pricing
sources (AWS, Azure, CoreWeave, RunPod, etc.) or may not know to target them
by current month. A fixed set of pricing queries ensures consistent coverage
regardless of LLM behavior on any given run.

**How it works:**
Produces 15 fixed `SearchQuery` objects for the demo scope:
- Nvidia × 4 queries (AWS, Azure, CoreWeave, RunPod GPU rental pages)
- AMD × 4 queries (same cloud providers targeting MI300X)
- Supermicro × 4 queries (wholesale GPU pricing, rack-scale pricing)
- market × 3 queries (GPU cloud pricing news, market-wide price trends)

Queries are anchored to the current month and targeted at specific domains
(`site:aws.amazon.com/ec2/`, `coreweave.com/pricing`, etc.).

**Entry points:**
- `build_pricing_playbook_specs()` → spec dicts
- `specs_to_search_queries()` → `List[SearchQuery]`

These queries are merged into Agent 1's output before being passed to Agent 2.
They form the "15 deterministic playbook queries" that guarantee pricing
signal coverage across every run.

---

## 17. Database Adapter Layer

**Files:** `app/db/adapter.py`, `app/db/sqlite_adapter.py`, `app/db/postgres_adapter.py`, `app/db/__init__.py`

The storage layer is abstracted behind a `DatabaseAdapter` ABC. The concrete
implementation is selected at startup via the `DATABASE_BACKEND` environment
variable.

### Abstract interface

```python
class DatabaseAdapter(ABC):
    async def save_report(self, report, facts=None, claims=None) -> None
    async def load_report(self, report_id: str) -> MarketPulseReport | None
    async def latest_report_id(self) -> str | None
    async def list_report_facts(self, report_id: str) -> list[FactObject]
    async def get_fact(self, report_id: str, fact_id: str) -> FactObject | None
    async def get_claim(self, report_id: str, claim_id: str) -> VerifiedClaim | None
    async def search_facts(self, report_id: str, query: str, top_k: int = 10) -> list[FactObject]
    async def get_company_narrative(self, report_id: str, ticker_or_company: str) -> CompanyNarrative | None
    async def save_chat_message(self, session_id: str, role: str, content: str) -> None
```

### Backend selection

```python
# app/db/__init__.py
def _build_adapter() -> DatabaseAdapter:
    backend = os.getenv("DATABASE_BACKEND", "sqlite").lower()
    if backend == "postgres":
        from app.db.postgres_adapter import PostgresAdapter
        return PostgresAdapter(os.environ["DATABASE_URL"])
    from app.db.sqlite_adapter import SQLiteAdapter
    return SQLiteAdapter()

db_adapter: DatabaseAdapter = _build_adapter()
```

| Backend | Adapter | Connection | Notes |
|---|---|---|---|
| `sqlite` (default) | `SQLiteAdapter` | `aiosqlite` → `backend/data/pulselens.db` | Thin wrapper around `database.py` |
| `postgres` | `PostgresAdapter` | `asyncpg` pool → Supabase or any Postgres | Lazy pool init, JSONB codec, pgvector for `search_facts` |

### Checkpointing

Both the pipeline graph and chat graph use `MemorySaver` for LangGraph
checkpoints. This means state is in-memory only and does not survive process
restarts. Replacing with `AsyncSqliteSaver` (or Postgres-backed saver) is
a planned follow-up.

---

## 18. Chat Graph — Analyst Chat

**Files:** `app/chat/graph.py` + `app/chat/agent8_analyst_chat.py`  
**Type:** Separate LangGraph StateGraph — runs on demand per user query  
**Does NOT re-run the pipeline** — queries from existing stored report

> **Current release:** Chat is synchronous request/response. The API endpoint
> (`POST /api/chat`) is an `async def` route that `await`s `chat_graph.ainvoke()`.
> Token streaming is not implemented; the full response is returned at once.

### Node sequence

```
[retrieve_facts]     semantic search over fact embeddings for the report
      ↓
[build_prompt]       inject evidence block + last 5 history exchanges
      ↓
[analyst_chat]       Agent 8: Self-RAG + FLARE patterns (see below)
                     Citations converted: [fact_xxx] → [1], [2], etc.
      ↓
[validate_citations] all [fact_id] refs must exist in retrieved facts
      ↓ valid                    ↓ invalid (1 built-in retry — same node)
return response      [retry: correction prompt with hallucinated IDs listed]
                     (no graph loop — retry is inside validate_citations node)
```

### Chat state

```python
class ChatState(TypedDict, total=False):
    report_id:          str
    session_id:         str
    history:            List[ChatMessage]    # last 5 exchanges only
    current_query:      str
    retrieved_facts:    List[FactObject]
    prompt:             str
    response:           str
    cited_fact_ids:     List[str]
    invalid_citations:  List[str]
    retrieval_rounds:   int                  # for FLARE tracking
    errors:             List[str]
    context_attachment: Optional[dict]       # see Context attachments below
```

### Context attachments

The frontend supports pre-attaching a selected card as context for the chat
query. When the user clicks "Ask Chat" from a workspace card, the URL carries
context params (e.g. `?context=watch_item&title=...`, `?context=fact&fact_id=...`).
The `ChatRequest` carries this as:

```python
class ContextAttachment(BaseModel):
    type:            str          # watch_item | risk_alert | fact | company | signal | pricing | report
    title:           Optional[str]
    entity:          Optional[str]
    signal_type:     Optional[str]
    summary:         Optional[str]
    rationale:       Optional[str]
    trigger:         Optional[str]
    urgency:         Optional[str]
    supporting_count: Optional[int]
    against_count:   Optional[int]
    evidence_quote:  Optional[str]
    confidence:      Optional[float]
    source_domain:   Optional[str]
    source_tier:     Optional[int]
    fact_id:         Optional[str]
```

The serialised attachment is injected into `ChatState.context_attachment` and
surfaced in the Agent 8 system prompt under:
```
Attached context (selected by the analyst from the PulseLens Overview):
{context_attachment_block}
```

This allows Agent 8 to answer specifically about the attached card
(watch item rationale, risk alert contradiction, evidence fact detail, etc.)
in addition to retrieved report facts.

### [PAPER 10] Self-RAG — Self-Reflective Retrieval Augmented Generation
```
Authors:  Asai et al.
Venue:    NeurIPS 2023
Citation: arXiv:2310.11511
```

**What it does:**
LLM decides *when* to retrieve, not just *what* to retrieve.
Before generating, the model emits special reflection tokens:
- `[IsREL]` — is the retrieved evidence relevant to the query?
- `[IsSUP]` — is the claim I'm about to make supported by evidence?
- `[IsUSE]` — is this response actually useful to the user?

If evidence is insufficient (`[IsSUP] = no`), the model pauses
and calls `search_facts()` again with a refined query before continuing.

**Why it matters here:**
Static RAG retrieves top-k facts once and generates regardless.
Self-RAG prevents the common failure: answering confidently from
retrieved context that doesn't actually support the answer.

---

### [PAPER 11] FLARE — Forward-Looking Active REtrieval
```
Authors:  Jiang et al.
Venue:    EMNLP 2023
Citation: arXiv:2305.06983
```

**What it does:**
Instead of retrieve-once-then-generate, FLARE generates the answer
sentence by sentence. When the model's confidence on a sentence drops
below a threshold, it pauses, formulates an implicit query from
the uncertain sentence, retrieves additional evidence, and
regenerates that sentence with the new context.

**Why it matters here:**
Complex multi-hop questions like "Why is AMD gaining share and what does
that mean for Nvidia's Q3?" require evidence for at least two separate
claims. A single retrieval pass gets evidence for one but not both.
FLARE fetches the second piece of evidence when it realizes it needs it.

---

### Citation validation

```python
def validate_citations(response: str, valid_ids: set[str]) -> tuple[bool, list]:
    cited        = re.findall(r'\[fact_[a-z0-9]+\]', response)
    hallucinated = [fid for fid in cited if fid.strip('[]') not in valid_ids]
    return (len(hallucinated) == 0), hallucinated

# On failure, retry prompt includes:
# "The following fact IDs you cited do not exist in this report: {list}.
#  Revise your response using only the evidence provided."
```

### Citation formatting for users

After citation validation, the backend converts internal `[fact_id]` references
to user-friendly numbered citations (`[1]`, `[2]`, etc.) before returning the
response. The `cited_facts` array in the API response is ordered to match:
`cited_facts[0]` → `[1]`, `cited_facts[1]` → `[2]`, etc.
The frontend renders numbered superscript badges inline and a "Sources used"
section below the assistant message.

---

## 19. Data flow diagram

```
Raw Query
    │
    ▼
SearchQuery[]          ← Step-Back + Multi-HyDE (arXiv:2310.06117, 2509.16369)
    │                     + 15 deterministic pricing playbook queries
    ▼
RawDocument[]          ← Bright Data (SERP API, Web Unlocker, Browser API)
    │
    ▼
FactObject[] (raw)     ← RASG schema extraction (arXiv:2405.20245)
    │                  ← pricing_pre_extractor regex pass (merged in)
    ▼
FactObject[] (validated)  ← validate_fact() — verbatim quote presence check
    │
    ▼
FactObject[] (atomic)  ← SAFE atomic verification (arXiv:2403.18802)
    │
    ▼
FactObject[] (scored)  ← FinBERT financial sentiment (ProsusAI/finbert)
    │
    ▼
FactObject[] (quality-checked)  ← Quality Gate — loop back if coverage low
    │
    ▼
VerifiedClaim[]        ← ClaimCheck corroboration (ACL 2025)
                          MiniCheck per-fact validation (arXiv:2404.10774)
                          FActScore atomic precision (arXiv:2305.14251)
    │
    ├── ContradictionFlag[]  ← write_contradiction_notes() (async, LLM)
    │
    ▼
SignalScores{}         ← Weighted formula (tier × recency × factscore)
PulseScore (0–100)
    │
    ▼
CompanyNarrative[]     ← Company Narratives node (LLM, async per company)
    │
    ▼
MarketNarrative        ← STORM multi-perspective (arXiv:2402.14207)
    │
    ▼
WatchItem[]            ← Watch List Builder (LLM)
    │
    ▼
MarketPulseReport      ← Report Assembler → db_adapter.save_report()
                          (SQLite or Postgres, selected by DATABASE_BACKEND)
    │
    └──────────────────────────────────────────┐
                                               │
                                     User Chat Query
                                     + optional ContextAttachment
                                               │
                                               ▼
                               retrieved FactObject[]  ← Self-RAG (arXiv:2310.11511)
                                               │           FLARE (arXiv:2305.06983)
                                               ▼
                               Grounded Response + [1][2] numbered citations
                               + context attachment injected in prompt
                                               │
                                               ▼
                               Citation validation → return to frontend
                               frontend renders: numbered superscripts + Sources section
```

---

## 20. Paper reference index

Complete reference list — every paper used in PulseLens.

---

### [1] Step-Back Prompting
```
Title:    Take a Step Back: Evoking Reasoning via Abstraction in Large Language Models
Authors:  Huaixiu Steven Zheng et al.
Venue:    Google DeepMind, 2023
Link:     https://arxiv.org/abs/2310.06117
Applied:  Agent 1 — Query Planner (first reasoning step before query generation)
```

---

### [2] Multi-HyDE (adapted — query generation step only)
```
Title:    Enhancing Financial RAG with Agentic AI and Multi-HyDE
Authors:  Srinivasan et al., IIT Madras
Venue:    EMNLP 2025
Link:     https://arxiv.org/abs/2509.16369
Results:  +11.2% accuracy, -15% hallucination on financial QA
Applied:  Agent 1 — Query Planner (diverse non-equivalent query fan-out only;
          hypothetical document synthesis, embedding, retrieval, and reranking
          steps are not implemented — web collection replaces vector retrieval)
```

---

### [3] RASG
```
Title:    RASG: Retrieval Augmented Structured Generation
          Business Document Information Extraction As Tool Use
Authors:  Cesista et al.
Venue:    2024
Link:     https://arxiv.org/abs/2405.20245
Applied:  Agent 3 — Fact Extractor (schema-constrained extraction prompt)
```

---

### [4] SAFE
```
Title:    Long-form Factuality in Large Language Models
          (introduces SAFE: Search-Augmented Factuality Evaluator)
Authors:  Jerry Wei et al., Google DeepMind
Venue:    2024
Link:     https://arxiv.org/abs/2403.18802
Applied:  Node — validate_and_split (atomic claim decomposition + verification)
```

---

### [5] FinBERT
```
Title:    FinBERT: Financial Sentiment Analysis with Pre-trained Language Models
Authors:  Yang et al.
Venue:    2020
Source:   https://huggingface.co/ProsusAI/finbert
Applied:  Agent 4 — FinBERT Scorer (sentiment classification on every fact.claim)
```

---

### [6] ClaimCheck
```
Title:    ClaimCheck: Automated Fact-Checking via Web Evidence
Authors:  Putta et al.
Venue:    ACL / KnowledgeNLP Workshop 2025
Results:  62.6% verdict accuracy on AVeriTeC benchmark
Applied:  Node — M4 Triangulator (cross-source corroboration logic)
```

---

### [7] MiniCheck
```
Title:    MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents
Authors:  Tang et al.
Venue:    2024
Link:     https://arxiv.org/abs/2404.10774
Results:  GPT-4-level F1, 400× faster
Applied:  Node — M4 Triangulator (per-fact validation before corroboration)
```

---

### [8] FActScore
```
Title:    FActScore: Fine-grained Atomic Evaluation of Factual Precision
          in Long Form Text Generation
Authors:  Min et al.
Venue:    EMNLP 2023
Link:     https://arxiv.org/abs/2305.14251
Applied:  Node — M4 Triangulator (atomic precision score stored as VerifiedClaim.factscore)
          Node — M5 Signal Scorer (factscore used as quality multiplier in pulse formula)
```

---

### [9] STORM
```
Title:    Assisting in Writing Wikipedia-like Articles From Scratch
          with Large Language Models
          (introduces STORM: Synthesis Through Outline, Research, Multi-perspective)
Authors:  Shao et al., Stanford University
Venue:    NAACL 2024
Link:     https://arxiv.org/abs/2402.14207
Applied:  Agent 6 — Narrative Synthesizer (multi-perspective market brief generation)
```

---

### [10] Self-RAG
```
Title:    Self-RAG: Learning to Retrieve, Generate, and Critique through
          Self-Reflection
Authors:  Asai et al.
Venue:    NeurIPS 2023
Link:     https://arxiv.org/abs/2310.11511
Applied:  Agent 8 — Analyst Chat (self-reflective retrieval decisions)
```

---

### [11] FLARE
```
Title:    Active Retrieval Augmented Generation
          (introduces FLARE: Forward-Looking Active REtrieval)
Authors:  Jiang et al.
Venue:    EMNLP 2023
Link:     https://arxiv.org/abs/2305.06983
Applied:  Agent 8 — Analyst Chat (sentence-level active retrieval for multi-hop questions)
```

---

*Version 2.0 — Updated to reflect Sprint 8 codebase.*  
*Every non-trivial design decision traces back to a peer-reviewed method.*  
*Changes from v1.0: corrected pipeline DAG order; added Company Narratives node;*  
*added Pricing nodes; corrected Agent 2 fan-out (internal batching, not Send API);*  
*corrected Agent 6/7 sequencing (not parallel); added DB Adapter layer;*  
*updated Chat section (sync, no streaming, context attachments, citation formatting);*  
*updated Frontend section (Workspace with 6 URL-driven views, standalone Chat page).*
