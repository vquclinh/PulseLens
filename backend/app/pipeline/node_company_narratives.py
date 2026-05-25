# Node — Company Narratives
# Builds Layer 2 company cards from verified claims and M5 company scores.
from __future__ import annotations

import asyncio
import json
import logging
import re
from statistics import mean
from typing import Any

from app.config.companies import COMPANIES, Company
from app.schemas.models import CompanyNarrative, MomentumLabel, VerifiedClaim
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

_CLAIM_REF_RE = re.compile(r"\[(claim_[A-Za-z0-9_]+)\]")

_SYSTEM_PROMPT = """\
You are a senior market analyst writing a company card for a dashboard.

Use ONLY the verified claims provided. Do not invent events, products, numbers,
or outlooks. If evidence is thin, say so plainly.

Return ONLY valid JSON matching this schema:
{{
  "narrative": "2-3 concise analyst sentences with [claim_id] citations",
  "key_events": ["max 3 short bullets, each grounded in evidence"],
  "key_drivers": ["max 3 short drivers, each grounded in evidence"],
  "competitive_position": "gaining | holding | losing"
}}

Rules:
- Cite claim IDs exactly as [claim_id] in the narrative.
- Do not predict stock prices.
- Separate evidence from inference.
- If signals conflict, mention the tension directly.

Company: {company}
Ticker: {ticker}
Momentum score: {momentum_score}
Momentum label: {momentum_label}
Signal scores: {signal_scores_json}
Verified claims: {claims_json}\
"""


def _jsonable(obj: object) -> object:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


def _company_by_name(name: str) -> Company | None:
    return next((company for company in COMPANIES if company.name == name), None)


def _company_scores(signal_scores: dict[str, Any], company: str) -> dict[str, Any]:
    breakdown = signal_scores.get("breakdown", {})
    if not isinstance(breakdown, dict):
        return {}
    by_company = breakdown.get("by_company", {})
    if not isinstance(by_company, dict):
        return {}
    item = by_company.get(company, {})
    return item if isinstance(item, dict) else {}


def _momentum_label(score: int, claims: list[VerifiedClaim]) -> MomentumLabel:
    if claims and any(claim.is_contradicted for claim in claims):
        return MomentumLabel.mixed
    if score >= 75:
        return MomentumLabel.strong_positive
    if score >= 60:
        return MomentumLabel.positive
    if score >= 45:
        return MomentumLabel.neutral
    if any(claim.signal_type.value == "supplier_risk" for claim in claims):
        return MomentumLabel.elevated_risk
    return MomentumLabel.negative


def _default_competitive_position(company: str, signal_scores: dict[str, Any]) -> str:
    breakdown = signal_scores.get("breakdown", {})
    by_company = breakdown.get("by_company", {}) if isinstance(breakdown, dict) else {}
    if not isinstance(by_company, dict) or company not in by_company:
        return "holding"

    ranked = sorted(
        (
            (name, float(data.get("pulse_score", 50.0)))
            for name, data in by_company.items()
            if isinstance(data, dict)
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    if not ranked:
        return "holding"
    index = [name for name, _score in ranked].index(company)
    if index < max(1, len(ranked) // 3):
        return "gaining"
    if index >= max(1, len(ranked) * 2 // 3):
        return "losing"
    return "holding"


def _claim_rank(claim: VerifiedClaim) -> float:
    return claim.final_confidence * max(claim.factscore, 0.1) * (claim.recency_score or 0.5)


def _fallback_narrative(
    company: Company,
    claims: list[VerifiedClaim],
    signal_scores: dict[str, Any],
    reason: str | None = None,
) -> CompanyNarrative:
    scores = _company_scores(signal_scores, company.name)
    momentum_score = int(round(float(scores.get("pulse_score", 50.0))))
    top_claims = sorted(claims, key=_claim_rank, reverse=True)[:3]
    label = _momentum_label(momentum_score, claims)
    if top_claims:
        narrative = " ".join(
            f"{claim.summary} [{claim.claim_id}]" for claim in top_claims[:2]
        )
        key_events = [claim.summary for claim in top_claims[:3]]
        key_drivers = sorted({claim.signal_type.value for claim in top_claims})[:3]
    else:
        narrative = f"No verified company-specific claims are available for {company.name} in this report."
        key_events = []
        key_drivers = []
    if reason:
        logger.warning("Company narrative fallback for %s: %s", company.name, reason)
    return CompanyNarrative(
        company=company.name,
        ticker=company.ticker,
        momentum=label,
        momentum_score=momentum_score,
        narrative=narrative,
        key_events=key_events,
        key_drivers=key_drivers,
        competitive_position=_default_competitive_position(company.name, signal_scores),
        supporting_claim_ids=[claim.claim_id for claim in top_claims],
        evidence_count=sum(len(claim.supporting_facts) for claim in claims),
        price_current=None,
        price_change_7d_pct=None,
        signal_lead_days=None,
    )


def _validate_payload(payload: dict[str, Any], valid_claim_ids: set[str]) -> list[str]:
    errors: list[str] = []
    position = payload.get("competitive_position")
    if position not in {"gaining", "holding", "losing"}:
        errors.append("competitive_position must be gaining, holding, or losing")
    narrative = str(payload.get("narrative", ""))
    cited = set(_CLAIM_REF_RE.findall(narrative))
    if valid_claim_ids and not cited:
        errors.append("narrative must cite at least one [claim_id]")
    invalid = cited - valid_claim_ids
    for claim_id in sorted(invalid):
        errors.append(f"invalid claim citation: {claim_id}")
    return errors


def _synthesize_company_sync(
    company: Company,
    claims: list[VerifiedClaim],
    signal_scores: dict[str, Any],
    retry_note: str = "",
) -> dict[str, Any]:
    scores = _company_scores(signal_scores, company.name)
    momentum_score = int(round(float(scores.get("pulse_score", 50.0))))
    label = _momentum_label(momentum_score, claims)
    system = _SYSTEM_PROMPT.format(
        company=company.name,
        ticker=company.ticker,
        momentum_score=momentum_score,
        momentum_label=label.value,
        signal_scores_json=json.dumps(scores, ensure_ascii=False, default=str),
        claims_json=json.dumps([_jsonable(claim) for claim in claims], ensure_ascii=False),
    )
    user = retry_note or "Write the company narrative JSON now."
    return LLMClient(agent_name="agent6").call_json(system, user, max_tokens=1536)


async def _build_one_company(
    company: Company,
    claims: list[VerifiedClaim],
    signal_scores: dict[str, Any],
) -> CompanyNarrative:
    if not claims:
        return _fallback_narrative(company, claims, signal_scores)

    valid_claim_ids = {claim.claim_id for claim in claims}
    scores = _company_scores(signal_scores, company.name)
    momentum_score = int(round(float(scores.get("pulse_score", 50.0))))
    label = _momentum_label(momentum_score, claims)
    top_claims = sorted(claims, key=_claim_rank, reverse=True)[:4]

    try:
        payload = await asyncio.to_thread(_synthesize_company_sync, company, top_claims, signal_scores)
        if not isinstance(payload, dict):
            raise ValueError(f"LLM returned {type(payload).__name__}, expected object")
        errors = _validate_payload(payload, valid_claim_ids)
        if errors:
            retry = (
                "The previous JSON failed validation:\n"
                + "\n".join(f"- {error}" for error in errors)
                + "\nRewrite using only valid [claim_id] citations."
            )
            payload = await asyncio.to_thread(_synthesize_company_sync, company, top_claims, signal_scores, retry)
            if not isinstance(payload, dict):
                raise ValueError(f"retry returned {type(payload).__name__}, expected object")
            errors = _validate_payload(payload, valid_claim_ids)
            if errors:
                raise ValueError("; ".join(errors))

        return CompanyNarrative(
            company=company.name,
            ticker=company.ticker,
            momentum=label,
            momentum_score=momentum_score,
            narrative=str(payload.get("narrative", "")).strip(),
            key_events=[str(item).strip() for item in payload.get("key_events", [])][:3],
            key_drivers=[str(item).strip() for item in payload.get("key_drivers", [])][:3],
            competitive_position=str(payload.get("competitive_position", "holding")),
            supporting_claim_ids=[claim.claim_id for claim in top_claims],
            evidence_count=sum(len(claim.supporting_facts) for claim in claims),
            price_current=None,
            price_change_7d_pct=None,
            signal_lead_days=None,
        )
    except Exception as exc:
        return _fallback_narrative(company, claims, signal_scores, str(exc))


async def build_company_narratives(
    claims: list[VerifiedClaim],
    signal_scores: dict[str, Any],
    companies: list[str] | None = None,
) -> list[CompanyNarrative]:
    selected_names = companies or [company.name for company in COMPANIES]
    selected = [_company_by_name(name) for name in selected_names]
    selected_companies = [company for company in selected if company is not None]
    claims_by_company = {
        company.name: [claim for claim in claims if claim.entity == company.name]
        for company in selected_companies
    }

    narratives = await asyncio.gather(
        *(
            _build_one_company(company, claims_by_company[company.name], signal_scores)
            for company in selected_companies
        )
    )

    logger.info(
        "Company narratives built: %d companies, %.1f avg evidence count",
        len(narratives),
        mean([item.evidence_count for item in narratives]) if narratives else 0.0,
    )
    return list(narratives)
