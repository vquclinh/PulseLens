# Agent 7 — Watch List Builder
# Produces forward indicators from unresolved, evidence-backed signals.
from __future__ import annotations

import asyncio
import json
import logging

from app.schemas.models import MarketNarrative, WatchItem, VerifiedClaim
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

_VALID_URGENCY = {"this_week", "next_2_weeks", "this_month"}

_SYSTEM_PROMPT = """\
Based on the evidence and market narrative, identify
3-5 forward indicators to monitor next week.

Focus ONLY on signals currently developing but unresolved.
Do not invent items not supported by evidence.

For each WatchItem:
  title:                  what to watch (max 10 words)
  rationale:              why it matters (2 sentences)
  trigger:                specific condition to confirm/deny
  signals_pointing_there: fact_ids or claim_ids
  urgency:                this_week | next_2_weeks | this_month

Return ONLY valid JSON array of WatchItem objects.

Market narrative: {market_narrative_json}
Verified claims:  {verified_claims_json}\
"""


def _jsonable(obj: object) -> object:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


def _fallback_items(claims: list[VerifiedClaim]) -> list[WatchItem]:
    items: list[WatchItem] = []
    for claim in sorted(claims, key=lambda c: c.final_confidence, reverse=True)[:3]:
        items.append(
            WatchItem(
                title=f"Monitor {claim.entity} {claim.signal_type.value}",
                rationale=(
                    f"{claim.summary} This signal is verified but still needs follow-up evidence."
                ),
                trigger="New Tier 1 or Tier 2 evidence confirms or contradicts this claim.",
                signals_pointing_there=[claim.claim_id, *claim.supporting_facts[:2]],
                urgency="next_2_weeks",
            )
        )
    return items


def _parse_items(raw: object, claims: list[VerifiedClaim]) -> list[WatchItem]:
    if not isinstance(raw, list):
        raise ValueError(f"Agent 7 returned {type(raw).__name__}, expected list")
    valid_refs = {claim.claim_id for claim in claims}
    for claim in claims:
        valid_refs.update(claim.supporting_facts)

    items: list[WatchItem] = []
    for entry in raw[:5]:
        if not isinstance(entry, dict):
            continue
        try:
            item = WatchItem.model_validate(entry)
        except Exception:
            continue
        if item.urgency not in _VALID_URGENCY:
            continue
        refs = [ref for ref in item.signals_pointing_there if ref in valid_refs]
        if not refs:
            continue
        item.signals_pointing_there = refs
        items.append(item)
    return items


def _build_sync(narrative: MarketNarrative, claims: list[VerifiedClaim]) -> list[WatchItem]:
    llm = LLMClient(agent_name="agent7")
    system = _SYSTEM_PROMPT.format(
        market_narrative_json=narrative.model_dump_json(),
        verified_claims_json=json.dumps([_jsonable(c) for c in claims], ensure_ascii=False),
    )
    raw = llm.call_json(system=system, user="Build the watch list now. Return only JSON.", max_tokens=2048)
    return _parse_items(raw, claims)


async def run_watch_list_builder(
    narrative: MarketNarrative | None,
    claims: list[VerifiedClaim],
) -> MarketNarrative:
    if narrative is None:
        narrative = MarketNarrative(
            narrative_headline="Verified market evidence has been assembled for review.",
            narrative_body="No narrative context was available for watch-list generation.",
            anomalies=[],
            watch_list=[],
        )

    if not claims:
        return narrative.model_copy(update={"watch_list": []})

    try:
        items = await asyncio.to_thread(_build_sync, narrative, claims)
        if not items:
            items = _fallback_items(claims)
    except Exception as exc:
        logger.warning("Agent 7 fallback watch list used: %s", exc)
        items = _fallback_items(claims)

    return narrative.model_copy(update={"watch_list": items})
