# Report API — POST /api/run triggers pipeline, GET /api/report/{id} returns report JSON
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.companies import COMPANIES
from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
from app.db.database import load_report, list_report_facts, latest_report_id
from app.pipeline.graph import pipeline_graph
from app.schemas.models import FactObject, MarketPulseReport
from app.utils.helpers import generate_uuid

router = APIRouter(prefix="/api")


class RunPipelineRequest(BaseModel):
    market: str | None = None
    companies: list[str] | None = None
    time_window: str | None = None


@router.post("/run")
async def run_pipeline(request: RunPipelineRequest):
    state = {
        "market": request.market or DEFAULT_MARKET,
        "companies": request.companies or [company.name for company in COMPANIES],
        "time_window": request.time_window or DEFAULT_TIME_WINDOW,
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
    config = {"configurable": {"thread_id": f"run-{generate_uuid()[:12]}"}}
    result = await pipeline_graph.ainvoke(state, config=config)
    report = result.get("report")
    if report is None:
        raise HTTPException(status_code=500, detail={"errors": result.get("errors", [])})
    return {
        "report_id": report.report_id,
        "pulse_score": report.pulse_score,
        "pulse_status": report.pulse_status.value,
        "quality_status": report.quality_status.value,
    }


@router.get("/reports/latest")
async def get_latest_report():
    """Returns the most recent pipeline report_id so the UI can auto-load it."""
    rid = await latest_report_id()
    if rid is None:
        raise HTTPException(status_code=404, detail="No reports found")
    return {"report_id": rid}


@router.get("/report/{report_id}", response_model=MarketPulseReport)
async def get_report(report_id: str):
    report = await load_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
    return report


@router.get("/report/{report_id}/facts", response_model=list[FactObject])
async def get_report_facts(report_id: str):
    report = await load_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
    return await list_report_facts(report_id)
