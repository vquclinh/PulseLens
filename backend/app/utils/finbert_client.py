# Placeholder FinBERT client interface. The active pipeline scorer reads FINBERT_MODEL
# from app.config.quality_gates.
from typing import Tuple


class FinBERTClient:
    def __init__(self, device: str = "cpu") -> None:
        self.device = device

    def score(self, text: str) -> Tuple[str, float]:
        return ("neutral", 0.0)
