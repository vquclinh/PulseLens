# Agent 6 — Narrative Synthesizer
# STORM-inspired multi-perspective synthesis over verified claims.
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from app.schemas.models import AnomalyFlag, MarketNarrative, VerifiedClaim
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

_CLAIM_REF_RE = re.compile(r"\[(claim_[A-Za-z0-9_]+)\]")

_SYSTEM_PROMPT = """\
You are a senior market analyst writing for buy-side teams.

Method: STORM multi-perspective synthesis (arXiv:2402.14207)

STEP 1 — Analyze each signal type perspective independently:
  What does hiring data say on its own?
  What does investor signal data say?
  What does pricing data say?
  What does news sentiment say?

STEP 2 — Identify agreements and tensions:
  Where do perspectives align?
  Where do they conflict?
  What is unusual vs expected?

STEP 3 — Synthesize:
  narrative_headline: 1 analyst sentence. No filler.
  narrative_body: 3-5 sentences with cross-signal causality.
                  Each sentence cites >= 1 [claim_id].
  anomalies: patterns that do not fit normal expectations.
  watch_list: [] for this step; Agent 7 fills it.

Rules:
  - Never predict stock prices
  - State conflicts explicitly — do not smooth them over
  - Separate evidence from inference
  - Inferences start with "This may suggest..."

Return ONLY valid JSON matching this schema:
{{
  "narrative_headline": "string",
  "narrative_body": "string with [claim_id] citations",
  "anomalies": [
    {{
      "description": "string",
      "signal_types_involved": ["hiring_momentum"],
      "implication": "string",
      "fact_ids": ["fact_id"]
    }}
  ],
  "watch_list": []
}}

Verified claims:  {verified_claims_json}
Signal scores:    {signal_scores_json}
Company rankings: {company_rankings_json}\
"""


def _jsonable(obj: object) -> object:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


def _company_rankings(signal_scores: dict[str, Any]) -> dict[str, Any]:
    breakdown = signal_scores.get("breakdown", {})
    if isinstance(breakdown, dict):
        by_company = breakdown.get("by_company", {})
        if isinstance(by_company, dict):
            return by_company
    return {}


def _fallback_narrative(claims: list[VerifiedClaim], reason: str | None = None) -> MarketNarrative:
    top_claims = sorted(claims, key=lambda claim: claim.final_confidence, reverse=True)[:3]
    if top_claims:
        cited = " ".join(f"{claim.summary} [{claim.claim_id}]" for claim in top_claims)
        body = f"Verified evidence is available but automated synthesis was limited. {cited}"
    else:
        body = "No verified claims were available for narrative synthesis."
    if reason:
        logger.warning("Agent 6 fallback narrative used: %s", reason)
    return MarketNarrative(
        narrative_headline="Verified market evidence has been assembled for review.",
        narrative_body=body,
        anomalies=[],
        watch_list=[],
    )


def _validate_citations(narrative: MarketNarrative, valid_claim_ids: set[str]) -> list[str]:
    errors: list[str] = []
    cited = set(_CLAIM_REF_RE.findall(narrative.narrative_body))
    invalid = sorted(cited - valid_claim_ids)
    for claim_id in invalid:
        errors.append(f"Invalid claim_id citation: {claim_id}")
    if valid_claim_ids and not cited:
        errors.append("narrative_body must cite at least one [claim_id]")
    return errors


def _parse_narrative(raw: object) -> MarketNarrative:
    if not isinstance(raw, dict):
        raise ValueError(f"Agent 6 returned {type(raw).__name__}, expected object")
    raw.setdefault("watch_list", [])
    raw.setdefault("anomalies", [])
    return MarketNarrative.model_validate(raw)


def _synthesize_sync(
    claims: list[VerifiedClaim],
    signal_scores: dict[str, Any],
    retry_note: str = "",
) -> MarketNarrative:
    llm = LLMClient(agent_name="agent6")
    system = _SYSTEM_PROMPT.format(
        verified_claims_json=json.dumps([_jsonable(c) for c in claims], ensure_ascii=False),
        signal_scores_json=json.dumps(signal_scores, ensure_ascii=False, default=str),
        company_rankings_json=json.dumps(_company_rankings(signal_scores), ensure_ascii=False, default=str),
    )
    user = retry_note or "Write the market narrative now. Return only JSON."
    raw = llm.call_json(system=system, user=user, max_tokens=4096)
    return _parse_narrative(raw)


async def run_narrative_synthesizer(
    claims: list[VerifiedClaim],
    signal_scores: dict[str, Any],
) -> MarketNarrative:
    if not claims:
        return _fallback_narrative(claims)

    valid_claim_ids = {claim.claim_id for claim in claims}
    try:
        narrative = await asyncio.to_thread(_synthesize_sync, claims, signal_scores)
        errors = _validate_citations(narrative, valid_claim_ids)
        if not errors:
            return narrative
        retry_note = (
            "The previous narrative failed validation:\n"
            + "\n".join(f"- {error}" for error in errors)
            + "\nRewrite the narrative using only valid [claim_id] citations."
        )
        narrative = await asyncio.to_thread(_synthesize_sync, claims, signal_scores, retry_note)
        errors = _validate_citations(narrative, valid_claim_ids)
        if errors:
            return _fallback_narrative(claims, "; ".join(errors))
        return narrative
    except Exception as exc:
        return _fallback_narrative(claims, str(exc))
