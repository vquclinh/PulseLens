"""
Pipeline quality regression test — run from backend/ as:
  python -m tests.test_pipeline_quality

Runs Agent 1 → Agent 2 → Agent 3 → validate_fact → SAFE → FinBERT on 5 live queries,
prints a before/after comparison against the baseline from the first pipeline run,
and saves all intermediate files to /tmp/pipeline_test_v2/.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# ── Bootstrap ────────────────────────────────────────────────────────────────
_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv
load_dotenv(_BACKEND / ".env")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
for _n in ("app.pipeline", "app.utils"):
    logging.getLogger(_n).setLevel(logging.INFO)

OUT = Path("/tmp/pipeline_test_v2")
OUT.mkdir(exist_ok=True)

SEP  = "=" * 70
SEP2 = "-" * 70

# ── Baseline values from the first run ───────────────────────────────────────
BASELINE = {
    "documents":      25,
    "raw_facts":      25,
    "validated":      25,
    "safe":           21,
    "scored":         21,
    "avg_confidence": 0.926,
    "stale_facts":    3,    # AMD FY2020
    "edgar_facts":    5,    # 13F-HR index pages
    "finbert_misclass": 2,  # Intel soaring / News from...
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _dump(obj, path: Path):
    def _s(o):
        return o.model_dump() if hasattr(o, "model_dump") else str(o)
    path.write_text(json.dumps(obj, indent=2, default=_s))


POSITIVE_RE = re.compile(
    r"\b(rais|record|beat|strong|growth|gain|expand|launch|breakthrough|"
    r"exceed|surpass|profit|upgrad|bullish)\b", re.I
)
NEGATIVE_RE = re.compile(
    r"\b(layoff|laid.off|cut|miss|declin|drop|loss|shortag|risk|delay|"
    r"disappoint|warn|below|fell|miss|struggl|bearish|downgrad)\b", re.I
)

def _sentiment_mismatch(claim: str, scored: str) -> bool:
    pos = bool(POSITIVE_RE.search(claim))
    neg = bool(NEGATIVE_RE.search(claim))
    if pos and not neg and scored == "negative":
        return True
    if neg and not pos and scored == "positive":
        return True
    return False

def _is_stale(fact) -> bool:
    """Fact references data before 2024."""
    claim_lower = fact.claim.lower()
    for year in range(2000, 2024):
        if str(year) in claim_lower:
            return True
    return False

def _is_edgar_index_fact(fact) -> bool:
    """Fact came from EDGAR filing index — low-signal metadata."""
    claim_lower = fact.claim.lower()
    return any(x in claim_lower for x in [
        "13f-hr", "13f-nt", "quarterly report filed by institutional",
        "filed by institutional managers", "accession number",
    ])

def _is_headline_fragment(fact) -> bool:
    """Claim is a headline copy or starts with known bad patterns."""
    claim = fact.claim
    bad_starts = ("News from", "According to", "Watch ", "Report:")
    return any(claim.startswith(p) for p in bad_starts)


# ════════════════════════════════════════════════════════════════════════════
# Pipeline stages
# ════════════════════════════════════════════════════════════════════════════

async def _run_pipeline() -> dict:
    from app.pipeline.agent1_query_planner import QueryPlanner
    from app.pipeline.agent2_web_workers import collect_documents
    from app.pipeline.agent3_fact_extractors import extract_facts_from_documents
    from app.pipeline.node_validate_and_split import validate_facts, run_safe_verification
    from app.pipeline.agent4_finbert_scorer import run_finbert_scorer
    from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
    from app.config.companies import COMPANIES

    print(f"\n{SEP}")
    print("Running Agent 1 (query planning)…")
    planner = QueryPlanner()
    all_queries = planner.run(
        market=DEFAULT_MARKET,
        companies=[c.name for c in COMPANIES],
        time_window=DEFAULT_TIME_WINDOW,
        expansion_round=0,
    )
    queries = all_queries[:5]
    print(f"  Agent 1: {len(all_queries)} total queries — using first 5")

    print("Running Agent 2 (web collection)…")
    documents = await collect_documents(queries)
    print(f"  Agent 2: {len(documents)} documents after quality filter")
    _dump(documents, OUT / "raw_documents.json")

    print("Running Agent 3 (fact extraction)…")
    raw_facts = await extract_facts_from_documents(documents)
    print(f"  Agent 3: {len(raw_facts)} raw facts from {len(documents)} documents")
    _dump(raw_facts, OUT / "raw_facts.json")

    print("Running validate_fact…")
    docs_by_id = {d.doc_id: d for d in documents}
    validated = validate_facts(raw_facts, docs_by_id)
    print(f"  validate_fact: {len(validated)} / {len(raw_facts)} passed")
    _dump(validated, OUT / "validated_facts.json")

    print("Running SAFE verification…")
    safe_facts = await run_safe_verification(validated)
    print(f"  SAFE: {len(safe_facts)} / {len(validated)} passed")
    _dump(safe_facts, OUT / "safe_facts.json")

    print("Running FinBERT…")
    scored_facts, errors = await run_finbert_scorer(safe_facts)
    print(f"  FinBERT: {len(scored_facts)} scored, {len(errors)} errors")
    _dump(scored_facts, OUT / "scored_facts.json")

    return {
        "documents":  documents,
        "raw_facts":  raw_facts,
        "validated":  validated,
        "safe":       safe_facts,
        "scored":     scored_facts,
        "errors":     errors,
    }


# ════════════════════════════════════════════════════════════════════════════
# Quality checks + report
# ════════════════════════════════════════════════════════════════════════════

def _analyze(data: dict) -> dict:
    raw_facts   = data["raw_facts"]
    scored      = data["scored"]

    avg_conf     = sum(f.confidence for f in raw_facts) / max(len(raw_facts), 1)
    stale        = [f for f in raw_facts if _is_stale(f)]
    edgar        = [f for f in raw_facts if _is_edgar_index_fact(f)]
    headline     = [f for f in scored if _is_headline_fragment(f)]
    misclass     = [f for f in scored if _sentiment_mismatch(f.claim, f.sentiment)]
    pre2024_date = [
        f for f in scored
        if f.published_date and f.published_date < "2024-01-01"
    ]

    return {
        "documents":        len(data["documents"]),
        "raw_facts":        len(raw_facts),
        "validated":        len(data["validated"]),
        "safe":             len(data["safe"]),
        "scored":           len(scored),
        "avg_confidence":   round(avg_conf, 3),
        "stale_facts":      len(stale),
        "edgar_facts":      len(edgar),
        "headline_facts":   len(headline),
        "finbert_misclass": len(misclass),
        "pre2024_dates":    len(pre2024_date),
        "stale_list":       [f.fact_id + ": " + f.claim[:80] for f in stale],
        "edgar_list":       [f.fact_id + ": " + f.claim[:80] for f in edgar],
        "headline_list":    [f.fact_id + ": " + f.claim[:80] for f in headline],
        "misclass_list":    [
            f"{f.fact_id}: {f.sentiment} ← {f.claim[:70]}" for f in misclass
        ],
        "confidence_dist":  _conf_dist(raw_facts),
    }


def _conf_dist(facts) -> str:
    if not facts:
        return "no facts"
    bands = {"1.0": 0, "0.9": 0, "0.8": 0, "0.7": 0, "<0.7": 0}
    for f in facts:
        c = f.confidence
        if c >= 1.0:   bands["1.0"]  += 1
        elif c >= 0.9: bands["0.9"]  += 1
        elif c >= 0.8: bands["0.8"]  += 1
        elif c >= 0.7: bands["0.7"]  += 1
        else:          bands["<0.7"] += 1
    total = len(facts)
    return "  ".join(f"{k}:{v}({100*v//total}%)" for k, v in bands.items())


def _check(label: str, value, baseline, direction: str = "lower", threshold=None) -> str:
    """Return PASS / FAIL / WARN string for a metric check."""
    if threshold is not None:
        if direction == "lower" and value <= threshold:
            return f"✅ PASS  {label}: {value} (target ≤ {threshold})"
        if direction == "higher" and value >= threshold:
            return f"✅ PASS  {label}: {value} (target ≥ {threshold})"
        return f"❌ FAIL  {label}: {value} (target {'≤' if direction=='lower' else '≥'} {threshold})"
    delta = value - baseline
    arrow = "↓" if delta < 0 else ("↑" if delta > 0 else "→")
    sign  = "+" if delta >= 0 else ""
    return f"   {label}: {baseline} → {value}  ({sign}{delta:.3f} {arrow})"


def _print_report(result: dict):
    B = BASELINE
    A = result

    print(f"\n{SEP}")
    print("BEFORE / AFTER COMPARISON")
    print(SEP)
    print(f"  BEFORE: avg_confidence={B['avg_confidence']:.3f}  "
          f"stale_facts={B['stale_facts']}  edgar_facts={B['edgar_facts']}")
    print(f"  AFTER:  avg_confidence={A['avg_confidence']:.3f}  "
          f"stale_facts={A['stale_facts']}  edgar_facts={A['edgar_facts']}")

    print(f"\n{SEP2}")
    print("FUNNEL")
    print(f"  documents  : {A['documents']:>3}  (was {B['documents']})")
    print(f"  raw_facts  : {A['raw_facts']:>3}  (was {B['raw_facts']})")
    print(f"  validated  : {A['validated']:>3}  (was {B['validated']})")
    print(f"  safe       : {A['safe']:>3}  (was {B['safe']})")
    print(f"  scored     : {A['scored']:>3}  (was {B['scored']})")

    print(f"\n{SEP2}")
    print("VERIFICATION CHECKS")
    print(_check("stale_facts (≤0)",     A["stale_facts"],     B["stale_facts"],     "lower",  0))
    print(_check("edgar_facts (≤0)",     A["edgar_facts"],     B["edgar_facts"],     "lower",  0))
    print(_check("headline_facts (≤0)",  A["headline_facts"],  0,                    "lower",  0))
    print(_check("finbert_misclass (≤0)",A["finbert_misclass"],B["finbert_misclass"],"lower",  0))
    print(_check("pre2024_dates (≤0)",   A["pre2024_dates"],   0,                    "lower",  0))
    print(_check("scored_facts (≥15)",   A["scored"],          B["scored"],          "higher", 15))

    # Confidence: target range 0.75–0.85
    conf_ok = 0.75 <= A["avg_confidence"] <= 0.88
    conf_label = "✅ PASS" if conf_ok else ("⚠️  WARN" if A["avg_confidence"] < 0.75 else "⚠️  WARN")
    conf_note  = "(in 0.75–0.88 target)" if conf_ok else ("(too low)" if A["avg_confidence"] < 0.75 else "(still inflated)")
    print(f"  {conf_label}  avg_confidence: {B['avg_confidence']:.3f} → {A['avg_confidence']:.3f}  {conf_note}")

    print(f"\n{SEP2}")
    print("CONFIDENCE DISTRIBUTION")
    print(f"  Before : all clustered ~0.9")
    print(f"  After  : {A['confidence_dist']}")

    if A["stale_list"]:
        print(f"\n{SEP2}")
        print("REMAINING STALE FACTS")
        for item in A["stale_list"]:
            print(f"  {item}")

    if A["edgar_list"]:
        print(f"\n{SEP2}")
        print("REMAINING EDGAR INDEX FACTS")
        for item in A["edgar_list"]:
            print(f"  {item}")

    if A["headline_list"]:
        print(f"\n{SEP2}")
        print("REMAINING HEADLINE FRAGMENTS")
        for item in A["headline_list"]:
            print(f"  {item}")

    if A["misclass_list"]:
        print(f"\n{SEP2}")
        print("REMAINING FINBERT MISCLASSIFICATIONS")
        for item in A["misclass_list"]:
            print(f"  {item}")

    # Write markdown report
    checks = [
        ("stale_facts",     A["stale_facts"],    0,  "lower"),
        ("edgar_facts",     A["edgar_facts"],     0,  "lower"),
        ("headline_facts",  A["headline_facts"],  0,  "lower"),
        ("finbert_misclass",A["finbert_misclass"],0,  "lower"),
        ("scored ≥ 15",     A["scored"],         15, "higher"),
    ]
    all_pass = all(
        (v <= t if d == "lower" else v >= t)
        for _, v, t, d in checks
    ) and conf_ok

    verdict = "✅ ALL CHECKS PASS" if all_pass else "⚠️  SOME CHECKS FAILED — see details above"

    md = [
        "# Pipeline Quality Report v2 — After Fixes",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        "\n---\n",
        "## Funnel Summary",
        "| Stage | Before | After | Change |",
        "|-------|--------|-------|--------|",
        f"| Documents | {B['documents']} | {A['documents']} | {A['documents']-B['documents']:+d} |",
        f"| Raw facts | {B['raw_facts']} | {A['raw_facts']} | {A['raw_facts']-B['raw_facts']:+d} |",
        f"| After validate_fact | {B['validated']} | {A['validated']} | {A['validated']-B['validated']:+d} |",
        f"| After SAFE | {B['safe']} | {A['safe']} | {A['safe']-B['safe']:+d} |",
        f"| After FinBERT | {B['scored']} | {A['scored']} | {A['scored']-B['scored']:+d} |",
        "\n---\n",
        "## Fix Verification",
        f"| Fix | Metric | Before | After | Result |",
        f"|-----|--------|--------|-------|--------|",
        f"| FIX 1 time window | stale_facts | {B['stale_facts']} | {A['stale_facts']} | {'✅' if A['stale_facts']==0 else '❌'} |",
        f"| FIX 2 declarative | headline_frags | 2 | {A['headline_facts']} | {'✅' if A['headline_facts']==0 else '❌'} |",
        f"| FIX 3 edgar filter | edgar_facts | {B['edgar_facts']} | {A['edgar_facts']} | {'✅' if A['edgar_facts']==0 else '❌'} |",
        f"| FIX 4 confidence | avg_conf | {B['avg_confidence']:.3f} | {A['avg_confidence']:.3f} | {'✅' if conf_ok else '⚠️'} |",
        f"| Regression | scored ≥ 15 | {B['scored']} | {A['scored']} | {'✅' if A['scored']>=15 else '❌'} |",
        "\n---\n",
        "## Confidence Distribution",
        f"\nBefore: all clustered ~0.9",
        f"\nAfter:  {A['confidence_dist']}",
        "\n---\n",
        f"## Verdict\n\n### {verdict}",
    ]
    report_path = OUT / "PIPELINE_QUALITY_REPORT_V2.md"
    report_path.write_text("\n".join(md))
    print(f"\n  → saved {report_path}")

    print(f"\n{SEP}")
    print(f"VERDICT: {verdict}")
    print(SEP)


# ════════════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════════════

async def _main():
    print(f"\n{'#'*70}")
    print("  PIPELINE QUALITY REGRESSION TEST v2")
    print(f"{'#'*70}")
    data   = await _run_pipeline()
    result = _analyze(data)
    _print_report(result)
    print(f"\n  Files saved to: {OUT}")


if __name__ == "__main__":
    asyncio.run(_main())
