# Agent 5 — Contradiction Writers
# LLM via OpenRouter writes a symmetric analyst note for each contradicted (entity, signal_type) pair.
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from app.schemas.models import ContradictionFlag, FactObject, VerifiedClaim
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

_MAX_CONCURRENT = 5

_SYSTEM = """\
You are writing a contradiction note for a financial intelligence report.
Present BOTH sides accurately and symmetrically.
Do NOT lean toward either interpretation.
Do NOT blend the conflicting signals into a neutral statement.
Do NOT editorialize or add your own interpretation.
End with: "Recommend manual review before acting on this signal."

Entity:            {entity}
Signal type:       {signal_type}
Positive evidence: {positive_facts_json}
Negative evidence: {negative_facts_json}

Return: a single paragraph, max 100 words.\
"""


def _build_prompt(
    flag: ContradictionFlag,
    facts_by_id: dict[str, FactObject],
) -> str:
    def _fact_to_str(fid: str) -> str:
        f = facts_by_id.get(fid)
        if f is None:
            return fid
        return f.claim

    pos_claims = [_fact_to_str(fid) for fid in flag.positive_facts]
    neg_claims = [_fact_to_str(fid) for fid in flag.negative_facts]

    return _SYSTEM.format(
        entity=flag.entity,
        signal_type=flag.signal_type.value,
        positive_facts_json=json.dumps(pos_claims, ensure_ascii=False),
        negative_facts_json=json.dumps(neg_claims, ensure_ascii=False),
    )


def _write_note(flag: ContradictionFlag, facts_by_id: dict[str, FactObject]) -> str:
    """Synchronous LLM call — run via asyncio.to_thread."""
    llm = LLMClient(agent_name="agent5")
    prompt = _build_prompt(flag, facts_by_id)
    try:
        note = llm.call_text(prompt, "", max_tokens=256).strip()
    except Exception as exc:
        logger.warning("Agent 5 LLM failed for %s/%s: %s", flag.entity, flag.signal_type.value, exc)
        note = (
            f"Conflicting signals detected for {flag.entity} {flag.signal_type.value}. "
            "Recommend manual review before acting on this signal."
        )
    # Enforce max 100-word limit — truncate at sentence boundary if needed
    words = note.split()
    if len(words) > 100:
        note = " ".join(words[:100])
        if not note.endswith("."):
            note = note.rstrip(",;:") + "."
    return note


async def write_contradiction_notes(
    flags: list[ContradictionFlag],
    scored_facts: list[FactObject],
    verified_claims: list[VerifiedClaim],
) -> tuple[list[ContradictionFlag], list[VerifiedClaim]]:
    """
    For each ContradictionFlag: call LLM (concurrently, bounded) to produce a ≤100-word note.
    Updates ContradictionFlag.note and the matching VerifiedClaim.contradiction_note in-place.
    Returns the updated lists.
    """
    if not flags:
        return flags, verified_claims

    facts_by_id = {f.fact_id: f for f in scored_facts}

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def _process(flag: ContradictionFlag) -> tuple[ContradictionFlag, str]:
        async with semaphore:
            note = await asyncio.to_thread(_write_note, flag, facts_by_id)
        return flag, note

    results = await asyncio.gather(*(_process(f) for f in flags))

    # Build lookup: (entity, signal_type) → note
    note_map: dict[tuple[str, str], str] = {}
    for flag, note in results:
        flag.note = note
        note_map[(flag.entity, flag.signal_type.value)] = note
        logger.info(
            "Agent 5 wrote contradiction note for %s/%s (%d words)",
            flag.entity, flag.signal_type.value, len(note.split()),
        )

    # Propagate notes onto VerifiedClaims
    for vc in verified_claims:
        key = (vc.entity, vc.signal_type.value)
        if vc.is_contradicted and key in note_map:
            vc.contradiction_note = note_map[key]

    return flags, verified_claims


# ── Standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from app.schemas.models import SignalType, FactObject, ContradictionFlag, VerifiedClaim

    # Mock data ── two contradicted (entity, signal_type) pairs
    mock_facts = [
        FactObject(
            fact_id="f001", doc_id="d1", entity="Nvidia", signal_type=SignalType.hiring_momentum,
            claim="Nvidia posted 3,200 new job openings in Q1 2025, primarily in AI infrastructure.",
            evidence_quote="3,200 new job openings", source_url="https://careers.nvidia.com", source_tier=1,
            published_date="2025-03-15", sentiment="positive", sentiment_score=0.91, confidence=0.95,
            safe_verified=True,
        ),
        FactObject(
            fact_id="f002", doc_id="d2", entity="Nvidia", signal_type=SignalType.hiring_momentum,
            claim="Nvidia cut 500 positions from its data-center division in February 2025.",
            evidence_quote="cut 500 positions", source_url="https://reuters.com/nvidia", source_tier=2,
            published_date="2025-02-20", sentiment="negative", sentiment_score=-0.84, confidence=0.88,
            safe_verified=True,
        ),
        FactObject(
            fact_id="f003", doc_id="d3", entity="AMD", signal_type=SignalType.pricing_pressure,
            claim="AMD reduced MI300X list prices by 12% in response to Nvidia H100 competition.",
            evidence_quote="reduced MI300X list prices by 12%", source_url="https://amd.com/ir", source_tier=1,
            published_date="2025-04-01", sentiment="negative", sentiment_score=-0.77, confidence=0.92,
            safe_verified=True,
        ),
        FactObject(
            fact_id="f004", doc_id="d4", entity="AMD", signal_type=SignalType.pricing_pressure,
            claim="AMD raised MI300X enterprise pricing by $2,000 per unit following strong Q1 demand.",
            evidence_quote="raised MI300X enterprise pricing by $2,000", source_url="https://bloomberg.com/amd", source_tier=2,
            published_date="2025-04-10", sentiment="positive", sentiment_score=0.72, confidence=0.87,
            safe_verified=True,
        ),
    ]

    mock_flags = [
        ContradictionFlag(
            entity="Nvidia", signal_type=SignalType.hiring_momentum,
            positive_facts=["f001"], negative_facts=["f002"], note="",
        ),
        ContradictionFlag(
            entity="AMD", signal_type=SignalType.pricing_pressure,
            positive_facts=["f004"], negative_facts=["f003"], note="",
        ),
    ]

    mock_claims = [
        VerifiedClaim(
            claim_id="vc1", entity="Nvidia", signal_type=SignalType.hiring_momentum,
            summary="Nvidia hiring signals are contradicted",
            supporting_facts=["f001", "f002"], corroboration_count=2,
            source_tiers_present=[1, 2], weighted_sentiment=0.2, recency_score=0.8,
            final_confidence=0.91, factscore=0.85, is_contradicted=True, contradiction_note=None,
        ),
        VerifiedClaim(
            claim_id="vc2", entity="AMD", signal_type=SignalType.pricing_pressure,
            summary="AMD pricing pressure signals are contradicted",
            supporting_facts=["f003", "f004"], corroboration_count=2,
            source_tiers_present=[1, 2], weighted_sentiment=-0.05, recency_score=0.7,
            final_confidence=0.89, factscore=0.82, is_contradicted=True, contradiction_note=None,
        ),
    ]

    async def main() -> None:
        print("\n── Agent 5: writing contradiction notes ────────────────────")
        print(f"  {len(mock_flags)} contradicted pairs, {len(mock_facts)} mock facts\n")

        updated_flags, updated_claims = await write_contradiction_notes(
            mock_flags, mock_facts, mock_claims
        )

        for flag in updated_flags:
            print(f"  [{flag.entity} / {flag.signal_type.value}]")
            print(f"  note ({len(flag.note.split())} words):")
            print(f"    {flag.note}")
            print()

        print("── VerifiedClaim contradiction_note propagation ─────────────")
        for vc in updated_claims:
            print(f"  {vc.claim_id}: contradiction_note set = {vc.contradiction_note is not None}")
            if vc.contradiction_note:
                print(f"    {vc.contradiction_note[:80]}…")
            print()

        # Verify postconditions
        assert all(f.note for f in updated_flags), "Some flags have empty notes"
        assert all("Recommend manual review" in f.note for f in updated_flags), \
            "Closing sentence missing from some notes"
        assert all(vc.contradiction_note is not None for vc in updated_claims), \
            "Some VerifiedClaims missing contradiction_note"
        print("✅ All assertions passed")

    asyncio.run(main())
