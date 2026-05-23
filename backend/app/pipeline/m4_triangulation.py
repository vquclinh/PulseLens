# M4: Groups facts into verified claims, enforces corroboration >= 2, flags contradictions
from typing import List
from app.schemas.models import FactObject, VerifiedClaim


def recency_weight(published_date: str, window_days: int = 7) -> float:
    pass


def weighted_sentiment(facts: List[FactObject]) -> float:
    pass


def build_contradiction_note(facts: List[FactObject]) -> str:
    pass


async def triangulate(facts: List[FactObject]) -> List[VerifiedClaim]:
    pass
