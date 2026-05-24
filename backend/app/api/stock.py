# Stock API — GET /api/stock/{ticker} returns Alpha Vantage price context with 4-hour cache
from fastapi import APIRouter
from app.schemas.models import StockContext

router = APIRouter(prefix="/api")


@router.get("/stock/{ticker}", response_model=StockContext)
async def get_stock(ticker: str):
    pass
