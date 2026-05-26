# Node — validate_fact + SAFE atomic verification (arXiv:2403.18802)
#
# Two sequential gates between Agent 3 output and FinBERT scoring:
#   1. validate_facts()       — pure Python verbatim check (fastest, no LLM cost)
#   2. run_safe_verification() — LLM atomic decomposition + support check
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from app.config.companies import KNOWN_ENTITIES
from app.config.quality_gates import FACT_MIN_CONFIDENCE, SAFE_MAX_CONCURRENT, SAFE_MIN_SUPPORT_RATIO
from app.schemas.models import FactObject, RawDocument
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

_MIN_CONFIDENCE = FACT_MIN_CONFIDENCE
_MIN_SUPPORT_RATIO = SAFE_MIN_SUPPORT_RATIO   # SAFE threshold: discard if < 50% atomic claims supported
_MAX_CONCURRENT_SAFE = SAFE_MAX_CONCURRENT    # SAFE is expensive (2+ LLM calls per fact)

# ── Gate 1 supplemental: deterministic claim-quality patterns ─────────────────

_METADATA_NAV_PATTERNS = [
    re.compile(r"provides?\s+investor\s+relations\s+information", re.I),
    re.compile(r"includes?\s+(?:financial\s+results|sec\s+filings|earnings\s+webcasts)", re.I),
    re.compile(r"(?:website|page|portal)\s+provides?", re.I),
    re.compile(r"contains?\s+links?\s+to", re.I),
    re.compile(r"offers?\s+information\s+about", re.I),
    re.compile(r"investor\s+relations\s+(?:page|portal|section|information)", re.I),
    re.compile(r"(?:financial\s+results|press\s+releases|sec\s+filings)\s+(?:are|can\s+be)\s+(?:found|accessed|viewed)", re.I),
]

_PRICING_STRONG_PATTERNS = [
    re.compile(r"\$[\d,]+\.?\d*"),                                                                   # explicit $ amount
    re.compile(r"\d+\.?\d*\s*%\s*(?:increase|decrease|drop|rise|change|higher|lower)", re.I),       # % price change
    re.compile(r"(?:discount|discounted|on.demand|spot\s+price|rental\s+rate|hourly\s+rate)", re.I),
    re.compile(r"(?:cost|price)\s+per\s+(?:hour|month|year)", re.I),
    re.compile(r"starting\s+price\s+of\s+\$", re.I),
    re.compile(r"(?:lead\s+time).{0,60}(?:availability|weeks?|months?|days?)", re.I),
]

_PRICING_REJECT_PATTERNS = [
    re.compile(r"(?:launched?|announced?|introduced?)\s+.{0,40}(?:index|tracker|benchmark|price\s+index)", re.I),
    re.compile(r"(?:index|tracker|benchmark).{0,40}(?:launched?|announced?|introduced?)", re.I),
    re.compile(r"hbm.{0,60}(?:price|cost|shortage)", re.I),
    re.compile(r"memory.{0,60}(?:shortage|supply).{0,60}(?:price|cost)", re.I),
    re.compile(r"available\s+with\s+a\s+starting\s+price(?!\s+of\s+\$)", re.I),
]

# ── Gate 1: pure Python verbatim check ────────────────────────────────────────


def validate_facts(
    raw_facts: list[FactObject],
    docs_by_id: dict[str, RawDocument],
) -> tuple[list[FactObject], dict]:
    """
    CRITICAL anti-hallucination gate (ARCHITECTURE.md §5).

    Checks in order (cheapest first):
      1. evidence_quote is a VERBATIM substring of source.content
         (LLM invented the quote → discard the entire fact)
      2. claim length ≤ 150 chars
      3. confidence ≥ configured minimum (default 0.60)
      4. entity is in KNOWN_ENTITIES
      5. claim does not match navigation/metadata page description patterns
      6. pricing_pressure: claim+quote must contain explicit price signal
         (index launches, HBM shortage, "available at a price" → rejected)

    Returns (validated_facts, audit_dict).
    """
    validated: list[FactObject] = []
    discarded_verbatim = discarded_conf = discarded_entity = discarded_len = 0
    discarded_nav_metadata = 0
    discarded_pricing_weak = 0
    pricing_sanity_checked = 0
    rejected_nav_fact_ids: list[str] = []

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

        if any(pat.search(fact.claim) for pat in _METADATA_NAV_PATTERNS):
            discarded_nav_metadata += 1
            rejected_nav_fact_ids.append(fact.fact_id)
            logger.debug(
                "validate_fact: nav_metadata FAIL fact=%s claim=%.80s",
                fact.fact_id, fact.claim,
            )
            continue

        if fact.signal_type.value == "pricing_pressure":
            text = fact.claim + " " + fact.evidence_quote
            if any(pat.search(text) for pat in _PRICING_REJECT_PATTERNS):
                if not any(pat.search(text) for pat in _PRICING_STRONG_PATTERNS):
                    discarded_pricing_weak += 1
                    logger.info(
                        "validate_fact: pricing_sanity REJECT fact=%s claim=%.80s",
                        fact.fact_id, fact.claim,
                    )
                    continue
            pricing_sanity_checked += 1

        validated.append(fact)

    audit: dict = {
        "discarded_verbatim": discarded_verbatim,
        "discarded_length": discarded_len,
        "discarded_confidence": discarded_conf,
        "discarded_entity": discarded_entity,
        "discarded_nav_metadata": discarded_nav_metadata,
        "pricing_sanity_checked_count": pricing_sanity_checked,
        "pricing_sanity_rejected_count": discarded_pricing_weak,
        "pricing_sanity_relabel_count": 0,
        "pricing_sanity_weak_count": discarded_pricing_weak,
        "metadata_navigation_fact_rejected_count": discarded_nav_metadata,
        "rejected_metadata_navigation_facts": rejected_nav_fact_ids,
    }
    logger.info(
        "validate_fact: %d/%d passed  "
        "(verbatim=%d len=%d conf=%d entity=%d nav_meta=%d pricing_weak=%d discarded)",
        len(validated), len(raw_facts),
        discarded_verbatim, discarded_len, discarded_conf, discarded_entity,
        discarded_nav_metadata, discarded_pricing_weak,
    )
    return validated, audit


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
