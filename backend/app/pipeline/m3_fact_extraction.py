# M3: Extracts structured FactObjects from raw documents using LLM + validates quotes verbatim
from typing import List
from app.schemas.models import RawDocument, FactObject
from app.utils.llm_client import LLMClient
from app.utils.finbert_client import FinBERTClient
from app.config.companies import COMPANIES


async def extract_facts(documents: List[RawDocument]) -> List[FactObject]:
    pass


def validate_fact(fact: FactObject, source: RawDocument) -> bool:
    pass
