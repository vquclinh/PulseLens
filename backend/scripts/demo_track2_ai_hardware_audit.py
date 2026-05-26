#!/usr/bin/env python
"""Demo full-pipeline audit for Bright Data Track 2 AI hardware slice."""
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
from langchain_core.runnables import RunnableConfig

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

load_dotenv(BACKEND / ".env")

from app.config.demo_scope import get_scope_config, scope_payload  # noqa: E402
from app.config.markets import DEFAULT_TIME_WINDOW  # noqa: E402
from app.pipeline.graph import pipeline_graph  # noqa: E402
from app.pipeline.state import PipelineState  # noqa: E402
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


def _initial_state(scope: Any) -> PipelineState:
    return {
        "market": scope.market,
        "companies": scope.companies,
        "time_window": DEFAULT_TIME_WINDOW,
        "demo_scope_enabled": scope.demo_scope_enabled,
        "target_signal_types": scope.core_signal_types,
        "core_signal_types": scope.core_signal_types,
        "optional_signal_types": scope.optional_signal_types,
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
    artifact_dir = ROOT / "pipeline_audit_artifacts" / f"demo_track2_{timestamp}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(artifact_dir / "pipeline_run.log", encoding="utf-8"),
        ],
    )

    scope = get_scope_config()
    config: RunnableConfig = {"configurable": {"thread_id": f"demo-track2-{generate_uuid()[:12]}"}}
    result = await pipeline_graph.ainvoke(_initial_state(scope), config=config)

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
            "top_signals": report.top_signals,
            "watch_list": report.market_narrative.watch_list if report.market_narrative else [],
            "audit_summary": report.audit_summary,
        }
    else:
        report_summary = {"report": None, "errors": result.get("errors") or []}

    pricing_doc_count = sum(
        1 for doc in result.get("raw_documents", [])
        if getattr(doc, "signal_type_hint", None) and doc.signal_type_hint.value == "pricing_pressure"
    )
    brightdata_calls = (
        int(fetch_summary.get("total_fetch_attempts") or 0)
        + int(web_audit.get("query_count") or 0)
        + sum(2 for query in web_audit.get("queries", []) if query.get("fallback_used"))
    )
    core_covered = sorted(set(quality_audit["covered_signal_types"]) & set(scope.core_signal_types))
    core_missing = sorted(set(scope.core_signal_types) - set(core_covered))
    optional_covered = sorted(set(quality_audit["covered_signal_types"]) & set(scope.optional_signal_types))
    optional_missing = sorted(set(scope.optional_signal_types) - set(optional_covered))
    company_entities = {getattr(fact, "entity", "") for fact in result.get("scored_facts", [])}
    companies_covered = sorted(set(scope.companies) & company_entities)

    demo_report_summary = {
        "report": report_summary,
        "companies_covered": companies_covered,
        "core_signals_covered": core_covered,
        "core_signals_missing": core_missing,
        "optional_signals_covered": optional_covered,
        "optional_signals_missing": optional_missing,
        "pricing_pressure_document_count": pricing_doc_count,
        "estimated_brightdata_calls": brightdata_calls,
    }

    _write(artifact_dir / "demo_scope_config.json", scope_payload(scope))
    _write(artifact_dir / "query_planner_audit.json", query_audit)
    _write(artifact_dir / "web_collection_audit.json", web_audit)
    _write(artifact_dir / "quality_gate_audit.json", quality_audit)
    _write(artifact_dir / "fetch_error_summary.json", fetch_summary)
    _write(artifact_dir / "final_report_quality_summary.json", report_summary)
    _write(artifact_dir / "demo_report_summary.json", demo_report_summary)

    signal_counts = Counter(f.signal_type.value for f in result.get("scored_facts", []))
    watch_items = report.market_narrative.watch_list if isinstance(report, MarketPulseReport) and report.market_narrative else []

    print("\nDemo Track 2 AI hardware audit")
    print(f"  artifacts: {artifact_dir}")
    print(f"  report_id: {report.report_id if isinstance(report, MarketPulseReport) else None}")
    print(f"  quality_status: {quality_audit.get('quality_status')}")
    print(f"  quality_reasons: {quality_audit.get('quality_reasons')}")
    print(f"  pulse_score: {report.pulse_score if isinstance(report, MarketPulseReport) else None}")
    print(f"  companies covered: {companies_covered}")
    print(f"  core signals covered/missing: {core_covered} / {core_missing}")
    print(f"  optional signals covered/missing: {optional_covered} / {optional_missing}")
    print(f"  evidence_count: {quality_audit.get('fact_count')}")
    print(f"  source_count: {quality_audit.get('source_count')}")
    print(f"  pricing_pressure document count: {pricing_doc_count}")
    print(f"  Bright Data calls estimate: {brightdata_calls}")
    print(f"  zero-doc query rate: {quality_audit.get('zero_doc_query_rate')}")
    print(f"  top 5 evidence-backed signals: {signal_counts.most_common(5)}")
    print(f"  watch list items: {len(watch_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
