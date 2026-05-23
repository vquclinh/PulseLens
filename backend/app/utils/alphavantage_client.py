# Alpha Vantage API wrapper with 4-hour diskcache for stock price context
import httpx
import diskcache
from app.schemas.models import StockContext


class AlphaVantageClient:
    def __init__(self, api_key: str, cache_dir: str = ".cache/alphavantage") -> None:
        pass

    async def get_quote(self, ticker: str) -> StockContext:
        pass

    async def get_daily_series(self, ticker: str, days: int = 7) -> dict:
        pass
