# PulseLens Project Status

Last updated: 2026-05-25

## Built Now

- Agent 1 Query Planner: Step-Back abstraction plus Multi-HyDE-inspired 40-50 query fan-out.
- Agent 2 Web Workers: Bright Data SERP discovery, page scraping, cache, source tiering, and content filtering.
- Agent 3 Fact Extractors: RASG-inspired structured JSON extraction, entity normalization, and validation.
- SAFE-inspired validation node: verbatim quote validation plus atomic evidence support check.
- Agent 4 FinBERT Scorer: batch financial sentiment scoring.
- Quality Gate: wired between Agent 4 and M4; expands queries when fact volume or signal coverage is low.
- M4 Triangulator: corroboration, Tier-1 override, contradiction detection, and confidence/factscore proxies.
- Agent 5 Contradiction Writer: LLM-written symmetric contradiction notes.
- M5 Signal Scorer: deterministic pulse score, status, confidence, and breakdowns using shared signal weights.
- Company Narratives: dashboard-ready company cards built between M5 and Agent 6, with deterministic fallback.
- Agent 6 Narrative Synthesizer: STORM-inspired narrative generation with citation validation and fallback.
- Agent 7 Watch List Builder: evidence-backed forward indicators with urgency validation and fallback.
- Report Assembler: builds and saves `MarketPulseReport`, facts, claims, and fact embeddings to SQLite.
- Chat Agent 8: grounded analyst chat over stored facts, with citation validation and fallback.
- API: `/api/run`, `/api/report/{report_id}`, `/api/stock/{ticker}`, and `/api/chat` are wired.
- Frontend: TypeScript and production build pass.

## Important Caveats

- Agent 1 live execution still requires working OpenRouter network/API access.
- Agent 2 live execution requires Bright Data zones and credits.
- Stored fact embeddings use `sentence-transformers`; if the model is unavailable, chat falls back to lexical fact search.
- Agent 6 and Agent 7 are STORM-inspired prompt implementations, not full STORM research loops.
- Agent 8 is Self-RAG/FLARE-inspired; it performs grounded retrieval discipline and citation validation, not the full paper training setup.
- M4 uses ClaimCheck/MiniCheck/FActScore-inspired proxies, not the full paper implementations.
- LangGraph still uses `MemorySaver`; SQLite checkpointing is still a follow-up.
- LangGraph `Send` fan-out is still a follow-up; Agent 2 and Agent 3 currently batch internally.

## Next Best Step

Run one live backend pipeline with real API keys, inspect the generated report and chat answer quality, then harden any weak prompts or source filters before demo polish.
