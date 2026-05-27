# Authoritative Final Demo Artifacts

**Date:** 2026-05-28  
**Status: LOCKED — This is the authoritative backend baseline for demo.**

---

## Report Identity

| Field | Value |
|-------|-------|
| `report_id` | `report_e68e7289fc30` |
| `quality_status` | **PASS** |
| `pulse_score` | 52.7 (`risk_rising`) |
| `pulse_confidence` | 0.611 |
| Review bundle path | `pipeline_audit_artifacts/final_review_bundle_report_e68e7289fc30/` |
| Pipeline run started | 2026-05-28 00:40:06 UTC |
| Report saved | 2026-05-28 00:48:42 UTC |
| Run duration | ~8 min 36 sec |

---

## Final Metrics

| Metric | Value |
|--------|-------|
| Evidence count (facts) | **67** |
| Source count (unique domains) | **23** |
| Verified claims | **10** |
| Average confidence | 0.905 |
| Queries issued | 32 |
| Accepted documents | 48 |
| Estimated BrightData calls | ~94 |
| Query expansion rounds | 0 (PASS on first round) |
| Failed / zero-doc queries | 8 / 8 |
| Fetch errors | 2 |

### Signal Coverage

| Signal Type | Facts |
|------------|-------|
| `strategic_messaging` | 17 |
| `product_launch` | 16 |
| `investor_signal` | 12 |
| `pricing_pressure` | **14** |
| `supplier_risk` | 7 |
| `news_sentiment` | 1 |
| `hiring_momentum` | 0 (optional — not required for PASS) |

All 6 of the 6 required signal types covered. Zero missing signal types.

### Pricing Quality

| Category | Count |
|----------|-------|
| Strong pricing signals | **13** |
| Weak pricing signals | 0 |
| Misclassified pricing | 0 |
| Insufficient evidence | 1 |
| False positives (post-precision fix) | 0 |

**Verdict: ACCEPTABLE — majority of pricing facts are strong signals (93%)**

---

## Review Bundle Contents

All files located in `pipeline_audit_artifacts/final_review_bundle_report_e68e7289fc30/`:

| File | Description |
|------|-------------|
| `final_report_quality_summary.json` | Top-level PASS/FAIL, pulse score, signal scores, watch list |
| `demo_report_summary.json` | Full report object + company/signal coverage metadata |
| `evidence_quality_summary.json` | Fact count, source count, signal distribution, pricing verdict |
| `quality_gate_audit.json` | Gate decision, zero-doc rate, fetch error rate, company coverage |
| `pricing_pressure_semantics_audit.json` | Per-fact pricing classification (strong/weak/misclassified) |
| `source_tier_quality_audit.json` | Per-domain quality rating and fact counts |
| `suspicious_claims.json` | Suspicious claim list — **empty (0 suspicious claims)** |
| `pricing_extraction_gap_summary.json` | Pricing URLs that produced no facts and root causes |
| `signal_semantics_audit.json` | Signal-type audit across all facts |
| `web_collection_audit.json` | Per-document collection metadata (URL, content length, tier) |
| `query_planner_audit.json` | Agent 1 query plan, signal distribution, regen attempts |
| `fetch_error_summary.json` | BrightData HTTP errors and retry outcomes |
| `pricing_document_extraction_diagnosis.json` | Diagnosis of pricing doc yield vs. accepted doc count |
| `pipeline_run.log` | Full pipeline execution log (all agents, BrightData calls, LLM calls) |

---

## Commands

### Run Live Demo Pipeline (requires API keys)
```bash
cd /mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens/backend
PULSELENS_DEMO_SCOPE=true python scripts/demo_track2_ai_hardware_audit.py
```

### Run Evidence Quality Audit Against This Report (offline, no API calls)
```bash
cd /mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens/backend
python scripts/evidence_quality_audit.py --report-id report_e68e7289fc30
```

### Run Zero-Cost Static Tests (no API keys)
```bash
cd /mnt/vquclinh/PROJECT-CMAKE/PULSE-LENS/PulseLens/backend
python tests/pipeline/test_pricing_pre_extractor.py    # 22 tests
python tests/pipeline/test_pricing_browser_routing.py  # 12 tests
python tests/pipeline/test_agent1_expansion_stability.py  # 4 tests
python tests/pipeline/test_agent1_signal_balance.py    # 15 tests
```

---

## Baseline Lock Notice

**This report (`report_e68e7289fc30`) is the authoritative backend demo baseline.**

- Do NOT re-run the live pipeline unless a critical bug is discovered that affects correctness.
- Do NOT lower `QUALITY_MIN_FACTS` (currently 50) to inflate status.
- Do NOT remove or weaken signal balance constants in `agent1_query_planner.py`.
- Do NOT modify `node_quality_gate.py` thresholds.
- The backend achieved PASS on the first quality gate round with 67 facts, 23 sources,
  zero suspicious claims, and 93% strong pricing signals.

**All remaining work should target frontend/demo polish, not backend retrieval optimization.**

---

## Companies and Signals Covered

- **Companies:** AMD, Nvidia, Supermicro
- **Core signals covered:** investor_signal, pricing_pressure, product_launch, supplier_risk
- **Optional signals covered:** news_sentiment, strategic_messaging
- **Optional signals missing:** hiring_momentum (no dedicated hiring query returned usable results; not required for PASS)
