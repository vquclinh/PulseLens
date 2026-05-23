# M2: Fetches raw web content via Bright Data, assigns source tiers, caches results
from typing import List
from app.schemas.models import SearchQuery, RawDocument
from app.config.source_tiers import assign_tier
from app.utils.brightdata_client import BrightDataClient


async def collect_documents(queries: List[SearchQuery]) -> List[RawDocument]:
    pass
