# PulseLens Codebase Audit Report

Input note: requested `PULSELENS_PROJECT.md` and `papers/MULTI_HYDE.pdf` are not present in this checkout. I audited the product spec present as `idea.md` and the paper file present as `papers/MULTI-HYDE.pdf`, plus `ARCHITECTURE.md`, `papers/TAKE_A_STEP_BACK.pdf`, all 34 Python files under `backend/app/`, and `frontend/src/types/index.ts` as requested.

## 1. Step-Back Prompting verification (arXiv:2310.06117)

Paper baseline:
- `papers/TAKE_A_STEP_BACK.pdf` defines Step-Back Prompting as abstraction before task solving: derive a higher-level concept/principle, then reason using that abstraction. The extracted paper text states that the method has two steps: abstraction and reasoning (`/tmp/pulselens_step_back_audit.txt:113-119`).
- The paper emphasizes that Step-Back is higher-level abstraction, not decomposition into lower-level sub-questions (`/tmp/pulselens_step_back_audit.txt:581-596`).
- For knowledge QA, the paper uses few-shot examples to generate a more generic step-back question, then uses original and step-back context in the final answer prompt (`/tmp/pulselens_step_back_audit.txt:1115-1227`).

Verification table:

| Requirement | Verdict | Evidence |
|---|---|---|
| Does the implementation perform abstraction BEFORE query generation? | PASS | `_STEP_BACK_SYSTEM` is defined at `backend/app/pipeline/agent1_query_planner.py:49-71`. `QueryPlanner.run()` calls `self._llm.call_text()` for Step-Back at `backend/app/pipeline/agent1_query_planner.py:166-179`. Query generation starts after that at `backend/app/pipeline/agent1_query_planner.py:189-215`. |
| Is the Step-Back output used as context in the next step, not discarded? | PASS | The query generation prompt includes `{abstract_principles}` at `backend/app/pipeline/agent1_query_planner.py:81-83`. The actual value is injected at `backend/app/pipeline/agent1_query_planner.py:198-200`. |
| Does the Step-Back prompt ask the correct abstraction question as described in the paper? | PASS, adapted | The paper asks for a higher-level concept/principle. The implementation asks what the "web evidence landscape" would look like under accelerating, decelerating, and structural stress conditions at `backend/app/pipeline/agent1_query_planner.py:55-57`. This is a domain-specific abstraction question and is appropriate for market-intelligence query planning. |
| Does the prompt ask about each signal type separately? | PASS | The prompt explicitly says "For EACH of the 7 signal types" and asks for 2-4 sentences each at `backend/app/pipeline/agent1_query_planner.py:59-63`. |
| Does the prompt ask for positive and negative evidence patterns? | PASS | Positive/accelerating evidence and negative/decelerating evidence are requested at `backend/app/pipeline/agent1_query_planner.py:60-61`. |
| Does the prompt ask which source types carry reliable signal? | PASS | Source reliability is requested at `backend/app/pipeline/agent1_query_planner.py:62`. |
| Are there deviations from the paper methodology? | PARTIAL | There are no few-shot Step-Back examples in code, unlike the paper examples at `/tmp/pulselens_step_back_audit.txt:1115-1126`. The Step-Back output is free-form prose (`backend/app/pipeline/agent1_query_planner.py:70`), not structured JSON. The code also says "runs once" at `backend/app/pipeline/agent1_query_planner.py:166`, but `run()` will execute Step-Back again on every expansion call. |

Exact implementation path:
- Step-Back prompt: `backend/app/pipeline/agent1_query_planner.py:49-71`
- Step-Back call: `backend/app/pipeline/agent1_query_planner.py:166-179`
- Stored for inspection: `backend/app/pipeline/agent1_query_planner.py:178`
- Step-Back injected into query generation: `backend/app/pipeline/agent1_query_planner.py:81-83` and `backend/app/pipeline/agent1_query_planner.py:198-200`

Verdict: The Step-Back implementation is a good domain adaptation, but not paper-exact. It should be made structured and should include examples if this is expected to be robust in production.

## 2. Multi-HyDE verification (arXiv:2509.16369)

Paper baseline:
- The Multi-HyDE paper describes HyDE as generating hypothetical documents, embedding them, and retrieving real documents similar to those synthetic documents (`/tmp/pulselens_multi_hyde_audit.txt:34-42`).
- The Multi-HyDE method combines multi-query retrieval and HyDE, plus BM25 and a reranker (`/tmp/pulselens_multi_hyde_audit.txt:279-282`).
- Algorithm 1 is explicit: generate query variants, generate hypothetical documents, embed them, retrieve, concatenate, rerank, return (`/tmp/pulselens_multi_hyde_audit.txt:361-374`).

Implementation mapping:

| Real Multi-HyDE step | Status | Actual code |
|---|---|---|
| 1. Generate multiple query variants | ADAPTED | Query generation prompt asks for non-equivalent search queries at `backend/app/pipeline/agent1_query_planner.py:73-127`; LLM JSON call happens at `backend/app/pipeline/agent1_query_planner.py:211-215`. |
| 2. Generate hypothetical documents for each query | MISSING | The prompt says each query should target a "DIFFERENT hypothetical document" at `backend/app/pipeline/agent1_query_planner.py:76-79`, but no code generates hypothetical documents. |
| 3. Embed hypothetical documents | MISSING | No embedding model, vector store, or embedding call exists in `backend/app/`. |
| 4. Retrieve using embeddings | MISSING | `backend/app/pipeline/m2_web_collection.py:8-9` is a stub. It will eventually perform web collection, not Multi-HyDE vector retrieval. |
| 5. Rerank results | MISSING | No reranker is implemented. There is no cross-encoder/BGE/BM25 reranking layer. |

Naming honesty:
- Code overclaims: `backend/app/pipeline/agent1_query_planner.py:74` says it is "applying Multi-HyDE methodology"; `backend/app/pipeline/agent1_query_planner.py:1-3` labels the module Step-Back + Multi-HyDE.
- Docs overclaim: `ARCHITECTURE.md:281-286` describes full Multi-HyDE-like retrieval, but code only produces search-query strings.
- More honest name: `Step-Back + Multi-HyDE-inspired web query fan-out`.

Acceptability:
- For a web-search MVP, adapting only the non-equivalent query fan-out portion is acceptable if documented honestly.
- It is not acceptable to claim paper-faithful Multi-HyDE until hypothetical document generation, embeddings, retrieval, and reranking exist.

Verdict: Multi-HyDE is ADAPTED at best. Full Multi-HyDE is not implemented.

## 3. LangGraph architecture audit

Pipeline graph requirements from `ARCHITECTURE.md`:
- Parallel M2/M3 fan-out via `Send` API: `ARCHITECTURE.md:96`, `ARCHITECTURE.md:120-137`
- Conditional quality-gate loop: `ARCHITECTURE.md:172-181`, `ARCHITECTURE.md:638-661`
- Full DAG from Query Planner through Report Assembler: `ARCHITECTURE.md:109-233`
- SQLite checkpointing: `ARCHITECTURE.md:97`

Pipeline graph findings:

| Check | Verdict | Requirement vs actual |
|---|---|---|
| Are all architecture nodes registered? | MOSTLY YES | Nodes are registered at `backend/app/pipeline/graph.py:137-150`: `query_planner`, `web_worker`, `fact_extractor`, `validate_fact`, `validate_and_split`, `finbert_scorer`, `quality_gate`, `triangulator`, `contradiction_writer`, `signal_scorer`, `narrative_synthesizer`, `watch_list_builder`, `report_assembler`. |
| Are edges wired as specified? | PARTIAL | Linear edges exist at `backend/app/pipeline/graph.py:152-176`. However, architecture requires parallel fan-out for M2/M3 and contradiction writers (`ARCHITECTURE.md:120-137`, `ARCHITECTURE.md:188-196`), while actual code is linear. |
| Is conditional edge implemented? | PARTIAL | Conditional edge mapping is present at `backend/app/pipeline/graph.py:161-169`; router returns `expand_queries` or `proceed` at `backend/app/pipeline/graph.py:123-130`. But `quality_gate()` always returns `{"quality_passed": True}` at `backend/app/pipeline/graph.py:79-82`, so expansion cannot happen in real execution. |
| Is `Send` API used for M2/M3 fan-out? | FAIL | No import or use of `Send` exists in `backend/app/pipeline/graph.py`. Actual path is `query_planner -> web_worker -> fact_extractor` at `backend/app/pipeline/graph.py:153-155`. |
| Is `SqliteSaver` configured correctly? | PARTIAL | `SqliteSaver` is created at `backend/app/pipeline/graph.py:178-181`. Runtime invocation requires `config={"configurable": {"thread_id": ...}}`; invoking without it raises a checkpointer error. `/api/run` is `pass`, so no thread config is provided anywhere (`backend/app/api/report.py:8-10`). |
| Does `PipelineState` match spec? | PARTIAL | `PipelineState` has core fields at `backend/app/pipeline/state.py:17-55`, but lacks separate fields for validated facts / SAFE-verified facts and does not model batch fan-out state. Also all fields are required by default `TypedDict`, while graph nodes use partial states via `state.get()` (`backend/app/pipeline/graph.py:30-40`). |
| Are placeholder nodes clearly marked? | PASS | File header says placeholders at `backend/app/pipeline/graph.py:1-2`; node block says placeholders at `backend/app/pipeline/graph.py:25-26`. |

Chat graph findings:

| Check | Verdict | Requirement vs actual |
|---|---|---|
| Chat nodes registered? | PARTIAL | Required sequence appears at `backend/app/chat/graph.py:44-53`: retrieve, build prompt, analyst chat, validate citations. |
| Self-RAG + FLARE implemented? | FAIL | All chat nodes return `{}` at `backend/app/chat/graph.py:16-37`. No retrieval, no reflection tokens, no sentence-level active retrieval, no retry logic. |
| Chat tools implemented? | FAIL | `ARCHITECTURE.md:1169-1186` specifies `search_facts`, `get_claim`, `get_company_narrative`; none exist in code. |
| `ChatState` matches spec? | PASS | `backend/app/chat/state.py:8-15` matches `ARCHITECTURE.md:1158-1167`. |
| Placeholder nodes clearly marked? | PASS | `backend/app/chat/graph.py:1-2` and `backend/app/chat/graph.py:14` clearly mark placeholder status. |

Runtime verification:
- Graph compiles in the backend venv.
- `pipeline_graph.get_graph()` shows the expected registered node names and linear edges.
- `pipeline_graph.invoke(...)` without configurable `thread_id` fails with: `Checkpointer requires one or more of the following 'configurable' keys: thread_id, checkpoint_ns, checkpoint_id`.
- With a `thread_id`, a mocked run returns only `queries`, `query_expansion_rounds`, and `quality_passed`; downstream outputs remain absent because nodes are stubs.

Verdict: LangGraph wiring is a scaffold, not a complete architecture implementation.

## 4. Hardcoded values audit

| Finding | File / line | Hardcoded value | What it should reference |
|---|---:|---|---|
| Model names are hardcoded. | `backend/app/utils/llm_client.py:18-23` | `anthropic/claude-sonnet-4-5` repeated for agents 1/3/5/6/7/8 | Environment/config values such as `AGENT1_MODEL`, `AGENT3_MODEL`, etc. |
| OpenRouter base URL is hardcoded. | `backend/app/utils/llm_client.py:15` | `https://openrouter.ai/api/v1` | Config/env, especially because architecture says Anthropic SDK directly. |
| Code uses OpenRouter key, spec says Anthropic key. | `backend/app/utils/llm_client.py:39-41`; `idea.md:1152` | `OPENROUTER_API_KEY` vs `ANTHROPIC_API_KEY` | Choose one provider and make docs/env/code consistent. |
| CORS origin default hardcoded. | `backend/main.py:10` | `http://localhost:5173` | `.env.example` has `CORS_ORIGINS`; keep default but document it as dev-only. |
| DB path duplicated. | `backend/app/pipeline/graph.py:21-22`; `backend/app/db/database.py:6` | `data/pulselens.db` built in two places | Single database config module. |
| Alpha Vantage cache path hardcoded. | `backend/app/utils/alphavantage_client.py:8` | `.cache/alphavantage` | Config/env or `backend/data/cache`. |
| Retry delays hardcoded. | `backend/app/utils/llm_client.py:25` | `[1, 2, 4]` | Config constants with comments or env override. |
| Token limits hardcoded. | `backend/app/utils/llm_client.py:56`, `backend/app/utils/llm_client.py:96`, `backend/app/pipeline/agent1_query_planner.py:214` | `4096`, `2048` | Per-agent config constants/env. |
| Quality thresholds hardcoded in config but not role-specific. | `backend/app/config/quality_gates.py:2-4` | `15`, `5`, `2` | Config is okay, but expansion needs separate `MIN_EXPANSION_QUERIES`. |
| Agent 1 target counts hardcoded. | `backend/app/pipeline/agent1_query_planner.py:161` | `"5 to 10"` / `"15 to 20"` | Constants; initial target should match spec 15-25. |
| Coverage retry count hardcoded. | `backend/app/pipeline/agent1_query_planner.py:192` | `range(2)` | Named constant such as `MAX_COVERAGE_RETRIES`. |
| Bright Data result count hardcoded. | `backend/app/utils/brightdata_client.py:10` | `num_results: int = 10` | Config/env; architecture expects batching and coverage tuning. |
| Alpha Vantage lookback hardcoded. | `backend/app/utils/alphavantage_client.py:14` | `days: int = 7` | Config derived from report time window. |
| Tier-1 company IR domains duplicated outside company config. | `backend/app/config/source_tiers.py:6-16` | `ir.nvidia.com`, `ir.amd.com`, etc. | Derive from `COMPANIES[*].ir_url` or central domain config to avoid drift. |
| Source type enum includes `protected` but prompt omits definition. | `backend/app/config/source_tiers.py:45-52`; `backend/app/pipeline/agent1_query_planner.py:96-101` | `protected` is valid in schema prompt enum but undefined in prompt text | Either define `protected` in prompt or exclude it from Agent 1 source types. |
| Frontend mock company universe duplicated. | `frontend/src/modules/sector-select/pages/sector-select-page.tsx:20-29` | 8 company names/tickers and mock scores | Backend company/report API or shared generated types/data. |
| Frontend mock signal weights duplicated. | `frontend/src/modules/sector-select/pages/sector-select-page.tsx:10-18` | weights `0.25`, `0.20`, etc. | Backend `SIGNAL_WEIGHTS` via API or generated config. |
| Frontend hardcoded facts and quotes. | `frontend/src/modules/sector-select/pages/sector-select-page.tsx:31-76` | `fact_c1`, `fact_a3`, mock Reuters/Nvidia quotes | Mock fixture file clearly separated from production UI, or real report API. |

No hardcoded API secrets were found in tracked backend/app code. I intentionally did not read `backend/.env`.

## 5. Schema consistency audit

Python model vs product spec:

| Model / field | Status | Details |
|---|---|---|
| `RawDocument.source_tier` | PARTIAL | Spec requires `Literal[1,2,3,4]` at `idea.md:302`; Python uses `int` at `backend/app/schemas/models.py:43`. |
| `RawDocument.signal_type_hint` | PARTIAL | Spec requires `SignalType` at `idea.md:304`; Python uses `Optional[str]` at `backend/app/schemas/models.py:45`; TS uses `string | null` at `frontend/src/types/index.ts:37`. |
| `FactObject.source_tier` | PARTIAL | Spec requires `Literal[1,2,3,4]` at `idea.md:318`; Python uses `int` at `backend/app/schemas/models.py:56`. |
| `FactObject.sentiment` | PARTIAL | Spec requires `Literal["positive","negative","neutral"]` at `idea.md:320`; Python uses `str` at `backend/app/schemas/models.py:58`; `frontend/src/types/index.ts:50` is stricter. |
| `FactObject.atomic_claims`, `safe_verified` | EXTRA | Python adds SAFE fields at `backend/app/schemas/models.py:61-62`. These are absent from product spec but consistent with `ARCHITECTURE.md` SAFE design. |
| `VerifiedClaim.factscore` | EXTRA | Python adds `factscore` at `backend/app/schemas/models.py:76`; product spec omits it at `idea.md:332-345`, but architecture later requires FActScore usage. |
| `AnomalyFlag.signal_types_involved` | PARTIAL | Spec uses `List[SignalType]` at `idea.md:379-382`; Python uses `List[str]` at `backend/app/schemas/models.py:83`; TS index uses `SignalType[]` at `frontend/src/types/index.ts:75`. |
| `WatchItem.urgency` | PARTIAL | Spec uses `Literal["this_week","next_2_weeks","this_month"]` at `idea.md:390`; Python uses `str` at `backend/app/schemas/models.py:93`; TS index is stricter at `frontend/src/types/index.ts:85`. |
| `CompanyNarrative.momentum_score` | PARTIAL | Spec says `int` at `idea.md:354`; Python uses `float` at `backend/app/schemas/models.py:100`. |
| `CompanyNarrative.competitive_position` | PARTIAL | Spec restricts `"gaining" | "holding" | "losing"` at `idea.md:358`; Python uses `str` at `backend/app/schemas/models.py:104`; TS index is stricter at `frontend/src/types/index.ts:96`. |
| `GroundedBrief.strategic_implication` | PASS in Python / FAIL in `api.ts` | Python uses `str` at `backend/app/schemas/models.py:127`, matching `idea.md:428` and `frontend/src/types/index.ts:119`. `frontend/src/types/api.ts:116` incorrectly uses `CitedStatement[]`. |

Python vs TypeScript:

| Area | Status | Details |
|---|---|---|
| `frontend/src/types/index.ts` | MOSTLY CURRENT | It includes `factscore`, `atomic_claims`, `safe_verified`, and `SearchQuery` (`frontend/src/types/index.ts:40-55`, `frontend/src/types/index.ts:57-71`, `frontend/src/types/index.ts:202-210`). |
| `frontend/src/types/api.ts` | STALE | Missing `FactObject.atomic_claims`, `FactObject.safe_verified`, `VerifiedClaim.factscore`, and `SearchQuery`; has incorrect `GroundedBrief.strategic_implication` type (`frontend/src/types/api.ts:40-68`, `frontend/src/types/api.ts:113-117`). |
| Duplicate TS schema files | FAIL | `frontend/src/types/index.ts` and `frontend/src/types/api.ts` both define backend models and have drifted. |

State consistency:
- `PipelineState` contains main pipeline fields at `backend/app/pipeline/state.py:17-55`, but it does not include separate `validated_facts` or SAFE-only intermediate outputs shown in the architecture data flow (`ARCHITECTURE.md:1245-1251`).
- `PipelineState.query_expansion_rounds` comment says it is incremented by the quality gate (`backend/app/pipeline/state.py:49-51`), but actual graph increments it in `query_planner` (`backend/app/pipeline/graph.py:43-46`).
- `ChatState` matches architecture exactly (`backend/app/chat/state.py:8-15`; `ARCHITECTURE.md:1158-1167`).

Verdict: Schema consistency NEEDS FIX. `index.ts` is close; `api.ts` is stale; Python models need stricter literal types where the spec requires finite enums.

## 6. Agent 1 logic audit

| Check | Verdict | Evidence |
|---|---|---|
| Does `_parse_and_validate()` validate entity against `KNOWN_ENTITIES` / `_VALID_ENTITIES`? | FAIL | `_VALID_ENTITIES` is defined at `backend/app/pipeline/agent1_query_planner.py:34`, but never used. The parser builds `SearchQuery` at `backend/app/pipeline/agent1_query_planner.py:247-255` and checks source/tier/priority/text at `backend/app/pipeline/agent1_query_planner.py:256-270`, but never checks `q.target_entity`. I verified a payload containing `NotACompany` is accepted if all expected companies also have coverage. |
| Does expansion mode use correct min queries? | FAIL | Expansion target is "5 to 10" at `backend/app/pipeline/agent1_query_planner.py:161`, but validation always requires `MIN_QUERIES = 15` at `backend/app/pipeline/agent1_query_planner.py:279-283`. A 10-query expansion fails validation. |
| Is `query_expansion_rounds` incremented in the correct place? | FAIL | Spec says quality gate increments it (`ARCHITECTURE.md:648-654`). Actual graph increments it in `query_planner` at `backend/app/pipeline/graph.py:43-46`. |
| Are generated queries truly non-equivalent? | PARTIAL | Prompt requires non-equivalence at `backend/app/pipeline/agent1_query_planner.py:76-79` and `backend/app/pipeline/agent1_query_planner.py:108-115`, but no post-generation duplicate/similarity validation exists. |
| Is Step-Back output injected into query generation? | PASS | Prompt context at `backend/app/pipeline/agent1_query_planner.py:81-83`; format injection at `backend/app/pipeline/agent1_query_planner.py:198-200`. |
| Can expansion mode ever succeed? | FAIL for intended behavior | If the LLM follows "5 to 10", it always fails the 15-query gate. It can only succeed if the LLM ignores the target and returns at least 15 queries. |
| Does code handle invalid JSON gracefully? | PASS | `LLMClient.call_json()` strips fences and retries JSON parse/API failures at `backend/app/utils/llm_client.py:51-89`; non-list JSON is rejected at `backend/app/pipeline/agent1_query_planner.py:236-238`. |
| Does company coverage validation exist? | PASS, with caveat | Zero-company coverage is detected at `backend/app/pipeline/agent1_query_planner.py:293-296`; retry prompt is built at `backend/app/pipeline/agent1_query_planner.py:191-224`. Caveat: invalid extra entities are still accepted because entity membership is not validated. |

Verdict: Agent 1 is directionally good but not safe enough to feed Agent 2 yet.

## 7. Configuration and environment audit

| Check | Verdict | Evidence |
|---|---|---|
| Does `.env.example` list all required variables from architecture/product spec? | PARTIAL | Product spec requires `ANTHROPIC_API_KEY`, `BRIGHTDATA_API_KEY`, `BRIGHTDATA_SERP_ZONE`, `BRIGHTDATA_SCRAPER_ZONE`, `ALPHA_VANTAGE_API_KEY` at `idea.md:1151-1156`. Current `.env.example` uses `OPENROUTER_API_KEY` instead of `ANTHROPIC_API_KEY` at `backend/.env.example:1-5`. |
| Does requirements include all dependencies? | PARTIAL | `backend/requirements.txt:1-16` includes FastAPI, OpenAI, LangGraph, transformers, torch, diskcache, httpx, dotenv, pytest, aiosqlite. Missing if following architecture literally: `anthropic` SDK and `sentence-transformers` for chat embeddings. |
| Single source of truth for company list? | PARTIAL | Backend company list is centralized in `backend/app/config/companies.py:16-81`. But company IR domains are duplicated in `backend/app/config/source_tiers.py:6-16`, and frontend mock company data is duplicated at `frontend/src/modules/sector-select/pages/sector-select-page.tsx:20-29`. |
| Single source of truth for signal weights? | PARTIAL | Backend weights are centralized at `backend/app/config/signal_types.py:4-12`, but frontend mock weights duplicate them at `frontend/src/modules/sector-select/pages/sector-select-page.tsx:10-18`. |
| Bright Data zone names configurable? | PARTIAL | `.env.example` has `BRIGHTDATA_SERP_ZONE` and `BRIGHTDATA_SCRAPER_ZONE` at `backend/.env.example:2-4`. The client constructor accepts zones at `backend/app/utils/brightdata_client.py:7`, but the implementation is `pass`; there is no configured routing yet. |
| Provider consistency? | FAIL | `ARCHITECTURE.md:103-105` says Anthropic SDK directly. Code uses OpenAI-compatible OpenRouter at `backend/app/utils/llm_client.py:11-15` and requires `OPENROUTER_API_KEY` at `backend/app/utils/llm_client.py:39-41`. |

Verdict: Configuration NEEDS FIX before Agent 2, mainly provider/env consistency and removing duplicated frontend/config data.

## 8. Issues found -- prioritized

### Critical (blocks pipeline from working)

1. `backend/app/api/report.py:8-15` - `/api/run` and `/api/report/{report_id}` are `pass`.
   - Spec: API must trigger full pipeline and return reports (`idea.md:1197-1200`).
   - Fix: implement graph invocation with a `thread_id`, persist report, and implement report retrieval.

2. `backend/app/pipeline/graph.py:49-118` - every node after Agent 1 is a placeholder returning `{}`.
   - Spec: M2-M6 must collect docs, extract facts, validate, score, synthesize, and assemble report.
   - Fix: wire real node functions incrementally, starting with M2.

3. `backend/app/api/chat.py:10-12` and `backend/app/chat/graph.py:16-37` - chat API and graph are stubs.
   - Spec: chat must retrieve facts, build prompt, generate grounded answer, validate citations (`ARCHITECTURE.md:1188-1213`).
   - Fix: implement DB-backed retrieval and citation validation before exposing `/api/chat`.

4. `backend/app/api/stock.py:9-11` and `backend/app/utils/alphavantage_client.py:7-15` - stock endpoint and client are stubs.
   - Spec: Alpha Vantage price context is required for stock context layer (`idea.md:1014-1062`).
   - Fix: implement quote/history fetching with cache and quota handling.

5. `backend/app/pipeline/graph.py:79-82` - quality gate always passes.
   - Spec: fail if facts < 50 or signal coverage < 4, then loop (`ARCHITECTURE.md:648-654`).
   - Fix: implement real quality gate from `scored_facts`.

6. `backend/app/pipeline/agent1_query_planner.py:161` plus `backend/app/pipeline/agent1_query_planner.py:279-283` - expansion mode cannot satisfy its own validator.
   - Spec: expansion should generate 5-10 gap-filling queries (`ARCHITECTURE.md:659-661`).
   - Fix: add separate `MIN_EXPANSION_QUERIES` and pass mode into validation.

7. `backend/app/pipeline/graph.py:178-181` - checkpointer requires `thread_id`, but no API invocation supplies it.
   - Spec: SQLite checkpointing should allow resume after failure (`ARCHITECTURE.md:97`).
   - Fix: `/api/run` must call graph with `config={"configurable": {"thread_id": report_run_id}}`.

8. Tests collect zero items.
   - Evidence: `backend/.venv/bin/python -m pytest backend/tests` collected 0 tests.
   - Spec: build order requires tests per module (`idea.md:1171-1195`).
   - Fix: add real `test_...` functions with assertions.

### High (produces wrong results)

1. `backend/app/pipeline/agent1_query_planner.py:34`, `backend/app/pipeline/agent1_query_planner.py:247-270` - invalid entities are accepted.
   - Spec: `target_entity` must be one of tracked companies or `market`.
   - Fix: check `q.target_entity in _VALID_ENTITIES` and reject otherwise.

2. `backend/app/pipeline/graph.py:43-46` - `query_expansion_rounds` increments in Agent 1 node.
   - Spec: quality gate owns loop state (`ARCHITECTURE.md:648-654`).
   - Fix: remove increment from `query_planner`; update in quality gate only when routing to expansion.

3. `backend/app/pipeline/agent1_query_planner.py:73-127` - code labels itself Multi-HyDE but only performs query fan-out.
   - Paper: Multi-HyDE requires hypothetical documents, embeddings, retrieval, and reranking (`/tmp/pulselens_multi_hyde_audit.txt:361-374`).
   - Fix: rename to Multi-HyDE-inspired until full retrieval is implemented.

4. `backend/app/pipeline/graph.py:153-155` - M2/M3 are linear, not parallel.
   - Spec: `Send` API fan-out for M2/M3 (`ARCHITECTURE.md:96`, `ARCHITECTURE.md:120-137`).
   - Fix: add conditional edge/router returning `Send` objects for query/document batches.

5. `backend/app/utils/llm_client.py:11-23` - architecture says Anthropic SDK directly, code uses OpenRouter/OpenAI-compatible client.
   - Spec: `ARCHITECTURE.md:103-105`.
   - Fix: either switch to Anthropic SDK or update architecture/env docs honestly.

6. `frontend/src/types/api.ts:40-117` - stale TypeScript schema can cause frontend/backend mismatch.
   - Spec: TS types must mirror backend schemas.
   - Fix: delete duplicate `api.ts` model definitions or generate TS from Pydantic/OpenAPI.

### Medium (works but deviates from spec)

1. `backend/app/pipeline/agent1_query_planner.py:49-71` - Step-Back prompt is free-form and lacks few-shot examples.
   - Paper: few-shot examples are used for Step-Back question generation (`/tmp/pulselens_step_back_audit.txt:1115-1126`).
   - Fix: request structured JSON/sections and include 1-2 examples.

2. `backend/app/pipeline/agent1_query_planner.py:108-115` - non-equivalence is prompt-only.
   - Spec: Multi-HyDE requires non-equivalent query fan-out.
   - Fix: validate duplicate `(entity, signal_type, source_type)` triples and near-duplicate query text.

3. `backend/app/config/quality_gates.py:2-3` - only minimum queries and minimum signal types are validated.
   - Spec intent: meaningful coverage across 8 companies and 7 signal types.
   - Fix: add min company coverage, min queries per high-weight signal, and max duplicate source/entity constraints.

4. `backend/app/config/source_tiers.py:6-16` duplicates company IR domains.
   - Spec: company metadata belongs in company config.
   - Fix: derive tier-1 IR domains from `COMPANIES`.

5. `backend/app/schemas/models.py:43`, `backend/app/schemas/models.py:56`, `backend/app/schemas/models.py:58`, `backend/app/schemas/models.py:83`, `backend/app/schemas/models.py:93`, `backend/app/schemas/models.py:104` - Python schemas are less strict than spec/TS.
   - Fix: use `Literal`/`SignalType` where specified.

6. `backend/app/utils/llm_client.py:18-23` - model config is hardcoded.
   - Fix: load per-agent model names from env/config.

7. `backend/app/config/source_tiers.py:45-52` and `backend/app/pipeline/agent1_query_planner.py:96-101` - `protected` source type can appear in enum but is not defined in prompt.
   - Fix: define it or remove it from Agent 1 allowed source types.

8. `frontend/src/modules/sector-select/pages/sector-select-page.tsx:6-85` - frontend has hardcoded mock market data and signal weights.
   - Fix: isolate as fixtures or replace with API-loaded report data.

### Low (style/naming/docs issues)

1. `PULSELENS_PROJECT.md` is referenced by docs/user request but absent; `idea.md` appears to be that document.
   - Fix: rename `idea.md` or add a pointer file.

2. `papers/MULTI_HYDE.pdf` requested but repo uses `papers/MULTI-HYDE.pdf`.
   - Fix: normalize filename or document canonical paper path.

3. `backend/app/pipeline/m1_query_intelligence.py:1-11` remains as an old stub while `agent1_query_planner.py` is the real Agent 1 implementation.
   - Fix: remove or make it a wrapper to avoid confusion.

4. `backend/requirements.txt:8` includes `langchain-core` even though architecture says no LangChain abstractions.
   - Fix: remove until needed or document why it is required.

## 9. Overall verdict

| Section | Verdict |
|---|---|
| 1. Step-Back Prompting verification | PASS with improvements needed |
| 2. Multi-HyDE verification | NEEDS FIX |
| 3. LangGraph architecture audit | NEEDS FIX |
| 4. Hardcoded values audit | NEEDS FIX |
| 5. Schema consistency audit | NEEDS FIX |
| 6. Agent 1 logic audit | NEEDS FIX |
| 7. Configuration and environment audit | NEEDS FIX |
| 8. Issues found -- prioritized | NEEDS FIX |

Ready to proceed to Agent 2 build: No.

Why: Agent 1 has a solid conceptual direction, but its expansion validation and entity validation need fixing before it becomes the foundation for web collection. More importantly, the graph quality gate is fake, API entrypoints are stubs, and LangGraph fan-out is not implemented. Building Agent 2 on this wiring will hide defects rather than reveal them.

Top 3 fixes before moving forward:
1. Fix Agent 1 validation: entity validation, expansion min query count, per-signal/per-company coverage checks, and non-equivalence checks.
2. Implement real quality-gate ownership of `query_expansion_rounds` and remove the increment from `query_planner`.
3. Make the architecture honest: either rename Agent 1 to "Multi-HyDE-inspired query fan-out" or implement hypothetical documents, embeddings, retrieval, and reranking.

## 10. Prompt quality and coverage audit

### 10a. Company coverage completeness

Tracked companies:
- All 8 companies are present in `backend/app/config/companies.py:16-81`: Nvidia, AMD, Intel, Broadcom, Supermicro, Dell, HPE, Micron.
- Each has `name`, `ticker`, `domain`, `ir_url`, `careers_url`, and `known_aliases` (`backend/app/config/companies.py:17-80`).

Agent 1 coverage:
- The query generation prompt explicitly requires at least 1 query per company at `backend/app/pipeline/agent1_query_planner.py:85-87` and `backend/app/pipeline/agent1_query_planner.py:113`.
- Post-generation zero-coverage validation exists at `backend/app/pipeline/agent1_query_planner.py:293-296`.
- A retry prompt for missing companies exists at `backend/app/pipeline/agent1_query_planner.py:191-224`.

Mental trace:
- It is possible for the LLM to return only 3-4 companies.
- If `expected_companies` contains all 8, that output will not be accepted; the planner retries once and then raises `_CoverageValidationError`.
- Bug that remains: it can accept invalid extra entities like `NotACompany` as long as all expected companies have at least one query.

Verdict: Company coverage is mostly covered, but entity validation is still broken.

### 10b. Query quantity and diversity

Current behavior:
- Initial target is 15-20 queries (`backend/app/pipeline/agent1_query_planner.py:161`), while product spec says 15-25 (`idea.md:471`).
- Expansion target is 5-10 queries (`backend/app/pipeline/agent1_query_planner.py:161`), but validator requires 15 (`backend/app/pipeline/agent1_query_planner.py:279-283`).

Coverage adequacy:
- The theoretical matrix is 8 companies x 7 signals = 56 cells.
- 15-25 queries is not enough to cover every cell. It can be enough for an MVP if it prioritizes high-weight signals and then uses quality-gate expansion after evidence collection.
- Current validation does not enforce at least 2 queries per signal. It only enforces at least 5 signal types (`backend/app/config/quality_gates.py:2-3`).
- There is no post-generation mechanism to ensure high-weight signals get more queries. The prompt displays weights via `_SIGNAL_TYPES_BLOCK` at `backend/app/pipeline/agent1_query_planner.py:39-42` and priority guidance at `backend/app/pipeline/agent1_query_planner.py:103-106`, but validation does not check weight-proportional allocation.

Verdict: Query diversity NEEDS IMPROVEMENT. Prompt says the right thing; validation does not enforce it.

### 10c. Step-Back prompt quality

Prompt location: `backend/app/pipeline/agent1_query_planner.py:49-71`

Checks:
- Specific enough: Yes. It asks about the market evidence landscape under acceleration, deceleration, and stress.
- Asks each signal type separately: Yes, `backend/app/pipeline/agent1_query_planner.py:59-65`.
- Positive and negative evidence: Yes, `backend/app/pipeline/agent1_query_planner.py:60-61`.
- Reliable source types: Yes, `backend/app/pipeline/agent1_query_planner.py:62`.
- Structured output: No. It asks for plain text at `backend/app/pipeline/agent1_query_planner.py:70`.
- Examples: No.

Rating: NEEDS IMPROVEMENT.

Required upgrade:
- Ask for JSON or numbered sections keyed by signal type.
- Include one good example for a signal type.
- Include "do not generate search queries in this step" to prevent leakage into Phase 2.

### 10d. Multi-HyDE query generation prompt quality

Prompt location: `backend/app/pipeline/agent1_query_planner.py:73-128`

Checks:
- Receives Step-Back output: Yes, `backend/app/pipeline/agent1_query_planner.py:81-83`.
- Specifies 3 decomposition dimensions: Yes, `backend/app/pipeline/agent1_query_planner.py:85-88`.
- Defines non-equivalent: Partially. It says different source type, angle, or company at `backend/app/pipeline/agent1_query_planner.py:76-79`.
- Includes good vs bad examples: No.
- Specifies output JSON schema: Yes, `backend/app/pipeline/agent1_query_planner.py:117-127`.
- Time anchors: Yes, it includes time window/current date at `backend/app/pipeline/agent1_query_planner.py:90-93`, but it does not explicitly require every query text to include a date/window.
- Domain-specific search operators: No. It does not instruct use of `site:sec.gov`, `site:ir.nvidia.com`, `site:jobs.dell.com`, etc.
- Edge cases: Partial. It handles low-coverage company retry but not no-data/ambiguous-company cases.

Rating: NEEDS IMPROVEMENT.

Required upgrade:
- Add concrete examples of good and bad queries.
- Require time anchors in every query.
- Use company metadata (`ir_url`, `careers_url`, `domain`) to suggest `site:` operators.
- Add post-generation validators for duplicate triples, invalid entity, per-signal minimums, and high-weight allocation.

### 10e. Extraction prompt quality (for Agent 3 -- if implemented)

Agent 3 is not implemented.

Evidence:
- `backend/app/pipeline/m3_fact_extraction.py:9-14` has `extract_facts()` and `validate_fact()` as `pass`.
- No extraction prompt exists in code.

Rating: NOT YET IMPLEMENTED.

### 10f. Prompt robustness checklist

| Prompt | Has examples? | Has constraints? | Has output schema? | Handles edge cases? | Rating |
|---|---|---|---|---|---|
| Step-Back | No | Yes | No | Partial | NEEDS IMPROVEMENT |
| Query Gen | No | Yes | Yes | Partial | NEEDS IMPROVEMENT |
| Extraction | No | No | No | No | NOT YET IMPLEMENTED |
| Contradiction | No | No | No | No | NOT YET IMPLEMENTED |
| Narrative | No | No | No | No | NOT YET IMPLEMENTED |
| Watch List | No | No | No | No | NOT YET IMPLEMENTED |
| Chat | No | No | No | No | NOT YET IMPLEMENTED |

Explanations:
- Step-Back lacks examples and structured output. This matters because free-form abstractions are harder to validate and less stable when injected into the query prompt.
- Query Gen lacks examples and domain-specific search operator instructions. This matters because the LLM may generate generic news searches instead of high-signal SEC/IR/job/pricing searches.
- Extraction is not implemented, so there is no RASG enforcement, no good/bad examples, no verbatim quote instruction, and no claim-length enforcement.
- Contradiction, Narrative, Watch List, and Chat prompts exist only in `ARCHITECTURE.md` / `idea.md`, not in executable code. They cannot be considered implemented.

Final prompt verdict: Agent 1 prompts are promising but not production-ready. All downstream prompts are absent from code.
