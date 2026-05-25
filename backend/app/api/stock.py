# Stock API — GET /api/stock/{ticker} returns Alpha Vantage price context with 4-hour cache
from fastapi import APIRouter, HTTPException
from app.schemas.models import StockContext
from app.utils.alphavantage_client import AlphaVantageClient

router = APIRouter(prefix="/api")


@router.get("/stock/{ticker}", response_model=StockContext)
async def get_stock(ticker: str):
    try:
        client = AlphaVantageClient.from_env()
        return await client.get_quote(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
