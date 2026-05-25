# Alpha Vantage API wrapper with 4-hour diskcache for stock price context
from __future__ import annotations

import os
from pathlib import Path

import diskcache
import httpx

from app.config.companies import COMPANIES
from app.schemas.models import StockContext


class AlphaVantageClient:
    def __init__(self, api_key: str, cache_dir: str = ".cache/alphavantage") -> None:
        if not api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY is required")
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        cache_path = Path(cache_dir)
        if not cache_path.is_absolute():
            cache_path = Path(__file__).resolve().parents[2] / cache_path
        self.cache = diskcache.Cache(str(cache_path))

    @classmethod
    def from_env(cls) -> "AlphaVantageClient":
        return cls(
            api_key=os.getenv("ALPHA_VANTAGE_API_KEY", ""),
            cache_dir=os.getenv("ALPHA_VANTAGE_CACHE_DIR", "cache/alphavantage"),
        )

    async def get_quote(self, ticker: str) -> StockContext:
        symbol = ticker.upper().strip()
        cache_key = f"quote:{symbol}"
        cached = self.cache.get(cache_key)
        if isinstance(cached, StockContext):
            return cached
        if isinstance(cached, dict):
            return StockContext.model_validate(cached)

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                self.base_url,
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self.api_key,
                },
            )
            response.raise_for_status()
            payload = response.json()

        quote = payload.get("Global Quote", {}) if isinstance(payload, dict) else {}
        price = _to_float(quote.get("05. price"))
        change_pct = _parse_percent(quote.get("10. change percent"))
        daily = await self.get_daily_series(symbol)

        context = StockContext(
            company=_company_for_ticker(symbol),
            ticker=symbol,
            price_current=price,
            price_7d_change_pct=change_pct,
            price_7d_high=daily.get("high"),
            price_7d_low=daily.get("low"),
            signal_detected_date=None,
            price_move_date=None,
            signal_lead_days=None,
            lead_time_note="Stock context only — not investment advice.",
        )
        self.cache.set(cache_key, context.model_dump(mode="json"), expire=4 * 60 * 60)
        return context

    async def get_daily_series(self, ticker: str, days: int = 7) -> dict:
        symbol = ticker.upper().strip()
        cache_key = f"daily:{symbol}:{days}"
        cached = self.cache.get(cache_key)
        if isinstance(cached, dict):
            return cached

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                self.base_url,
                params={
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "apikey": self.api_key,
                    "outputsize": "compact",
                },
            )
            response.raise_for_status()
            payload = response.json()

        series = payload.get("Time Series (Daily)", {}) if isinstance(payload, dict) else {}
        rows = list(series.values())[:days] if isinstance(series, dict) else []
        highs = [_to_float(row.get("2. high")) for row in rows if isinstance(row, dict)]
        lows = [_to_float(row.get("3. low")) for row in rows if isinstance(row, dict)]
        highs = [value for value in highs if value is not None]
        lows = [value for value in lows if value is not None]
        result = {
            "high": max(highs) if highs else None,
            "low": min(lows) if lows else None,
        }
        self.cache.set(cache_key, result, expire=4 * 60 * 60)
        return result


def _company_for_ticker(ticker: str) -> str:
    for company in COMPANIES:
        if company.ticker.upper() == ticker.upper():
            return company.name
    return ticker.upper()


def _to_float(value: object) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _parse_percent(value: object) -> float | None:
    if value is None:
        return None
    return _to_float(str(value).replace("%", ""))
