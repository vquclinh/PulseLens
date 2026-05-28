from __future__ import annotations

from app.db import database as _db
from app.db.adapter import DatabaseAdapter
from app.schemas.models import CompanyNarrative, FactObject, MarketPulseReport, VerifiedClaim


class SQLiteAdapter(DatabaseAdapter):

    async def save_report(
        self,
        report: MarketPulseReport,
        facts: list[FactObject] | None = None,
        claims: list[VerifiedClaim] | None = None,
    ) -> None:
        return await _db.save_report(report, facts, claims)

    async def load_report(self, report_id: str) -> MarketPulseReport | None:
        return await _db.load_report(report_id)

    async def latest_report_id(self) -> str | None:
        return await _db.latest_report_id()

    async def list_report_facts(self, report_id: str) -> list[FactObject]:
        return await _db.list_report_facts(report_id)

    async def get_fact(self, report_id: str, fact_id: str) -> FactObject | None:
        return await _db.get_fact(report_id, fact_id)

    async def get_claim(self, report_id: str, claim_id: str) -> VerifiedClaim | None:
        return await _db.get_claim(report_id, claim_id)

    async def search_facts(
        self, report_id: str, query: str, top_k: int = 10
    ) -> list[FactObject]:
        return await _db.search_facts(report_id, query, top_k)

    async def get_company_narrative(
        self, report_id: str, ticker_or_company: str
    ) -> CompanyNarrative | None:
        return await _db.get_company_narrative(report_id, ticker_or_company)

    async def save_chat_message(
        self, session_id: str, role: str, content: str
    ) -> None:
        return await _db.save_chat_message(session_id, role, content)
