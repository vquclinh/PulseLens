# Node — Report Assembler
# Converts the final pipeline state into a MarketPulseReport and persists it.
from __future__ import annotations

from statistics import mean
from typing import Any

from app.config.signal_types import SIGNAL_WEIGHTS
from app.db.database import save_report
from app.pipeline.state import PipelineState
from app.schemas.models import (
    CitedStatement,
    FactObject,
    GroundedBrief,
    MarketNarrative,
    MarketPulseReport,
    NewsItem,
    PipelineAuditSummary,
    PulseStatus,
    QualityStatus,
    SignalSummary,
    SignalType,
    VerifiedClaim,
)
from app.utils.helpers import extract_domain, generate_uuid, now_iso


def _signal_breakdown(scores: dict[str, Any]) -> dict[str, float]:
    breakdown = scores.get("breakdown", {})
    if isinstance(breakdown, dict) and isinstance(breakdown.get("by_signal"), dict):
        return {str(k): float(v) for k, v in breakdown["by_signal"].items()}
    if isinstance(breakdown, dict):
        return {str(k): float(v) for k, v in breakdown.items() if isinstance(v, (int, float))}
    return {}


def _pulse_status(value: object) -> PulseStatus:
    if isinstance(value, PulseStatus):
        return value
    try:
        return PulseStatus(str(value))
    except ValueError:
        return PulseStatus.stable


def build_top_signals(
    claims: list[VerifiedClaim],
    scores: dict[str, Any],
    facts: list[FactObject],
) -> list[SignalSummary]:
    by_signal = _signal_breakdown(scores)
    facts_by_id = {fact.fact_id: fact for fact in facts}
    ranked = sorted(
        SIGNAL_WEIGHTS.keys(),
        key=lambda signal: abs(by_signal.get(signal, 0.0) * SIGNAL_WEIGHTS[signal]),
        reverse=True,
    )[:5]

    summaries: list[SignalSummary] = []
    for signal in ranked:
        relevant = [claim for claim in claims if claim.signal_type.value == signal]
        fact_ids = [fid for claim in relevant for fid in claim.supporting_facts]
        source_count = len({
            facts_by_id[fid].source_url for fid in fact_ids if fid in facts_by_id
        })
        confidence = mean([claim.final_confidence for claim in relevant]) if relevant else 0.0
        narrative = relevant[0].summary if relevant else "No verified claims yet for this signal."
        summaries.append(
            SignalSummary(
                signal_type=SignalType(signal),
                score=round(by_signal.get(signal, 0.0), 4),
                source_count=source_count,
                confidence=round(confidence, 3),
                narrative=narrative,
                is_contradicted=any(claim.is_contradicted for claim in relevant),
            )
        )
    return summaries


def build_news_items(facts: list[FactObject]) -> list[NewsItem]:
    sorted_facts = sorted(facts, key=lambda fact: abs(fact.sentiment_score), reverse=True)
    return [
        NewsItem(
            item_id=f"news_{generate_uuid()[:12]}",
            headline=fact.claim,
            summary=fact.evidence_quote[:240],
            source_url=fact.source_url,
            domain=extract_domain(fact.source_url),
            source_tier=fact.source_tier,
            published_date=fact.published_date,
            sentiment=fact.sentiment,
            fact_ids=[fact.fact_id],
        )
        for fact in sorted_facts[:10]
    ]


def build_grounded_brief(claims: list[VerifiedClaim], quality_status: str, quality_reasons: list[str]) -> GroundedBrief:
    top = sorted(claims, key=lambda claim: claim.final_confidence, reverse=True)[:3]
    implication = f"Analysis based on {len(claims)} verified claims."
    if quality_status == QualityStatus.PARTIAL_PASS.value:
        implication += " Coverage is incomplete; treat conclusions as usable but provisional."
        if quality_reasons:
            implication += " Key gaps: " + "; ".join(quality_reasons[:3]) + "."
    return GroundedBrief(
        what_we_found=[
            CitedStatement(text=claim.summary, fact_ids=claim.supporting_facts[:2])
            for claim in top
        ],
        what_we_infer=[],
        strategic_implication=implication,
    )


def _fallback_narrative(claims: list[VerifiedClaim]) -> MarketNarrative:
    return MarketNarrative(
        narrative_headline="PulseLens has assembled the verified evidence for this market.",
        narrative_body=(
            f"The current report contains {len(claims)} verified claims. "
            "Narrative synthesis was not available for this run."
        ),
        anomalies=[],
        watch_list=[],
    )


def _quality_status(value: object) -> QualityStatus:
    if isinstance(value, QualityStatus):
        return value
    try:
        return QualityStatus(str(value))
    except ValueError:
        return QualityStatus.PARTIAL_PASS


def _build_audit_summary(state: PipelineState, facts: list[FactObject]) -> PipelineAuditSummary:
    web_audit = state.get("web_collection_audit") or {}
    fetch_summary = state.get("fetch_error_summary") or {}
    query_audits = web_audit.get("queries") if isinstance(web_audit, dict) else []
    query_count = len(query_audits) if isinstance(query_audits, list) else int(web_audit.get("query_count") or 0)
    zero_doc_count = (
        sum(1 for item in query_audits if int(item.get("accepted_doc_count") or 0) == 0)
        if isinstance(query_audits, list) else int(web_audit.get("zero_doc_query_count") or 0)
    )
    return PipelineAuditSummary(
        query_count=query_count or len(state.get("queries") or []),
        accepted_doc_count=len(state.get("raw_documents") or []),
        failed_query_count=int(web_audit.get("failed_query_count") or zero_doc_count),
        zero_doc_query_count=zero_doc_count,
        fetch_error_count=int(fetch_summary.get("failed_fetches") or 0),
        covered_signal_types=[SignalType(s) for s in state.get("covered_signal_types", []) if s in {st.value for st in SignalType}],
        missing_signal_types=[SignalType(s) for s in state.get("missing_signal_types", []) if s in {st.value for st in SignalType}],
        source_count=len({fact.source_url for fact in facts}),
        evidence_count=len(facts),
    )


def _mark_partial_narrative(narrative: MarketNarrative, reasons: list[str]) -> MarketNarrative:
    if narrative.narrative_body.startswith("Coverage incomplete:"):
        return narrative
    reason_text = "; ".join(reasons[:3]) if reasons else "quality thresholds were not fully met"
    narrative.narrative_body = (
        f"Coverage incomplete: this report is usable but provisional because {reason_text}. "
        + narrative.narrative_body
    )
    return narrative


async def report_assembler(state: PipelineState) -> dict:
    claims = state.get("verified_claims") or []
    scores = state.get("signal_scores") or {}
    facts = state.get("scored_facts") or []
    market_narrative = state.get("market_narrative") or _fallback_narrative(claims)
    quality_status = _quality_status(state.get("quality_status", QualityStatus.PARTIAL_PASS.value))
    quality_reasons = list(state.get("quality_reasons") or [])
    if quality_status == QualityStatus.PARTIAL_PASS:
        market_narrative = _mark_partial_narrative(market_narrative, quality_reasons)

    pulse_confidence = float(scores.get("pulse_confidence", 0.0))
    if quality_status == QualityStatus.PARTIAL_PASS:
        pulse_confidence = min(pulse_confidence, 0.5)

    report = MarketPulseReport(
        report_id=f"report_{generate_uuid()[:12]}",
        market=state.get("market", "US AI Hardware / Semiconductor"),
        time_window=state.get("time_window", "last 7 days"),
        generated_at=now_iso(),
        pulse_score=float(scores.get("pulse_score", 0.0)),
        pulse_status=_pulse_status(scores.get("pulse_status", PulseStatus.stable)),
        pulse_confidence=pulse_confidence,
        trend_vs_previous=None,
        top_signals=build_top_signals(claims, scores, facts),
        company_narratives=state.get("company_narratives") or [],
        news_items=build_news_items(facts),
        market_narrative=market_narrative,
        contradictions=state.get("contradictions") or [],
        grounded_brief=build_grounded_brief(claims, quality_status.value, quality_reasons),
        evidence_count=len(facts),
        source_count=len({fact.source_url for fact in facts}),
        signal_breakdown=_signal_breakdown(scores),
        quality_status=quality_status,
        quality_reasons=quality_reasons,
        audit_summary=_build_audit_summary(state, facts),
    )

    await save_report(report, facts, claims)
    return {"report": report}
