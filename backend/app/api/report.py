# Report API — POST /api/run triggers pipeline, GET /api/report/{id} returns report JSON
from fastapi import APIRouter
from app.schemas.models import MarketPulseReport

router = APIRouter(prefix="/api")


@router.post("/run")
async def run_pipeline():
    pass


@router.get("/report/{report_id}", response_model=MarketPulseReport)
async def get_report(report_id: str):
    pass
