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
- Agent 6 Narrative Synthesizer: STORM-inspired narrative generation with citation validation and fallback.
- Agent 7 Watch List Builder: evidence-backed forward indicators with urgency validation and fallback.
- Report Assembler: builds and saves `MarketPulseReport` to SQLite.
- API: `/api/run`, `/api/report/{report_id}`, and `/api/stock/{ticker}` are wired.
- Frontend: TypeScript and production build pass.

## Important Caveats

- Agent 1 live execution still requires working OpenRouter network/API access.
- Agent 2 live execution requires Bright Data zones and credits.
- Agent 6 and Agent 7 are STORM-inspired prompt implementations, not full STORM research loops.
- M4 uses ClaimCheck/MiniCheck/FActScore-inspired proxies, not the full paper implementations.
- LangGraph still uses `MemorySaver`; SQLite checkpointing is still a follow-up.
- LangGraph `Send` fan-out is still a follow-up; Agent 2 and Agent 3 currently batch internally.
- Chat Agent 8 is still placeholder work.

## Next Best Step

Run one live backend pipeline with real API keys, inspect the generated report quality, then decide whether to harden Agent 6/7 prompts or start Agent 8 chat.
