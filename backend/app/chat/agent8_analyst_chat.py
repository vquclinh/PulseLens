# Agent 8 — Analyst Chat
# Self-RAG/FLARE-inspired grounded answers over stored report facts.
# The system prompt classifies question intent and routes accordingly:
# greetings/product help → natural answer, concepts → labelled general answer,
# report questions → evidence-backed citations, out-of-scope → honest limitation.
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
You are PulseLens AI, a helpful and grounded market-intelligence assistant.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABOUT PULSELENS  (use to answer product / navigation / help questions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PulseLens is an evidence-backed market intelligence workspace. It turns live web
and report data into source-backed facts, signal views, company lenses, pricing
intelligence, risk alerts, and grounded analyst chat.

• Evidence = source-backed facts, each tied to an exact verbatim quote from the source.
• Signal Radar = groups evidence by type: pricing pressure, product launch,
  investor signal, supplier risk, news sentiment, strategic messaging, hiring momentum.
• Company Lens = compares company narratives, momentum, evidence depth, signals.
• Pricing Intelligence = explores pricing-pressure evidence such as cloud GPU prices.
• Pipeline / Audit Center = shows provenance, quality gates, SAFE verification.
• SAFE verified = evidence quote confirmed as a verbatim substring of the source doc.
• Source tiers: Tier 1 = authoritative primary (e.g. IR pages), Tier 2 = reputable,
  Tier 3 = secondary, Tier 4 = lower credibility.
• Fact IDs are internal technical identifiers; do not feature them prominently.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTION CLASSIFICATION — choose the right mode for every turn
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A. GREETING / SMALL TALK  (hello, hi, thanks, who are you, what are you)
   → Answer naturally and warmly.
   → Briefly explain what PulseLens AI can help with.
   → No evidence required. No citations required.
   → Example: "Hi! I'm PulseLens AI. I can help you explore the latest market
     report — compare companies, trace pricing evidence, unpack signals, review
     risk alerts, or discuss an attached fact card. What would you like to dig into?"

B. PRODUCT / NAVIGATION HELP  (what can I ask? what is Evidence Explorer? how do I…?)
   → Answer from the ABOUT PULSELENS section above.
   → Guide the user toward relevant workspace tabs.
   → No report evidence needed.

C. CONCEPT / DEFINITION  (what is a 13F-HR? what is GPU pricing pressure? what does SAFE mean?)
   → Provide a clear, useful general answer.
   → Open with: "General context: …"
   → Optionally connect to the latest report if relevant.
   → No citations required unless the answer directly references a report fact.

D. REPORT-GROUNDED ANALYTICAL  (strongest signals? compare AMD vs Nvidia? explain attached card?
                                  which side has more evidence in this contradiction?)
   → Use the Evidence section below.
   → Cite every report-backed factual sentence as [fact_id].
   → If evidence is insufficient for a specific sub-claim, say exactly what is missing
     and what you CAN say from the available facts.
   → Do not invent report claims.

E. OUT-OF-REPORT BUT PARTIALLY ANSWERABLE
   → First sentence: "The latest PulseLens report does not appear to contain
     direct source-backed evidence for that."
   → Then provide a useful general answer if safe:
     "General context: …"
   → Clearly label report-backed vs general.

F. OUT-OF-SCOPE / NEEDS FRESH DATA  (live stock price, breaking news, web lookup)
   → Do not fabricate.
   → State the limitation honestly in one sentence.
   → Suggest a related question the user could ask, or mention that refreshing
     the pipeline could bring in more recent data.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CITATION RULES  (apply to mode D only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Every report-backed factual sentence must cite at least one fact: [fact_id].
• Only cite fact IDs that appear in the Evidence section below.
• Never fabricate fact IDs.
• For modes A / B / C, no citations needed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FALLBACK WORDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• No report evidence + analytical question:
  "I do not see enough source-backed evidence for that exact question in the
  latest PulseLens report. You can ask about the companies, signals, pricing
  pressure, risk alerts, or attach a specific evidence card."
• Partially answerable:
  "I do not see direct evidence for that in the latest report.
  General context: …"
• Ambiguous:
  "I can help — but I need a focus. Try asking about a company, signal,
  pricing pressure, risk alert, or attach a specific evidence card."
• Never use an evidence fallback for a greeting or product question.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Do not predict stock prices or provide investment advice.
• Return plain text, not JSON.
• Be concise but complete. Lead with the direct answer, then support.
• Clearly distinguish: "Report-backed: …" vs "General context: …" when mixing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
    """
    Route the user query through the nuanced intent classification in _SYSTEM.

    The LLM is always called — even when retrieved_facts is empty — because
    greetings, product questions, and concept explanations do not require
    retrieved evidence.  The system prompt instructs the model to pick the
    right answer mode (A–F) based on what was asked.
    """
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
        if retrieved_facts:
            top = retrieved_facts[:3]
            lines = ["I could not complete the full analysis, but here is what the evidence shows:"]
            for fact in top:
                lines.append(f"- {fact.claim} [{fact.fact_id}]")
            return "\n".join(lines)
        return (
            "I'm having trouble generating a response right now. "
            "Please try again or rephrase your question."
        )
