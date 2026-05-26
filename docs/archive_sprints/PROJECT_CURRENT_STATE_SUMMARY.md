# PulseLens — Current State Summary

**Date:** 2026-05-26
**Sprint:** 4 complete, Sprint 5 not started
**Authoritative report:** `report_3dfb4b94068b` (PARTIAL_PASS, pulse_score=57.0)

---

## What PulseLens Does

PulseLens is an AI-powered investment signal intelligence platform that monitors a curated set of AI-hardware companies (Nvidia, AMD, Supermicro in demo scope; 8 companies in full mode) and produces structured, evidence-backed market intelligence reports. It aggregates evidence from public web sources, validates signal quality through a multi-stage AI pipeline, and presents findings in a dashboard with narrative synthesis and actionable watch-list items.

---

## Demo Scope

| Parameter | Value |
|---|---|
| Companies | Nvidia, AMD, Supermicro |
| Signal types | investor_signal, product_launch, pricing_pressure, supplier_risk, strategic_messaging, hiring_momentum |
| Mode | `demo_scope_enabled = True` in `backend/app/config/demo_scope.py` |
| Full 8-company mode | Available but NOT enabled — reserved for post-Sprint-5 stability |

---

## Architecture and Pipeline Sequence

```
BrightData SERP + Scraper
        ↓
Agent 1: query_planner          — generates 32 structured queries (round 0)
        ↓
Agent 2: web_worker             — fetches and accepts documents (BrightData)
        ↓
Agent 3: fact_extractor         — extracts typed FactObjects per document
        ↓
Gate 1: validate_fact           — 6 deterministic checks (verbatim/length/conf/entity/nav_meta/pricing_sanity)
        ↓
Gate 2: SAFE verification       — atomic decomposition + source support ratio (arXiv:2403.18802)
        ↓
Agent 4: finbert_scorer         — ProsusAI/finbert sentiment scoring
        ↓
quality_gate                    — threshold check (facts≥50, sources≥15, signals≥4)
     ↙ FAIL_EXPAND             ↘ PASS/PARTIAL_PASS
Agent 1 round 1 (expand)       → proceed
        ↓
Agent 5: triangulator           — cross-source corroboration (≥2 sources = verified)
        ↓
Agent 6: contradiction_writer   — flags contradicted signals
        ↓
Agent 7: signal_scorer          — per-type scores + pulse_score + narrative
        ↓
Agent 8: company_narratives     — per-company NLP summaries
        ↓
narrative_synthesizer           — headline + synthesis
        ↓
watch_list_builder              — urgency-ranked watch items
        ↓
report_assembler                — saves MarketPulseReport to SQLite DB
```

---

## BrightData Integration

- Used for: SERP queries (up to 80 per run) and page scraping (up to 57 accepted docs per run)
- Cost per demo run: ~118–140 BrightData calls
- Pricing docs rejected if: `pricing_source_family_mismatch`, `site_constraint_mismatch`, `ir_pages_requires_tier1_ir_or_sec_domain`
- Zero fetch errors in Sprint 4 run

---

## Research Methodology

1. **Query planning:** Agent 1 generates structured queries covering all required signal types across all tracked companies, constrained to validated source families (IR domains, tier-1 news, academic, pricing domains)
2. **Document retrieval:** BrightData SERP + scrape, filtered by URL scorer (hard rejections, relevance scoring)
3. **Fact extraction:** Agent 3 extracts typed FactObjects with claim, evidence_quote, confidence, signal_type, entity_name, source_url
4. **Multi-layer validation:** Gate 1 (deterministic) + Gate 2 (LLM-based SAFE verification)
5. **Sentiment scoring:** FinBERT per-fact, aggregated into signal-level sentiment scores
6. **Triangulation:** Claims corroborated by ≥2 independent sources promoted to verified status
7. **Contradiction detection:** Agent 6 flags claims that conflict within the same company/signal
8. **Report assembly:** Structured MarketPulseReport with narrative, pulse score, watch list, per-signal top narratives

---

## Reliability Mechanisms

| Mechanism | What It Prevents |
|---|---|
| `COMPANY_IR_DOMAINS` frozenset (Fix 1) | Out-of-scope company IR pages accepted via domain fallback |
| `_METADATA_NAV_PATTERNS` (Fix 2a) | IR navigation descriptions extracted as financial facts |
| `_PRICING_REJECT_PATTERNS` (Fix 2b) | Index-launch misclassifications and HBM supplier_risk mislabeled as pricing_pressure |
| SAFE verification (Gate 2) | Hallucinated or over-extrapolated claims not grounded in source |
| Triangulation | Unverified single-source claims shown separately from corroborated findings |
| `quality_gate` | Reports with insufficient signal depth never reach PASS status |
| Demo scope enforcement | Prevents accidental 8-company run during demo |

---

## Known Limitations

| Limitation | Status |
|---|---|
| `fact_count < 50` → PARTIAL_PASS | Inherent to filtering; requires retrieval depth improvements in Sprint 5 |
| CoreWeave/GCP pricing pages: JS-rendered tables inaccessible | Requires Playwright fallback — not implemented |
| pricing_pressure: 0 verified claims (triangulation threshold: 2 sources) | Only 2 domains produce pricing facts; Sprint 5 fix: lower threshold or add sources |
| investor_signal concentration: 60% of facts from IR domains | Structural imbalance; Sprint 5: diversify query routing |
| Agent 1 ValueError in round 1 expansion | Pre-existing bug; crashes clean regression; Sprint 5 P0 fix |
| 33% zero-doc query rate | Pricing queries narrow; Sprint 5: sub-query expansion |

---

## Improvements Since Sprint 1

| Sprint | Key Improvement |
|---|---|
| Sprint 1 | Pipeline foundation: LangGraph DAG, BrightData, Agent 3 extraction |
| Sprint 2 | Demo scope enforcement, 3-company baseline, initial artifact audits |
| Sprint 3 | Agent 3 prompt tuning (reduced hallucinations), evidence quality audit tooling |
| Sprint 4 | IR-nav entity scope enforcement, metadata/nav claim guard, pricing sanity filter; pulse_score +29% (44.3→57.0); pricing verdict WEAK→ACCEPTABLE; suspicious claims 1→0; signal coverage 4/6→6/6 |

---

## What Remains Before Demo / Hackathon

**Must-fix (P0):**
- Agent 1 ValueError crash in round 1 expansion

**Should-fix (P1, high value):**
- Retrieval depth improvement to consistently reach fact_count ≥50

**Nice-to-have (P2–P5):**
- Playwright fallback for CoreWeave/GCP pricing pages
- pricing_pressure triangulation threshold adjustment
- investor_signal corpus diversification
- zero-doc query rate reduction

**No remaining frontend issues:** Build is clean (exit 0). Dashboard loads report data correctly.

**Demo script:** `backend/scripts/demo_track2_ai_hardware_audit.py`

**Report access:** `GET /api/reports/latest` → returns `report_3dfb4b94068b` data
