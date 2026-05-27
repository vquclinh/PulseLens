"""
Live Agent 2 → Agent 3 integration test.

Tests:
  Task 2 — 5 known-good queries (IR, SEC, jobs, pricing, news):
    • shows documents returned
    • shows how many URLs were filtered by URLScorer
    • verifies each query type returns useful documents

  Task 3 — feeds documents into Agent 3:
    • verbatim quote check
    • claim specificity check
    • entity normalization check
    • SAFE discard rate

Run:
  python backend/scripts/test_a2_a3.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv
load_dotenv(_BACKEND / ".env")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
for _n in ("app.pipeline", "app.utils"):
    logging.getLogger(_n).setLevel(logging.INFO)

OUT = Path("/tmp/test_a2_a3")
OUT.mkdir(exist_ok=True)

SEP  = "=" * 70
SEP2 = "-" * 70


# ── 5 test queries ─────────────────────────────────────────────────────────────

def _make_queries():
    from app.schemas.models import SearchQuery, SignalType
    from app.utils.helpers import generate_uuid

    def _q(label, entity, sig, source_type, text):
        return label, SearchQuery(
            query_id=generate_uuid()[:12],
            query_text=text,
            target_entity=entity,
            signal_type=sig,
            source_type=source_type,
            priority=1,
            expected_source_tier=1 if source_type == "ir_pages" else 3,
        )

    return [
        _q("IR — Nvidia",
           "Nvidia", SignalType.investor_signal, "ir_pages",
           "Nvidia quarterly earnings report site:ir.nvidia.com"),

        _q("SEC — AMD",
           "AMD", SignalType.investor_signal, "ir_pages",
           "AMD 10-K annual report site:sec.gov"),

        _q("Jobs — Intel",
           "Intel", SignalType.hiring_momentum, "job_pages",
           "Intel software engineer AI machine learning jobs 2025"),

        _q("Pricing — Nvidia GPU",
           "Nvidia", SignalType.pricing_pressure, "serp_news",
           "H100 A100 GPU server pricing discount 2025"),

        _q("News — market",
           "market", SignalType.news_sentiment, "serp_news",
           "AI chip semiconductor market demand supply 2025"),
    ]


# ── Agent 2 runner with per-query stats ───────────────────────────────────────

async def run_agent2(queries) -> tuple[dict[str, Any], Any]:
    from app.pipeline.agent2_web_workers import (
        collect_documents_for_query, _discover_candidate_urls, BrightDataClient
    )
    from app.utils.url_scorer import URLScorer

    scorer = URLScorer()   # shared across all queries
    all_results = {}

    for label, query in queries:
        print(f"\n  [{label}]  query_id={query.query_id}")
        print(f"    text:        {query.query_text}")
        print(f"    source_type: {query.source_type}")

        # Get candidate URLs before filtering so we can show stats
        try:
            client = BrightDataClient.from_env()
        except ValueError as exc:
            print(f"    ⚠️  BrightData config error: {exc}")
            all_results[label] = []
            continue

        candidates_raw = await _discover_candidate_urls(client, query)
        candidates_pass = [c for c in candidates_raw if scorer.should_fetch(c, query)]
        filtered = len(candidates_raw) - len(candidates_pass)

        print(f"    SERP results : {len(candidates_raw)} raw → {len(candidates_pass)} passed filter (dropped {filtered})")

        if candidates_raw and not candidates_pass:
            print("    ⚠️  ALL candidates filtered — showing top 3 rejected URLs:")
            for c in candidates_raw[:3]:
                score = scorer.score(c, query)
                print(f"      score={score:.3f}  {c.get('url','')[:80]}")

        # Fetch the documents (scorer used inside collect_documents_for_query)
        docs = await collect_documents_for_query(query, scorer=scorer)
        all_results[label] = docs

        print(f"    Documents    : {len(docs)} useful documents")
        for d in docs[:3]:
            print(f"      [{d.source_tier}] {d.domain}  {d.title[:60]}")

    return all_results, scorer


# ── Agent 3 runner ─────────────────────────────────────────────────────────────

async def run_agent3(all_docs_by_label: dict) -> dict:
    from app.pipeline.agent3_fact_extractors import extract_facts_from_documents

    flat_docs = []
    for docs in all_docs_by_label.values():
        flat_docs.extend(docs)

    if not flat_docs:
        print("  ⚠️  No documents to process")
        return {"raw_facts": [], "docs": flat_docs}

    print(f"\n  Extracting facts from {len(flat_docs)} documents…")
    raw_facts = await extract_facts_from_documents(flat_docs)
    print(f"  Extracted: {len(raw_facts)} raw facts")
    return {"raw_facts": raw_facts, "docs": flat_docs}


# ── validate_fact + SAFE ───────────────────────────────────────────────────────

async def run_validation(raw_facts, docs) -> dict:
    from app.pipeline.node_validate_and_split import validate_facts, run_safe_verification

    docs_by_id = {d.doc_id: d for d in docs}
    validated, validation_audit = validate_facts(raw_facts, docs_by_id)
    print(f"  validate_fact: {len(validated)}/{len(raw_facts)} passed")

    safe = await run_safe_verification(validated)
    print(f"  SAFE:          {len(safe)}/{len(validated)} passed")
    return {"validated": validated, "safe": safe, "validation_audit": validation_audit}


# ── Quality analysis ───────────────────────────────────────────────────────────

def _analyze_facts(raw_facts, safe_facts, docs):
    docs_by_id = {d.doc_id: d for d in docs}

    # Verbatim quote check: is evidence_quote a substring of source content?
    verbatim_pass = 0
    verbatim_fail = []
    for f in raw_facts:
        doc = docs_by_id.get(f.doc_id)
        if doc and f.evidence_quote.strip():
            if f.evidence_quote in doc.content:
                verbatim_pass += 1
            else:
                verbatim_fail.append(f)

    # Claim specificity: does it have numbers, dates, or named metrics?
    import re
    specific_re = re.compile(r'\$[\d,.]+|\d+[%BMK]|\b\d{4}\b|\bQ[1-4]\b', re.I)
    specific = [f for f in safe_facts if specific_re.search(f.claim)]
    vague    = [f for f in safe_facts if not specific_re.search(f.claim)]

    # Entity normalization: all entities should be from KNOWN_ENTITIES
    from app.config.companies import KNOWN_ENTITIES
    normalized   = [f for f in raw_facts if f.entity in KNOWN_ENTITIES]
    unnormalized = [f for f in raw_facts if f.entity not in KNOWN_ENTITIES]

    return {
        "verbatim_pass":   verbatim_pass,
        "verbatim_fail":   verbatim_fail,
        "specific_claims": specific,
        "vague_claims":    vague,
        "normalized":      normalized,
        "unnormalized":    unnormalized,
    }


# ── Report ─────────────────────────────────────────────────────────────────────

def _print_report(all_docs, raw_facts, validated, safe_facts, analysis, scorer):
    total_docs = sum(len(d) for d in all_docs.values())

    print(f"\n{SEP}")
    print("AGENT 2 — DOCUMENT COLLECTION")
    print(SEP)
    print(f"  {'Query':<20} {'Docs':>4}")
    print(f"  {'-'*20} {'-'*4}")
    for label, docs in all_docs.items():
        print(f"  {label:<20} {len(docs):>4}")
    print(f"  {'-'*20} {'-'*4}")
    print(f"  {'TOTAL':<20} {total_docs:>4}")

    print(f"\n{SEP2}")
    print("AGENT 2 — URL FILTERING")
    mem = scorer.error_memory._failed
    if mem:
        print(f"  Domains with permanent errors:")
        for domain, count in sorted(mem.items()):
            print(f"    {domain}: {count} failure(s)")
    else:
        print("  No permanent HTTP errors recorded")

    print(f"\n{SEP}")
    print("AGENT 3 — FACT EXTRACTION + VALIDATION")
    print(SEP)
    print(f"  Raw facts extracted : {len(raw_facts)}")
    print(f"  After validate_fact : {len(validated)}")
    print(f"  After SAFE          : {len(safe_facts)}")
    if len(raw_facts):
        print(f"  SAFE discard rate   : {(len(validated)-len(safe_facts))/len(validated)*100:.0f}%" if validated else "  N/A")

    print(f"\n{SEP2}")
    print("QUALITY CHECKS")

    total_checked = len([f for f in raw_facts if f.doc_id in {d.doc_id for d in sum(all_docs.values(), [])}])
    print(f"\n  Verbatim quotes ({analysis['verbatim_pass']}/{total_checked} verified):")
    if analysis["verbatim_fail"]:
        print(f"    ⚠️  {len(analysis['verbatim_fail'])} quotes NOT verbatim (LLM may have paraphrased):")
        for f in analysis["verbatim_fail"][:3]:
            print(f"      fact {f.fact_id}: '{f.evidence_quote[:70]}'")
    else:
        print("    ✅ All checked quotes are verbatim substrings of source content")

    vague_pct = len(analysis["vague_claims"]) / max(len(safe_facts), 1) * 100
    print(f"\n  Claim specificity ({len(analysis['specific_claims'])}/{len(safe_facts)} have numbers/dates):")
    if vague_pct > 40:
        print(f"    ⚠️  {vague_pct:.0f}% of claims are vague (no numbers/dates)")
    else:
        print(f"    ✅ {100-vague_pct:.0f}% of claims are specific")
    if analysis["vague_claims"][:2]:
        for f in analysis["vague_claims"][:2]:
            print(f"      vague: {f.claim[:80]}")

    norm_pct = len(analysis["normalized"]) / max(len(raw_facts), 1) * 100
    print(f"\n  Entity normalization ({len(analysis['normalized'])}/{len(raw_facts)} normalized):")
    if analysis["unnormalized"]:
        print(f"    ⚠️  {len(analysis['unnormalized'])} facts with unrecognized entities:")
        for f in analysis["unnormalized"][:3]:
            print(f"      entity='{f.entity}'  claim: {f.claim[:60]}")
    else:
        print(f"    ✅ All entities normalized to known company names")

    print(f"\n{SEP2}")
    print("SAMPLE SAFE-VERIFIED FACTS")
    for f in safe_facts[:5]:
        print(f"\n  fact_id  : {f.fact_id}")
        print(f"  entity   : {f.entity}  [{f.signal_type.value}]  tier:{f.source_tier}  conf:{f.confidence:.2f}")
        print(f"  claim    : {f.claim}")
        print(f"  quote    : {f.evidence_quote[:100]}")
        print(f"  date     : {f.published_date}")

    # Save JSON
    def _s(o):
        return o.model_dump() if hasattr(o, "model_dump") else str(o)

    (OUT / "documents.json").write_text(
        json.dumps({k: [d.model_dump() for d in v] for k, v in all_docs.items()}, indent=2)
    )
    (OUT / "raw_facts.json").write_text(json.dumps([f.model_dump() for f in raw_facts], indent=2))
    (OUT / "safe_facts.json").write_text(json.dumps([f.model_dump() for f in safe_facts], indent=2))

    ok = total_docs >= 3 and len(safe_facts) >= 3
    verdict = "✅ PASS — Agent 2→3 pipeline is healthy" if ok else "⚠️  WARN — low document/fact yield"
    print(f"\n{SEP}")
    print(f"VERDICT: {verdict}")
    print(f"  Files saved to: {OUT}")
    print(SEP)


# ── Entry point ────────────────────────────────────────────────────────────────

async def _main():
    print(f"\n{'#'*70}")
    print("  AGENT 2 → AGENT 3 LIVE INTEGRATION TEST")
    print(f"{'#'*70}")

    queries = _make_queries()

    print(f"\n{SEP}")
    print("TASK 2 — AGENT 2: collecting documents for 5 queries")
    print(SEP)

    all_docs, scorer = await run_agent2(queries)

    flat_docs = []
    for docs in all_docs.values():
        flat_docs.extend(docs)

    if not flat_docs:
        print("\n⚠️  No documents collected — check BrightData config / network")
        return

    print(f"\n{SEP}")
    print("TASK 3 — AGENT 3: extracting and validating facts")
    print(SEP)

    a3 = await run_agent3(all_docs)
    raw_facts = a3["raw_facts"]

    if not raw_facts:
        print("\n⚠️  No facts extracted — check LLM config / document quality")
        return

    val = await run_validation(raw_facts, flat_docs)
    analysis = _analyze_facts(raw_facts, val["safe"], flat_docs)

    _print_report(all_docs, raw_facts, val["validated"], val["safe"], analysis, scorer)


if __name__ == "__main__":
    asyncio.run(_main())
