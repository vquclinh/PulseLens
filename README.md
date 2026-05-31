# PulseLens

> Evidence-backed market intelligence for fast-moving sectors.

PulseLens is an analyst workspace that turns live web signals into source-backed facts, market signals, company lenses, pricing intelligence, risk alerts, and grounded chat. Every claim traces back to an exact source quote — no black-box scores, no unattributed summaries.

**Current demo market:** US AI Hardware / Semiconductor  
**Tracked companies:** Nvidia · AMD · Supermicro

> **Research demo:** PulseLens is not production-ready and is not intended for investment or trading decisions.

---

## The Market Intelligence Gap

Financial analysts spend most of their time locating, reading, and cross-checking sources before they can form a coherent signal. Existing tools either surface raw headlines (high noise) or output black-box scores with no traceable evidence chain — leaving analysts unable to audit or challenge the output.

PulseLens approaches this differently:

- Every fact is tied to a verbatim source quote and a canonical URL
- Claims are triangulated across multiple independent sources before scoring
- The full pipeline audit trail — queries, document counts, quality gates, expansion rounds — is exposed in the UI
- The grounded chat assistant cites specific facts and refuses to fabricate when evidence is insufficient

---

## Core Infrastructure

| Layer | Tools |
|---|---|
| Web access | **Bright Data** — SERP API, Web Unlocker, Browser API |
| Agent orchestration | LangGraph multi-agent pipeline |
| LLM reasoning | OpenRouter-hosted models (Google Gemini 2.5 Flash by default) |
| Sentiment scoring | FinBERT (`ProsusAI/finbert`) |
| Backend API | FastAPI + Uvicorn |
| Frontend | React 18, Vite 6, TypeScript 5.6, TailwindCSS 4 |
| Storage | Supabase / Postgres with SQLite fallback |

---

## Key Features

| Feature | Description |
|---|---|
| **Intelligence Workspace** | Tabbed analysis workspace: Overview, Evidence, Pricing, Signals, Companies, Pipeline |
| **Evidence Explorer** | Browse and filter all extracted facts by signal type, confidence, and company |
| **Pricing Intelligence** | Dedicated view for pricing_pressure signals across tracked companies |
| **Signal Radar** | Cross-company signal coverage heatmap across all 7 signal types |
| **Company Lens** | Per-company narrative, momentum label, and tier badge |
| **Trust and Pipeline** | Full pipeline audit log: quality gate status, fact counts, source counts, expansion rounds |
| **Grounded Chat** | RAG analyst chat (Agent 8) backed by retrieved facts; every answer cites fact IDs |
| **Context Attachments** | Chat deeplinks accept URL params (`?context=...`) to pre-attach a watch item, risk alert, company, signal, or fact as chat context |
| **SAFE-style Verification** | Every extracted fact is checked for atomic claim validity before entering the quality gate |
| **Postgres / Supabase + SQLite** | Default SQLite; switch to Postgres/Supabase at runtime via `DATABASE_BACKEND=postgres` |
| **Bright Data Collection** | Agent 2 uses Bright Data's web unlocker to collect IR pages, SEC filings, pricing pages, and news |

---

## Architecture

PulseLens is structured as a full-stack market intelligence system: live web collection, agentic processing, source-backed fact storage, FastAPI endpoints, and a React analyst workspace.

![PulseLens Architecture](frontend/src/assets/architecture.png)

---

## Repository Structure

```
PulseLens/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (report, chat, stock)
│   │   ├── chat/         # Agent 8 chat graph + state
│   │   ├── config/       # Demo scope config
│   │   ├── db/           # SQLite + Postgres adapters
│   │   ├── pipeline/     # LangGraph nodes + graph
│   │   ├── schemas/      # Pydantic models
│   │   └── utils/        # LLM client, helpers
│   ├── data/             # pulselens.db (SQLite, git-tracked binary)
│   ├── scripts/          # CLI audit and migration scripts
│   ├── tests/            # Zero-cost static tests (pipeline/)
│   ├── main.py           # FastAPI app entry point
│   ├── run_pipeline.py   # CLI pipeline runner
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── hooks/        # useChat, useReport
│   │   ├── lib/          # api-client.ts
│   │   ├── modules/      # chat/, workspace/ (overview, evidence, pricing, signals, companies, pipeline)
│   │   ├── shared/       # Navbar, Badge, SentimentBadge, Sparkline, FactIdChip
│   │   ├── store/        # dashboard-store.ts (Zustand)
│   │   ├── types/        # index.ts mirrors backend Pydantic models
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── docs/
├── papers/               # Research papers referenced by the pipeline
├── pipeline_audit_artifacts/
├── ARCHITECTURE.md
├── CLAUDE.md             # Authoritative codebase guide for contributors
└── README.md
```

---

## Local Setup

### Prerequisites

- Python (the project was developed against Python 3.14; Python 3.11+ should work)
- Node.js 20+
- An [OpenRouter](https://openrouter.ai) API key (required for LLM calls)
- A [Bright Data](https://brightdata.com) API key (required to run the live pipeline)

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in your API keys (see Environment Variables below)

# Start the API server
uvicorn main:app --reload
# Server listens on http://localhost:8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server (proxies /api to localhost:8000)
npm run dev
# Opens at http://localhost:5173
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in the values. **Never commit `.env`.**

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | LLM calls for all agents (routed via OpenRouter) |
| `BRIGHTDATA_API_KEY` | Yes (pipeline) | Web collection — Bright Data unlocker |
| `ALPHA_VANTAGE_API_KEY` | Optional | Stock price context for `/api/stock/{ticker}` |
| `PULSELENS_DEMO_SCOPE` | Optional | `true` = Track 2 demo slice (Nvidia/AMD/Supermicro). Default: `true` |
| `QUALITY_MIN_FACTS` | Optional | Minimum facts to pass quality gate. **Do not lower below 50.** |
| `QUALITY_MIN_SOURCE_COUNT` | Optional | Minimum source domains to pass quality gate. **Do not lower below 15.** |
| `AGENT1_MODEL` | Optional | LLM model for Agent 1 query planner. Default: `google/gemini-2.5-flash` |
| `FINBERT_MODEL` | Optional | FinBERT model for Agent 4 sentiment scoring. Default: `ProsusAI/finbert` |
| `DATABASE_BACKEND` | Optional | `sqlite` (default) or `postgres` |
| `DATABASE_URL` | Postgres only | `postgresql://user:password@host:port/dbname` |
| `CORS_ORIGINS` | Optional | Comma-separated allowed origins. Default: `http://localhost:5173` |

---

## API Overview

All endpoints are prefixed with `/api`. The Vite dev proxy forwards requests from port 5173 to port 8000.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/reports/latest` | Returns the most recent `report_id` stored in the database |
| `GET` | `/api/report/{report_id}` | Returns the full `MarketPulseReport` JSON for a given report |
| `GET` | `/api/report/{report_id}/facts` | Returns the list of `FactObject[]` for a given report |
| `POST` | `/api/run` | Triggers the LangGraph pipeline asynchronously; returns a new `report_id` |
| `POST` | `/api/chat` | Sends a message to the RAG analyst chat; returns `response`, `cited_facts`, `session_id` |
| `GET` | `/api/stock/{ticker}` | Returns cached stock price context from Alpha Vantage (4-hour cache) |

**Chat request** accepts an optional `context_attachment` field with `attachment_type` values: `watch_item`, `risk_alert`, `fact`, `company`, `signal`, `pricing`, `report`.

---

## Demo Limitations

This is a research-grade demo, not a production system. Known limitations:

- **Single demo market:** Only US AI Hardware (Nvidia, AMD, Supermicro) is covered. Multi-market support is planned.
- **In-memory chat history:** Chat session history is stored in the browser only. Refreshing the page clears the conversation.
- **Source URL quality:** The pipeline relies on Bright Data's web unlocker. Some source URLs may be inaccessible or low-quality depending on site structure and rate limits.
- **No real-time data:** The pipeline must be run manually (or triggered via the UI). There is no scheduled refresh.
- **Hiring momentum coverage:** The `hiring_momentum` signal type requires dedicated job-board collection that is not yet wired into the demo scope. Expect zero hiring facts.
- **Backend is frozen for the current sprint:** The backend codebase is intentionally frozen at Sprint 8. All active development is on the frontend.
- **Not for financial decisions:** PulseLens is a research prototype. Do not use its output for investment or trading decisions.

---

## Roadmap

- Multi-market support (US Fintech, European Energy, etc.)
- Persistent chat history stored in the database
- Canonical source URL normalization and deduplication
- Scheduled pipeline refresh (cron-triggered)
- Streaming chat responses
- User authentication and per-user report history
- Hiring momentum signal via job-board integration
- Export report to PDF / structured JSON
- Configurable company watchlist

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Contributing

Contributions are welcome. Before opening a pull request:

1. Read `CLAUDE.md` — it is the authoritative guide for this codebase and documents hard constraints (quality gate thresholds, signal balance constants) that must not be changed.
2. All frontend work should use `src/lib/api-client.ts` for API calls. Do not add new fetch functions to the legacy `src/types/api.ts`.
3. Backend is currently frozen. Frontend-only changes are the active focus.
4. Run the zero-cost static tests before submitting: `python tests/pipeline/test_agent1_expansion_stability.py` and `python tests/pipeline/test_agent1_signal_balance.py`.

For questions, open an issue.
