from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.models import CompanyNarrative, FactObject, MarketPulseReport, VerifiedClaim


class DatabaseAdapter(ABC):

    @abstractmethod
    async def save_report(
        self,
        report: MarketPulseReport,
        facts: list[FactObject] | None = None,
        claims: list[VerifiedClaim] | None = None,
    ) -> None: ...

    @abstractmethod
    async def load_report(self, report_id: str) -> MarketPulseReport | None: ...

    @abstractmethod
    async def latest_report_id(self) -> str | None: ...

    @abstractmethod
    async def list_report_facts(self, report_id: str) -> list[FactObject]: ...

    @abstractmethod
    async def get_fact(self, report_id: str, fact_id: str) -> FactObject | None: ...

    @abstractmethod
    async def get_claim(self, report_id: str, claim_id: str) -> VerifiedClaim | None: ...

    @abstractmethod
    async def search_facts(
        self, report_id: str, query: str, top_k: int = 10
    ) -> list[FactObject]: ...

    @abstractmethod
    async def get_company_narrative(
        self, report_id: str, ticker_or_company: str
    ) -> CompanyNarrative | None: ...

    @abstractmethod
    async def save_chat_message(
        self, session_id: str, role: str, content: str
    ) -> None: ...
