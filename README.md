# 🔍 PulseLens

<h3 align="center">Evidence-Backed Market Intelligence for Fast-Moving Sectors</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/TypeScript-5.6-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/LangGraph-1.0-FF6B35?style=flat-square" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License"/>
</p>

<p align="center">
  PulseLens turns live web signals into source-backed facts, market signals, company lenses,<br/>
  pricing intelligence, risk alerts, and grounded chat.<br/>
  Every claim traces back to an exact source quote — no black-box scores, no unattributed summaries.
</p>

<p align="center">
  <strong>Current demo market:</strong> US AI Hardware / Semiconductor &nbsp;·&nbsp;
  <strong>Tracked companies:</strong> Nvidia · AMD · Supermicro
</p>

<p align="center">
  <a href="https://pulse-lens.vercel.app">🚀 Try Live Demo</a> &nbsp;·&nbsp;
  <a href="https://github.com/vquclinh/PulseLens/issues">🐛 Report Bug</a> &nbsp;·&nbsp;
  <a href="https://github.com/vquclinh/PulseLens/issues">✨ Request Feature</a>
</p>

> **Research demo:** PulseLens is not production-ready and is not intended for investment or trading decisions.

---

## 📚 Table of Contents

- [🎯 The Market Intelligence Gap](#-the-market-intelligence-gap)
- [✨ Key Features](#-key-features)
- [🏗️ Architecture](#️-architecture)
- [📁 Repository Structure](#-repository-structure)
- [🚀 Local Setup](#-local-setup)
- [⚙️ Environment Variables](#️-environment-variables)
- [⚠️ Demo Limitations](#️-demo-limitations)
- [🗺️ Roadmap](#️-roadmap)
- [🙏 Acknowledgements](#-acknowledgements)
- [📄 License](#-license)

---

## 🎯 The Market Intelligence Gap

Financial analysts spend most of their time locating, reading, and cross-checking sources before they can form a coherent signal. Existing tools either surface raw headlines (high noise) or output black-box scores with no traceable evidence chain — leaving analysts unable to audit or challenge the output.

PulseLens approaches this differently:

- Every fact is tied to a verbatim source quote and a canonical URL
- Claims are triangulated across multiple independent sources before scoring
- The full pipeline audit trail — queries, document counts, quality gates, expansion rounds — is exposed in the UI
- The grounded chat assistant cites specific facts and refuses to fabricate when evidence is insufficient

---

## ✨ Key Features

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

## 🏗️ Architecture

PulseLens is structured as a full-stack market intelligence system: live web collection, agentic processing, source-backed fact storage, FastAPI endpoints, and a React analyst workspace.

![PulseLens Architecture](frontend/src/assets/architecture.png)

---

## 📁 Repository Structure

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

## 🚀 Local Setup

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

## ⚙️ Environment Variables

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

## ⚠️ Demo Limitations

This is a research-grade demo, not a production system. Known limitations:

- **Single demo market:** Only US AI Hardware (Nvidia, AMD, Supermicro) is covered. Multi-market support is planned.
- **In-memory chat history:** Chat session history is stored in the browser only. Refreshing the page clears the conversation.
- **Source URL quality:** The pipeline relies on Bright Data's web unlocker. Some source URLs may be inaccessible or low-quality depending on site structure and rate limits.
- **No real-time data:** The pipeline must be run manually (or triggered via the UI). There is no scheduled refresh.
- **Hiring momentum coverage:** The `hiring_momentum` signal type requires dedicated job-board collection that is not yet wired into the demo scope. Expect zero hiring facts.
- **Backend is frozen for the current sprint:** The backend codebase is intentionally frozen at Sprint 8. All active development is on the frontend.
- **Not for financial decisions:** PulseLens is a research prototype. Do not use its output for investment or trading decisions.

---

## 🙏 Acknowledgements

PulseLens is built on top of methods from 11 peer-reviewed research papers. We sincerely thank all the authors for their outstanding contributions — their work made it possible to design a system where every architectural decision is grounded in published research.

| Method | Paper | Venue | Applied in |
|---|---|---|---|
| **[Step-Back Prompting](https://arxiv.org/abs/2310.06117)** | *Take a Step Back: Evoking Reasoning via Abstraction in LLMs* | Google DeepMind, 2023 | Agent 1 — Query Planner |
| **[Multi-HyDE](https://arxiv.org/abs/2509.16369)** | *Enhancing Financial RAG with Agentic AI and Multi-HyDE: A Novel Approach to Knowledge Retrieval and Hallucination Reduction* | EMNLP 2025, IIT Madras | Agent 1 — Query Planner |
| **[RASG](https://arxiv.org/abs/2405.20245)** | *Retrieval Augmented Structured Generation: Business Document Information Extraction As Tool Use* | 2024 | Agent 3 — Fact Extractor |
| **[SAFE](https://arxiv.org/abs/2403.18802)** | *Long-form Factuality in Large Language Models* | Google DeepMind, 2024 | Node — SAFE Atomic Verification |
| **[FinBERT](https://arxiv.org/abs/1908.10063)** | *FinBERT: Financial Sentiment Analysis with Pre-trained Language Models* | HuggingFace, 2020 | Agent 4 — Sentiment Scorer |
| **[ClaimCheck](https://aclanthology.org/2025.knowledgenlp-1.26/)** | *ClaimCheck: Automatic Fact-Checking of Textual Claims using Web Evidence* | ACL / KnowledgeNLP 2025 | Node — M4 Triangulator |
| **[MiniCheck](https://aclanthology.org/2024.emnlp-main.499/)** | *MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents* | EMNLP 2024 | Node — M4 Triangulator |
| **[FActScore](https://aclanthology.org/2023.emnlp-main.741/)** | *FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation* | EMNLP 2023 | Node — M4 Triangulator & M5 Scorer |
| **[STORM](https://aclanthology.org/2024.naacl-long.347/)** | *Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models* | NAACL 2024, Stanford | Agent 6 — Narrative Synthesizer |
| **[Self-RAG](https://openreview.net/pdf?id=hSyW5go0v8)** | *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection* | NeurIPS 2023 | Agent 8 — Analyst Chat |
| **[FLARE](https://aclanthology.org/2023.emnlp-main.495/)** | *Active Retrieval Augmented Generation* | EMNLP 2023 | Agent 8 — Analyst Chat |

---

## 🗺️ Roadmap

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

## 📄 License

This project is licensed under the [MIT License](LICENSE).
