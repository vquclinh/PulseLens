#!/usr/bin/env python
"""Run one focused retrieval-quality audit of the full PulseLens pipeline.

Artifacts are written under pipeline_audit_artifacts/<timestamp>/:
  - query_planner_audit.json
  - web_collection_audit.json
  - quality_gate_audit.json
  - fetch_error_summary.json
  - final_report_quality_summary.json
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

load_dotenv(BACKEND / ".env")

from app.config.companies import COMPANIES  # noqa: E402
from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW  # noqa: E402
from app.pipeline.graph import pipeline_graph  # noqa: E402
from app.schemas.models import MarketPulseReport  # noqa: E402
from app.utils.helpers import generate_uuid  # noqa: E402


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")


def _initial_state() -> dict[str, Any]:
    return {
        "market": DEFAULT_MARKET,
        "companies": [company.name for company in COMPANIES],
        "time_window": DEFAULT_TIME_WINDOW,
        "queries": [],
        "pending_queries": [],
        "query_planner_audit": {},
        "raw_documents": [],
        "web_collection_audit": {},
        "fetch_error_summary": {},
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
        "quality_status": "FAIL_EXPAND",
        "quality_reasons": [],
        "covered_signal_types": [],
        "missing_signal_types": [],
        "company_coverage": 0.0,
        "zero_doc_query_rate": 0.0,
        "fetch_error_rate": 0.0,
        "source_count": 0,
        "fact_count": 0,
        "errors": [],
    }


async def main() -> int:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = ROOT / "pipeline_audit_artifacts" / timestamp
    artifact_dir.mkdir(parents=True, exist_ok=True)

    log_file = artifact_dir / "pipeline_run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_file, encoding="utf-8")],
    )

    config = {"configurable": {"thread_id": f"retrieval-audit-{generate_uuid()[:12]}"}}
    result = await pipeline_graph.ainvoke(_initial_state(), config=config)

    query_audit = result.get("query_planner_audit") or {}
    web_audit = result.get("web_collection_audit") or {}
    fetch_summary = result.get("fetch_error_summary") or {}
    quality_audit = {
        "quality_status": result.get("quality_status"),
        "quality_reasons": result.get("quality_reasons") or [],
        "covered_signal_types": result.get("covered_signal_types") or [],
        "missing_signal_types": result.get("missing_signal_types") or [],
        "company_coverage": result.get("company_coverage"),
        "zero_doc_query_rate": result.get("zero_doc_query_rate"),
        "fetch_error_rate": result.get("fetch_error_rate"),
        "source_count": result.get("source_count"),
        "fact_count": result.get("fact_count"),
        "query_expansion_rounds": result.get("query_expansion_rounds"),
    }

    report = result.get("report")
    report_summary: dict[str, Any]
    if isinstance(report, MarketPulseReport):
        report_summary = {
            "report_id": report.report_id,
            "quality_status": report.quality_status.value,
            "quality_reasons": report.quality_reasons,
            "pulse_score": report.pulse_score,
            "pulse_status": report.pulse_status.value,
            "pulse_confidence": report.pulse_confidence,
            "evidence_count": report.evidence_count,
            "source_count": report.source_count,
            "audit_summary": report.audit_summary,
        }
    else:
        report_summary = {"report": None, "errors": result.get("errors") or []}

    _write(artifact_dir / "query_planner_audit.json", query_audit)
    _write(artifact_dir / "web_collection_audit.json", web_audit)
    _write(artifact_dir / "quality_gate_audit.json", quality_audit)
    _write(artifact_dir / "fetch_error_summary.json", fetch_summary)
    _write(artifact_dir / "final_report_quality_summary.json", report_summary)

    failed_domains = Counter(fetch_summary.get("failure_count_by_domain") or {})
    failed_reasons = Counter(fetch_summary.get("failure_count_by_reason") or {})
    print("\nRetrieval quality audit summary")
    print(f"  artifacts: {artifact_dir}")
    print(f"  final quality_status: {quality_audit.get('quality_status')}")
    print(f"  fact count: {quality_audit.get('fact_count')}")
    print(f"  source count: {quality_audit.get('source_count')}")
    print(f"  covered signal types: {quality_audit.get('covered_signal_types')}")
    print(f"  missing signal types: {quality_audit.get('missing_signal_types')}")
    print(f"  zero-doc query rate: {quality_audit.get('zero_doc_query_rate')}")
    print(f"  fetch error rate: {quality_audit.get('fetch_error_rate')}")
    print(f"  top failed domains: {failed_domains.most_common(10)}")
    print(f"  top failure reasons: {failed_reasons.most_common(10)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
