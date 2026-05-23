# M6: Synthesizes all 4 intelligence layers into a final MarketPulseReport via LLM
from typing import List
from app.schemas.models import VerifiedClaim, CompanyNarrative, MarketPulseReport
from app.utils.llm_client import LLMClient


async def build_report(
    market: str,
    claims: List[VerifiedClaim],
    company_narratives: List[CompanyNarrative],
    signal_scores: dict,
) -> MarketPulseReport:
    pass
