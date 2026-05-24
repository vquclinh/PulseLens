# PulseLens Re-Audit Report (Post-Fix)

Scope: re-audited only implemented/fixed code and intentionally skipped future-work placeholders listed by the user. I did not treat Agent 2-8 stubs, Send fan-out, API stubs, real quality-gate scoring logic, chat logic, tests, or frontend mock data as bugs unless a post-fix change broke currently used code.

## 1. Fix verification -- did each fix land correctly?

| Fix | Status | Evidence (file:line) |
|-----|--------|---------------------|
| 1. Entity validation enforced in _parse_and_validate() | FIXED | `_VALID_ENTITIES` is defined at `backend/app/pipeline/agent1_query_planner.py:37`; invalid `target_entity` is skipped at `backend/app/pipeline/agent1_query_planner.py:302-306`. Runtime check with `FakeCompany` produced "Skipping query ... invalid target_entity". |
| 2. Expansion mode uses separate min_queries (5 for expansion, 15 for normal) | PARTIALLY FIXED | Separate constants exist at `backend/app/config/quality_gates.py:2-3`; Agent 1 selects `MIN_EXPANSION_QUERIES` vs `MIN_QUERIES` at `backend/app/pipeline/agent1_query_planner.py:194-198`; `_parse_and_validate()` accepts caller-supplied `min_queries` at `backend/app/pipeline/agent1_query_planner.py:280-282` and applies it at `backend/app/pipeline/agent1_query_planner.py:340-345`. Remaining issue: expansion still enforces every expected company at `backend/app/pipeline/agent1_query_planner.py:355-358`, so a 7-query expansion cannot pass for the full 8-company universe. |
| 3. query_expansion_rounds no longer incremented in query_planner | FIXED | `query_planner()` returns only `{"queries": existing + queries}` at `backend/app/pipeline/graph.py:43-44`; `quality_gate()` owns the increment at `backend/app/pipeline/graph.py:92-96`. |
| 4. "Multi-HyDE" renamed to "Multi-HyDE-inspired" in code and docs | PARTIALLY FIXED | Main Agent 1 code is corrected at `backend/app/pipeline/agent1_query_planner.py:1-4`, `backend/app/pipeline/agent1_query_planner.py:94-96`, and `backend/app/pipeline/graph.py:29-30`. Architecture section is partially corrected at `ARCHITECTURE.md:273-293`. Remaining stale docs still say plain Multi-HyDE at `ARCHITECTURE.md:117`, `ARCHITECTURE.md:319`, `ARCHITECTURE.md:1243`, and `idea.md:473`. |
| 5. Python schemas use Literal types (source_tier, sentiment, urgency, etc.) | PARTIALLY FIXED | Previously flagged fields are fixed: `RawDocument.source_tier` and `signal_type_hint` at `backend/app/schemas/models.py:43-45`; `FactObject.source_tier` and `sentiment` at `backend/app/schemas/models.py:56-58`; `AnomalyFlag.signal_types_involved` at `backend/app/schemas/models.py:81-85`; `WatchItem.urgency` at `backend/app/schemas/models.py:88-93`; `CompanyNarrative.momentum_score` and `competitive_position` at `backend/app/schemas/models.py:96-104`. Remaining similar loose fields: `NewsItem.source_tier` and `NewsItem.sentiment` are still `int`/`str` at `backend/app/schemas/models.py:139-148`; `SearchQuery.expected_source_tier` is still `int` at `backend/app/schemas/models.py:192-199`. |
| 6. Duplicate frontend api.ts types removed, index.ts is single source | PARTIALLY FIXED | Model definitions are centralized in `frontend/src/types/index.ts:3-210`; `frontend/src/types/api.ts:1-9` imports from `./index` instead of redefining models. New issue: `api.ts` does not re-export those types, while many files still import types from `@/types/api`, e.g. `frontend/src/lib/api-client.ts:2`. `npm run build` fails with missing exports. |
| 7. Model names configurable via env, default is gemini-2.5-flash | FIXED | Default model is `google/gemini-2.5-flash` at `backend/app/utils/llm_client.py:17`; per-agent env loading is at `backend/app/utils/llm_client.py:19-27`; Agent 1 passes `agent_name="agent1"` at `backend/app/pipeline/agent1_query_planner.py:166-169`; `.env.example` lists `AGENT1_MODEL` through `AGENT8_MODEL` at `backend/.env.example:14-20`. |
| 8. Step-Back prompt outputs structured JSON with example | FIXED, with enforcement caveat | Prompt includes a JSON example at `backend/app/pipeline/agent1_query_planner.py:81-88`, requires JSON at `backend/app/pipeline/agent1_query_planner.py:90-91`, and forbids search queries at `backend/app/pipeline/agent1_query_planner.py:91`. Caveat: code calls `call_text()` and falls back to raw text on parse failure at `backend/app/pipeline/agent1_query_planner.py:210-221`, so JSON is requested but not strictly enforced. |
| 9. Query Gen prompt has good/bad examples and site: operators | FIXED | Company site domains are built at `backend/app/pipeline/agent1_query_planner.py:52-56` and injected at `backend/app/pipeline/agent1_query_planner.py:117-119` and `backend/app/pipeline/agent1_query_planner.py:241-254`; good/bad examples are at `backend/app/pipeline/agent1_query_planner.py:133-140`; site-operator rule is at `backend/app/pipeline/agent1_query_planner.py:146`; time-anchor rule is at `backend/app/pipeline/agent1_query_planner.py:143`. |
| 10. IR domains derived from companies.py, not hardcoded in source_tiers.py | FIXED | `source_tiers.py` imports `COMPANIES` at `backend/app/config/source_tiers.py:5`; `TIER_1_DOMAINS` derives IR domains from `c.ir_url` at `backend/app/config/source_tiers.py:7-12`; `assign_tier()` still normalizes `www.` and returns tier 1 for IR URLs at `backend/app/config/source_tiers.py:51-63`. Runtime check: `assign_tier("https://ir.nvidia.com/news") == 1`. |

Corrections still needed:
- For Fix 2, expansion validation needs a mode-aware company coverage policy. Either allow expansion to target only low-signal gaps without full 8-company coverage, or require expansion target count to be at least 8 when all-company coverage is still mandatory.
- For Fix 4, update remaining docs/comments to consistently say "Multi-HyDE-inspired query fan-out" when referring to implemented Agent 1 code.
- For Fix 6, either change all imports to `@/types/index` or add `export type * from './index'` to `frontend/src/types/api.ts`.

## 2. Agent 1 logic -- is it correct now?

| Check | Result |
|---|---|
| Does `_parse_and_validate()` reject `target_entity="FakeCompany"`? | Yes. It skips invalid entities at `backend/app/pipeline/agent1_query_planner.py:302-306`. Runtime check showed `FakeCompany` rows were skipped. |
| Does expansion mode with `min_queries=5` accept 7 queries? | Partially. `_parse_and_validate(..., min_queries=5)` accepts 7 valid queries when expected company coverage is satisfiable. However, for the real 8-company market, 7 queries cannot satisfy all-company coverage at `backend/app/pipeline/agent1_query_planner.py:355-358`. |
| Does normal mode with `min_queries=15` reject 10 queries? | Yes. Runtime check rejected 10 queries with "minimum is 15"; validation is at `backend/app/pipeline/agent1_query_planner.py:340-345`. |
| Is `query_expansion_rounds` ONLY modified by `quality_gate` node? | Yes in implemented pipeline code. `query_planner` only reads it at `backend/app/pipeline/graph.py:31-41`; `quality_gate` increments at `backend/app/pipeline/graph.py:92-96`. |
| Does the Step-Back prompt produce JSON output? | The prompt requests JSON, but the code does not enforce it. It calls `call_text()` at `backend/app/pipeline/agent1_query_planner.py:210-213` and falls back to raw text on JSON parse failure at `backend/app/pipeline/agent1_query_planner.py:215-221`. |
| Does the Query Gen prompt include good/bad examples? | Yes, at `backend/app/pipeline/agent1_query_planner.py:133-140`. |
| Does the Query Gen prompt inject company `ir_url` and `careers_url`? | It injects derived IR/careers domains, not full URLs. Domain derivation is at `backend/app/pipeline/agent1_query_planner.py:52-56`; prompt injection is at `backend/app/pipeline/agent1_query_planner.py:117-119`. This is acceptable for `site:` operators, but it is not literal full-URL injection. |
| Are all 8 companies guaranteed to get at least 1 query? | Yes for normal Agent 1 validation when `expected_companies` is the 8-company list. Zero coverage raises `_CoverageValidationError` at `backend/app/pipeline/agent1_query_planner.py:355-358`. |
| Are all 7 signal types guaranteed coverage? | No. Normal prompt asks for all signal types, but validation only requires `MIN_SIGNAL_TYPES = 5` at `backend/app/config/quality_gates.py:4` and `backend/app/pipeline/agent1_query_planner.py:347-353`. |
| Is there post-generation duplicate triple detection? | Yes. Duplicate `(target_entity, signal_type, source_type)` triples are deduplicated at `backend/app/pipeline/agent1_query_planner.py:325-335`. It keeps the first occurrence rather than raising immediately. |

Agent 1 logic verdict: almost ready, but two correctness gaps remain before Agent 2: expansion coverage policy and all-7-signal enforcement.

## 3. Schema strictness -- are types tight now?

| Field | Expected type | Actual type now | OK? |
|-------|--------------|----------------|-----|
| RawDocument.source_tier | `Literal[1,2,3,4]` | `Literal[1, 2, 3, 4]` at `backend/app/schemas/models.py:43` | Yes |
| RawDocument.signal_type_hint | `Optional[SignalType]` | `Optional[SignalType]` at `backend/app/schemas/models.py:45` | Yes |
| FactObject.source_tier | `Literal[1,2,3,4]` | `Literal[1, 2, 3, 4]` at `backend/app/schemas/models.py:56` | Yes |
| FactObject.sentiment | `Literal["positive","negative","neutral"]` | `Literal["positive", "negative", "neutral"]` at `backend/app/schemas/models.py:58` | Yes |
| AnomalyFlag.signal_types_involved | `List[SignalType]` | `List[SignalType]` at `backend/app/schemas/models.py:83` | Yes |
| WatchItem.urgency | `Literal["this_week","next_2_weeks","this_month"]` | `Literal["this_week", "next_2_weeks", "this_month"]` at `backend/app/schemas/models.py:93` | Yes |
| CompanyNarrative.momentum_score | `int` | `int` at `backend/app/schemas/models.py:100` | Yes |
| CompanyNarrative.competitive_position | `Literal["gaining","holding","losing"]` | `Literal["gaining", "holding", "losing"]` at `backend/app/schemas/models.py:104` | Yes |

Additional note: `NewsItem.source_tier` / `NewsItem.sentiment` and `SearchQuery.expected_source_tier` remain loose (`backend/app/schemas/models.py:145-148`, `backend/app/schemas/models.py:192-199`). They were not in the requested strictness table, but they are the same class of schema looseness.

## 4. Configuration consistency

- Default Agent 1 model: `google/gemini-2.5-flash`.
  Evidence: `_DEFAULT_MODEL` at `backend/app/utils/llm_client.py:17`; `AGENT_MODELS["agent1"]` at `backend/app/utils/llm_client.py:21`.

- Env or hardcoded:
  The model is env-configurable with a hardcoded default. This is acceptable for a default. Evidence: `os.getenv("AGENT1_MODEL", _DEFAULT_MODEL)` at `backend/app/utils/llm_client.py:21`.

- `.env.example` coverage:
  Yes, it lists `AGENT1_MODEL` through `AGENT8_MODEL` at `backend/.env.example:14-20`.

- OpenRouter vs Anthropic SDK consistency:
  Not fully consistent across docs. Code and `.env.example` consistently use OpenRouter: `OPENROUTER_BASE_URL` at `backend/app/utils/llm_client.py:15`, `OPENROUTER_API_KEY` at `backend/app/utils/llm_client.py:43-45`, and `backend/.env.example:1`. But docs still say Anthropic SDK/API in `ARCHITECTURE.md:104`, `idea.md:279`, `idea.md:1072`, and `idea.md:1152`.

- TIER_1_DOMAINS:
  Fixed. It is derived from `companies.py` IR URLs plus `sec.gov` at `backend/app/config/source_tiers.py:7-12`.

## 5. Prompt quality re-check

### Step-Back prompt:

| Check | Result |
|---|---|
| Does it request JSON output now? | Yes. `backend/app/pipeline/agent1_query_planner.py:90-91`. |
| Does it include at least 1 example? | Yes. `hiring_momentum` JSON example at `backend/app/pipeline/agent1_query_planner.py:81-88`. |
| Does it say "do NOT generate search queries in this step"? | Yes. `backend/app/pipeline/agent1_query_planner.py:91`. |

Prompt quality: improved. Enforcement caveat remains because non-JSON output only logs a warning and continues.

### Query Gen prompt:

| Check | Result |
|---|---|
| Does it include GOOD vs BAD query examples? | Yes. `backend/app/pipeline/agent1_query_planner.py:133-140`. |
| Does it instruct use of `site:` operators? | Yes. Domain list and SEC site are at `backend/app/pipeline/agent1_query_planner.py:117-119`; rule is at `backend/app/pipeline/agent1_query_planner.py:146`. |
| Does it inject company `ir_url` and `careers_url`? | Partially. It injects `ir_domain` and `careers_domain` derived from those URLs at `backend/app/pipeline/agent1_query_planner.py:52-56`. |
| Does it require time anchors in every query? | Yes. `backend/app/pipeline/agent1_query_planner.py:142-143`. |
| Is there post-validation for duplicate triples? | Yes. `backend/app/pipeline/agent1_query_planner.py:325-335`. |

Prompt quality: much better and reasonable for Agent 1. Remaining gap: all-7-signal coverage is prompt-level, not validator-level.

## 6. Remaining hardcoded values

Only implemented/used code considered.

| File:line | Hardcoded value | Why it matters |
|---|---|---|
| `backend/app/utils/llm_client.py:15` | `https://openrouter.ai/api/v1` | Used by every LLM call. If provider is intended to stay OpenRouter, this is acceptable as a provider constant; if provider may change, make it env-configurable. |
| `backend/app/utils/llm_client.py:29` | `_RETRY_DELAYS = [1, 2, 4]` | Used by LLM retry loops. Should be a named config constant or env only if tuning is expected. |
| `backend/app/utils/llm_client.py:61`, `backend/app/utils/llm_client.py:102`, `backend/app/pipeline/agent1_query_planner.py:258` | `4096` / `2048` token limits | Used by Agent 1 LLM calls. Should probably become per-agent config before production. |
| `backend/main.py:10` | fallback `http://localhost:5173` | Used by CORS. This is acceptable as a dev default because `CORS_ORIGINS` can override it. |
| `backend/app/pipeline/agent1_query_planner.py:235` | `range(2)` coverage retry count | Used in Agent 1. Should be a named constant if the retry policy matters. |
| `backend/app/pipeline/agent1_query_planner.py:196` | target strings `"5 to 10"` / `"15 to 25"` | Used in prompt. Better as config constants paired with validation thresholds. |
| `backend/app/pipeline/agent1_query_planner.py:133-140` | Nvidia/AMD/Intel examples | Used in prompt. These are acceptable as examples, not operational company configuration. |

## 7. LangGraph graph.py -- is the skeleton still valid?

| Check | Result |
|---|---|
| Does `graph.py` compile without errors? | Yes. Runtime import produced `CompiledStateGraph`. |
| Are placeholder nodes clearly marked? | Yes. File header marks placeholders at `backend/app/pipeline/graph.py:1-2`, and placeholder block at `backend/app/pipeline/graph.py:26-27`. |
| Is the conditional edge for `quality_gate` correctly wired? | Yes. Router returns `expand_queries` or `proceed` at `backend/app/pipeline/graph.py:139-146`; conditional mapping is at `backend/app/pipeline/graph.py:177-185`. Runtime check routed low signal coverage to `expand_queries` and sufficient coverage to `proceed`. |
| Is `query_expansion_rounds` handled correctly now? | Yes for the skeleton. `query_planner` only reads it at `backend/app/pipeline/graph.py:31-41`; `quality_gate` increments at `backend/app/pipeline/graph.py:92-96`. |
| Is checkpointer still configured? | Yes. SQLite connection and `SqliteSaver` compile are at `backend/app/pipeline/graph.py:194-197`. |

Skeleton verdict: valid for current Agent 1 work, with future-work placeholders intentionally left alone.

## 8. New issues introduced by fixes

| Check | Result |
|---|---|
| Did Fix 5 stricter types break backend imports? | No. `python -m compileall -q backend/app` completed successfully, and model import/Pydantic validation works. Invalid `source_tier=5` is rejected. |
| Did Fix 8 JSON Step-Back break Step-Back -> Query Gen connection? | No hard break. Raw Step-Back text is still assigned to `abstract_principles` at `backend/app/pipeline/agent1_query_planner.py:221` and injected into Query Gen at `backend/app/pipeline/agent1_query_planner.py:241-254`. However, JSON is not strictly enforced because non-JSON falls back to raw text at `backend/app/pipeline/agent1_query_planner.py:215-221`. |
| Did Fix 10 derived IR domains break `assign_tier()`? | No. Runtime checks: derived `TIER_1_DOMAINS` contains all 8 IR domains plus `sec.gov`; `assign_tier("https://ir.nvidia.com/news") == 1`; `assign_tier("https://www.reuters.com/x") == 2`; unknown domains return 4. |
| Does frontend still compile after Fix 6? | No. `npm run build` fails because `frontend/src/types/api.ts` imports types from `./index` but does not export them, while existing code imports model types from `@/types/api`. Example: `frontend/src/lib/api-client.ts:2` imports `MarketPulseReport`, `ChatRequest`, `ChatResponse`, and `StockContext` from `@/types/api`, but `frontend/src/types/api.ts:4-9` only imports them locally. |

New issue introduced:
- `frontend/src/types/api.ts` must either re-export all model types (`export type * from './index'`) or all imports must be migrated to `@/types/index`. Current state breaks frontend TypeScript compilation.

## 9. Verdict

- Is Agent 1 now correct enough to proceed to Agent 2? No, but it is close.

- Top remaining issues that block Agent 2 build:
  1. Expansion mode is logically inconsistent with all-company coverage. A 5-10 query expansion cannot guarantee 8-company coverage. Make expansion validation mode-aware.
  2. All 7 signal types are not post-validated. `MIN_SIGNAL_TYPES = 5` means the LLM can omit two signal types and still pass.
  3. Frontend type export fix broke compilation. This does not block backend Agent 2 directly, but it is a real introduced issue and should be corrected immediately.

- Overall quality rating: ALMOST READY.

The Agent 1 fixes are substantial and mostly correct. After the expansion coverage policy, signal coverage validation, and frontend type export issue are fixed, Agent 1 is ready enough to serve as the input contract for Agent 2.
