# Report API — POST /api/run triggers pipeline, GET /api/report/{id} returns report JSON
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.companies import COMPANIES
from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
from app.db.database import load_report
from app.pipeline.graph import pipeline_graph
from app.schemas.models import MarketPulseReport
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
    config = {"configurable": {"thread_id": f"run-{generate_uuid()[:12]}"}}
    result = await pipeline_graph.ainvoke(state, config=config)
    report = result.get("report")
    if report is None:
        raise HTTPException(status_code=500, detail={"errors": result.get("errors", [])})
    return {
        "report_id": report.report_id,
        "pulse_score": report.pulse_score,
        "pulse_status": report.pulse_status.value,
    }


@router.get("/report/{report_id}", response_model=MarketPulseReport)
async def get_report(report_id: str):
    report = await load_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
    return report
