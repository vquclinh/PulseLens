# Agent 8 — Analyst Chat
# Self-RAG/FLARE-inspired grounded answers over stored report facts.
from __future__ import annotations

import json
import logging
from typing import Iterable

from app.schemas.models import ChatMessage, FactObject, MarketPulseReport
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

MAX_FACTS_IN_CONTEXT = 10
MAX_HISTORY_EXCHANGES = 5

_SYSTEM = """\
You are PulseLens Analyst Chat, a grounded market-intelligence assistant.

Methods: Self-RAG-inspired evidence checking and FLARE-inspired active
retrieval discipline. The retrieval has already provided report facts.

Answer using ONLY the supplied report evidence.
Every factual sentence must cite at least one fact as [fact_id].
If evidence is insufficient, say what is not supported instead of guessing.
Do not predict stock prices or provide investment advice.
Do not cite fact IDs that are not present in the Evidence section.

Return plain text, not JSON.

Report summary:
{report_json}

Evidence:
{evidence}

Attached context (selected by the analyst from the PulseLens Overview):
{context_attachment_block}

Recent history:
{history}
"""


def _build_attachment_block(attachment: dict | None) -> str:
    if not attachment:
        return "None"
    lines = [f"Type: {attachment.get('type', 'unknown')}"]
    for key in (
        "title", "entity", "signal_type", "summary", "rationale", "trigger",
        "urgency", "evidence_quote", "source_domain", "fact_id",
    ):
        val = attachment.get(key)
        if val:
            lines.append(f"{key.replace('_', ' ').title()}: {val}")
    for key in ("supporting_count", "against_count", "source_tier"):
        val = attachment.get(key)
        if val is not None:
            lines.append(f"{key.replace('_', ' ').title()}: {val}")
    conf = attachment.get("confidence")
    if conf is not None:
        lines.append(f"Confidence: {conf:.0%}")
    return "\n".join(lines)


def build_evidence_block(facts: list[FactObject]) -> str:
    rows = []
    for fact in facts[:MAX_FACTS_IN_CONTEXT]:
        rows.append(
            "\n".join(
                [
                    f"[{fact.fact_id}]",
                    f"entity: {fact.entity}",
                    f"signal_type: {fact.signal_type.value}",
                    f"claim: {fact.claim}",
                    f"quote: {fact.evidence_quote}",
                    f"source: {fact.source_url}",
                    f"date: {fact.published_date or 'unknown'}",
                ]
            )
        )
    return "\n\n".join(rows) if rows else "No facts retrieved."


def build_history_block(history: Iterable[ChatMessage] | None) -> str:
    items = list(history or [])[-MAX_HISTORY_EXCHANGES * 2 :]
    if not items:
        return "No prior chat history."
    return "\n".join(f"{msg.role}: {msg.content}" for msg in items)


def _report_context(report: MarketPulseReport | None) -> dict:
    if report is None:
        return {}
    return {
        "report_id": report.report_id,
        "market": report.market,
        "time_window": report.time_window,
        "pulse_score": report.pulse_score,
        "pulse_status": report.pulse_status.value,
        "top_signals": [item.model_dump(mode="json") for item in report.top_signals[:5]],
        "company_narratives": [
            item.model_dump(mode="json") for item in report.company_narratives
        ],
    }


def answer_question(
    query: str,
    retrieved_facts: list[FactObject],
    history: list[ChatMessage] | None = None,
    report: MarketPulseReport | None = None,
    retry_note: str = "",
    context_attachment: dict | None = None,
) -> str:
    if not retrieved_facts:
        return (
            "I do not have enough retrieved evidence in this report to answer that "
            "reliably. Try asking about a company or signal that appears in the report."
        )

    system = _SYSTEM.format(
        report_json=json.dumps(_report_context(report), ensure_ascii=False),
        evidence=build_evidence_block(retrieved_facts),
        context_attachment_block=_build_attachment_block(context_attachment),
        history=build_history_block(history),
    )
    user = retry_note or query
    try:
        return LLMClient(agent_name="agent8").call_text(system, user, max_tokens=1536).strip()
    except Exception as exc:
        logger.warning("Agent 8 failed; using grounded fallback: %s", exc)
        top = retrieved_facts[:3]
        lines = [
            "I could not complete full chat synthesis, but the retrieved evidence shows:"
        ]
        for fact in top:
            lines.append(f"- {fact.claim} [{fact.fact_id}]")
        return "\n".join(lines)
