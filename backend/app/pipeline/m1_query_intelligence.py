# M1: Decomposes a market question into 15-25 targeted sub-queries using Multi-HyDE
from typing import List
from app.schemas.models import SearchQuery, SignalType
from app.config.companies import COMPANIES
from app.config.signal_types import SIGNAL_WEIGHTS

QUERY_TEMPLATES: dict = {}


async def generate_queries(market: str) -> List[SearchQuery]:
    pass
