# Node — validate_fact + SAFE atomic verification (arXiv:2403.18802)
#
# Two sequential gates between Agent 3 output and FinBERT scoring:
#   1. validate_facts()       — pure Python verbatim check (fastest, no LLM cost)
#   2. run_safe_verification() — LLM atomic decomposition + support check
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.config.companies import KNOWN_ENTITIES
from app.schemas.models import FactObject, RawDocument
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

_MIN_CONFIDENCE = 0.6
_MIN_SUPPORT_RATIO = 0.5   # SAFE threshold: discard if < 50% atomic claims supported
_MAX_CONCURRENT_SAFE = 5   # SAFE is expensive (2+ LLM calls per fact)

# ── Gate 1: pure Python verbatim check ────────────────────────────────────────


def validate_facts(
    raw_facts: list[FactObject],
    docs_by_id: dict[str, RawDocument],
) -> list[FactObject]:
    """
    CRITICAL anti-hallucination gate (ARCHITECTURE.md §5).

    Checks in order (cheapest first):
      1. evidence_quote is a VERBATIM substring of source.content
         (LLM invented the quote → discard the entire fact)
      2. claim length ≤ 150 chars
      3. confidence ≥ 0.6
      4. entity is in KNOWN_ENTITIES
    """
    validated: list[FactObject] = []
    discarded_verbatim = discarded_conf = discarded_entity = discarded_len = 0

    for fact in raw_facts:
        doc = docs_by_id.get(fact.doc_id)
        if doc is None:
            continue

        if fact.evidence_quote not in doc.content:
            discarded_verbatim += 1
            logger.debug(
                "validate_fact: verbatim FAIL  fact=%s  quote=%.60s",
                fact.fact_id, fact.evidence_quote,
            )
            continue

        if len(fact.claim) > 150:
            discarded_len += 1
            continue

        if fact.confidence < _MIN_CONFIDENCE:
            discarded_conf += 1
            continue

        if fact.entity not in KNOWN_ENTITIES:
            discarded_entity += 1
            logger.debug(
                "validate_fact: unknown entity %r  fact=%s", fact.entity, fact.fact_id
            )
            continue

        validated.append(fact)

    logger.info(
        "validate_fact: %d/%d passed  (verbatim=%d len=%d conf=%d entity=%d discarded)",
        len(validated), len(raw_facts),
        discarded_verbatim, discarded_len, discarded_conf, discarded_entity,
    )
    return validated


# ── Gate 2: SAFE atomic verification ─────────────────────────────────────────

_SPLIT_SYSTEM = """\
Decompose the claim into atomic, independently verifiable facts.
Each atomic fact must be a single assertion that cannot be split further.
Return a JSON array of strings ONLY. No explanation, no keys.\
"""

_VERIFY_SYSTEM = """\
Does the evidence quote directly support the atomic claim?
Answer ONLY "yes" or "no". No other words.\
"""


def atomic_split_and_verify(fact: FactObject, llm: LLMClient) -> Optional[FactObject]:
    """
    SAFE verification for a single fact (synchronous — called via to_thread).

    Step 1 — decompose claim into atomic sub-claims (call_json → list[str])
    Step 2 — verify each atomic claim against evidence_quote (call_text → "yes"/"no")
    Step 3 — discard if support ratio < 50%
    """
    # Step 1: decompose
    try:
        atomics = llm.call_json(
            _SPLIT_SYSTEM,
            f'Claim: "{fact.claim}"',
            max_tokens=256,
        )
        if not isinstance(atomics, list) or not atomics:
            # Cannot split reliably → keep the object for auditability, but do
            # not let it count as SAFE-verified.
            fact.atomic_claims = []
            fact.safe_verified = False
            return fact
        atomics = [str(a) for a in atomics if a]
    except Exception as exc:
        logger.warning("SAFE split failed for fact %s: %s — marking unverified", fact.fact_id, exc)
        fact.atomic_claims = []
        fact.safe_verified = False
        return fact

    # Step 2: verify each atomic claim
    supported: list[str] = []
    for atomic in atomics:
        user = (
            f'Atomic claim:   "{atomic}"\n'
            f'Evidence quote: "{fact.evidence_quote}"'
        )
        try:
            answer = llm.call_text(_VERIFY_SYSTEM, user, max_tokens=4).strip().lower()
            if answer.startswith("yes"):
                supported.append(atomic)
        except Exception as exc:
            # Fail closed: verifier errors do not count as support.
            logger.debug("SAFE verify failed for atomic in fact %s: %s", fact.fact_id, exc)

    # Step 3: support ratio check
    ratio = len(supported) / max(len(atomics), 1)
    if ratio < _MIN_SUPPORT_RATIO:
        fact.atomic_claims = supported
        fact.safe_verified = False
        logger.debug(
            "SAFE discarded fact %s (ratio=%.2f, %d/%d atomics supported)",
            fact.fact_id, ratio, len(supported), len(atomics),
        )
        return None

    fact.atomic_claims = supported
    fact.safe_verified = True
    return fact


async def run_safe_verification(facts: list[FactObject]) -> list[FactObject]:
    """
    Async batch SAFE verification — each fact runs in a thread (LLMClient is sync).
    Bounded by _MAX_CONCURRENT_SAFE to limit LLM costs.
    """
    if not facts:
        return []

    llm = LLMClient(agent_name="agent3")
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SAFE)

    async def _verify_one(fact: FactObject) -> Optional[FactObject]:
        async with semaphore:
            return await asyncio.to_thread(atomic_split_and_verify, fact, llm)

    results = await asyncio.gather(*(_verify_one(f) for f in facts))

    verified = [r for r in results if r is not None and r.safe_verified]
    unverified = [r for r in results if r is not None and not r.safe_verified]
    logger.info(
        "SAFE verification: %d/%d facts passed (%.0f%%); %d kept unverified internally",
        len(verified), len(facts),
        100 * len(verified) / max(len(facts), 1),
        len(unverified),
    )
    return verified
