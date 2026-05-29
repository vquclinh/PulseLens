# README and LICENSE Creation Report

## Files Created

| File | Path | Status |
|---|---|---|
| `README.md` | `/mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens/README.md` | Written (overwrote stub) |
| `LICENSE` | `/mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens/LICENSE` | Created new |

---

## README.md

### Sections included (in order)

1. **Title and tagline** — `# PulseLens` with one-line value proposition
2. **What is PulseLens** — product overview; current demo scope (US AI Hardware: Nvidia, AMD, Supermicro); explicit not-production disclaimer
3. **Why it matters** — problem statement (analyst evidence-chain overhead); value proposition (traceable claims, peer-reviewed grounding)
4. **Key features** — 11-row table covering: Intelligence Workspace, Evidence Explorer, Pricing Intelligence, Signal Radar, Company Lens, Trust and Pipeline, Grounded Chat, Context Attachments, SAFE-style verification, Postgres/Supabase + SQLite, Bright Data collection
5. **Architecture** — ASCII text diagram showing Frontend → FastAPI → LangGraph pipeline + chat graph → storage; brief description of each layer
6. **Repository structure** — concise annotated tree (backend/, frontend/, docs/, papers/, pipeline_audit_artifacts/, top-level files)
7. **Local setup** — prerequisites list; backend (venv, pip install, .env, uvicorn); frontend (npm install, npm run dev)
8. **Environment variables** — table of all vars from .env.example findings; placeholders only, no real values; warnings on QUALITY_MIN_FACTS and QUALITY_MIN_SOURCE_COUNT
9. **Running the pipeline** — cost and time warning; four script commands (run_pipeline.py, demo_track2_ai_hardware_audit.py, check_latest_report.py, evidence_quality_audit.py)
10. **Checks and builds** — frontend (npm run build, npm run preview); backend (two zero-cost static test scripts, py_compile note)
11. **API overview** — 6-row table covering all endpoints found: GET /api/reports/latest, GET /api/report/{id}, GET /api/report/{id}/facts, POST /api/run, POST /api/chat, GET /api/stock/{ticker}; note on context_attachment types
12. **Demo limitations** — 7 honest items: single demo market, in-memory chat, source URL quality, no real-time data, zero hiring_momentum facts, frozen backend, financial disclaimer
13. **Roadmap** — 9 items (multi-market, persistent chat, canonical URLs, scheduled refresh, streaming, auth, hiring signal, PDF export, configurable watchlist)
14. **Screenshots** — placeholder section
15. **License** — MIT link
16. **Contributing** — 4-point guide referencing CLAUDE.md, api-client.ts constraint, frozen backend, zero-cost tests

### Constraints verified

- Project name `PulseLens` preserved exactly throughout
- No raw report IDs included
- No API keys or secret values; all values are placeholders
- No production-readiness claim made; explicit "research-grade demo" and "not for financial decisions" disclaimers
- All features and scripts sourced from the provided findings only; nothing invented
- Markdown formatting consistent throughout (headers, tables, code blocks)

---

## LICENSE

- Type: MIT License
- Copyright holder: `Copyright (c) 2026 Linh Võ Quốc`
- Standard MIT boilerplate text; no modifications

---

## Source basis

All content derives exclusively from the FINDINGS provided. No features, endpoints, scripts, or environment variables were invented beyond what was documented in the ROOT, BACKEND, FRONTEND, SCRIPTS, and DOCS/REPORTS finding sections.
