#!/usr/bin/env python3
"""Run the full 8-company pipeline and save report_id to /tmp/pulselens_report_id.txt"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
for _noisy in ("httpx", "httpcore", "sentence_transformers", "transformers", "torch"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

from app.config.companies import COMPANIES
from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
from app.pipeline.graph import pipeline_graph
from app.utils.helpers import generate_uuid


async def main() -> str:
    print(f"\n{'='*60}")
    print(f"  PulseLens Full Pipeline Run")
    print(f"  Market  : {DEFAULT_MARKET}")
    print(f"  Companies: {', '.join(c.name for c in COMPANIES)}")
    print(f"{'='*60}\n")

    state = {
        "market": DEFAULT_MARKET,
        "companies": [c.name for c in COMPANIES],
        "time_window": DEFAULT_TIME_WINDOW,
        "queries": [],
        "raw_documents": [],
        "raw_facts": [],
        "scored_facts": [],
        "verified_claims": [],
        "contradictions": [],
        "signal_scores": {},
        "company_narratives": [],
        "market_narrative": None,
        "report": None,
        "query_expansion_rounds": 0,
        "low_signal_types": [],
        "quality_passed": False,
        "errors": [],
    }

    thread_id = f"run-{generate_uuid()[:12]}"
    config = {"configurable": {"thread_id": thread_id}}

    print(f"thread_id={thread_id}\n")
    result = await pipeline_graph.ainvoke(state, config=config)

    report = result.get("report")
    errors = result.get("errors", [])

    if report is None:
        print("\n❌ PIPELINE FAILED — no report generated")
        print("Errors:", errors[:10])
        sys.exit(1)

    print(f"\n{'='*60}")
    print("  PIPELINE COMPLETE")
    print(f"  report_id      : {report.report_id}")
    print(f"  pulse_score    : {report.pulse_score}")
    print(f"  pulse_status   : {report.pulse_status.value}")
    print(f"  pulse_conf     : {report.pulse_confidence:.3f}")
    print(f"  companies      : {len(report.company_narratives)}")
    print(f"  news_items     : {len(report.news_items)}")
    print(f"  top_signals    : {len(report.top_signals)}")
    print(f"  contradictions : {len(report.contradictions)}")
    print(f"  evidence_count : {report.evidence_count}")
    print(f"  headline       : {report.market_narrative.narrative_headline[:70]}")
    print(f"{'='*60}")

    if errors:
        print(f"\n  Non-fatal errors: {len(errors)}")
        for e in errors[:3]:
            print(f"    {e}")

    print("\n  Company narratives:")
    for cn in report.company_narratives:
        print(f"    {cn.ticker:6s} {cn.company:12s} {cn.momentum.value:18s} score={cn.momentum_score}")

    out = Path("/tmp/pulselens_report_id.txt")
    out.write_text(report.report_id)
    print(f"\n  Saved report_id to {out}")
    return report.report_id


if __name__ == "__main__":
    asyncio.run(main())
