# Node — M4 Triangulator (ClaimCheck + MiniCheck + FActScore patterns)
# ClaimCheck: corroboration >= 2 distinct domains OR tier-1 override (ACL 2025)
# MiniCheck: confidence + safe_verified pre-filter proxy (arXiv:2404.10774)
# FActScore: confidence-weighted atomic precision proxy (arXiv:2305.14251)
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from app.schemas.models import ContradictionFlag, FactObject, SignalType, VerifiedClaim
from app.utils.helpers import generate_uuid

logger = logging.getLogger(__name__)

_TIER_W: dict[int, float] = {1: 1.0, 2: 0.8, 3: 0.5, 4: 0.4}
_RECENCY_WINDOW_DAYS = 7
_MINICHECK_MIN_CONF  = 0.6   # proxy for per-fact MiniCheck validation


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host.lstrip("www.")
    except Exception:
        return url


def _days_since(date_str: Optional[str]) -> float:
    if not date_str:
        return float(_RECENCY_WINDOW_DAYS)
    try:
        pub = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - pub
        return max(0.0, delta.total_seconds() / 86400)
    except (ValueError, TypeError):
        return float(_RECENCY_WINDOW_DAYS)


def _recency_weight(date_str: Optional[str]) -> float:
    age = _days_since(date_str)
    # Day 0 = 1.0  ·  Day 3 = 0.25  ·  Day 6 = 0.14  ·  Day 7+ = 0.0
    return 0.0 if age > _RECENCY_WINDOW_DAYS else 1.0 / (age + 1)


# ── MiniCheck proxy ────────────────────────────────────────────────────────────

def _minicheck_validate(fact: FactObject) -> bool:
    """
    Lightweight MiniCheck proxy (arXiv:2404.10774).
    Full model not available; approximates per-fact validation using
    confidence threshold and SAFE verification status.
    Facts that passed Gate 1 + SAFE upstream already satisfy this — safety net.
    """
    return fact.confidence >= _MINICHECK_MIN_CONF and fact.safe_verified


# ── Sentiment + recency weighting ─────────────────────────────────────────────

def _calculate_weighted_sentiment(group: list[FactObject]) -> float:
    total = sum(
        _TIER_W.get(f.source_tier, 0.4) * _recency_weight(f.published_date)
        for f in group
    )
    if total == 0.0:
        return 0.0
    wmean = sum(
        f.sentiment_score
        * _TIER_W.get(f.source_tier, 0.4)
        * _recency_weight(f.published_date)
        for f in group
    )
    return wmean / total


def _calculate_recency_score(group: list[FactObject]) -> float:
    weights = [_recency_weight(f.published_date) for f in group]
    return sum(weights) / max(len(weights), 1)


def _calculate_factscore(group: list[FactObject]) -> float:
    """
    FActScore proxy (arXiv:2305.14251).
    Uses mean confidence across the group — best approximation without
    storing original atomic count at SAFE time.
    """
    return sum(f.confidence for f in group) / max(len(group), 1)


def _calculate_final_confidence(
    corroboration_count: int,
    source_tiers: set[int],
    recency_score: float,
    factscore: float,
) -> float:
    tier_bonus = 0.2 if 1 in source_tiers else 0.1 if 2 in source_tiers else 0.0
    corr_score = min(1.0, corroboration_count / 4)
    raw = factscore * 0.4 + corr_score * 0.4 + recency_score * 0.2 + tier_bonus
    return round(min(1.0, raw), 3)


def _generate_summary(group: list[FactObject]) -> str:
    top = max(group, key=lambda f: f.confidence)
    return top.claim[:150]


# ── Core triangulation ─────────────────────────────────────────────────────────

def triangulate(
    facts: list[FactObject],
) -> tuple[list[VerifiedClaim], list[ContradictionFlag]]:
    """
    M4 Triangulator — ClaimCheck + MiniCheck + FActScore.

    Step 1 — MiniCheck proxy: discard low-confidence / unverified facts
    Step 2 — Group by (entity, signal_type)
    Step 3 — ClaimCheck corroboration: require ≥2 distinct domains OR ≥1 Tier-1 source
    Step 4 — Contradiction detection: positive AND negative sentiment in same group
    Step 5 — FActScore + weighted sentiment + recency + confidence → VerifiedClaim
    """
    validated = [f for f in facts if _minicheck_validate(f)]
    logger.info(
        "M4 triangulator: MiniCheck pass=%d fail=%d",
        len(validated), len(facts) - len(validated),
    )

    groups: dict[tuple, list[FactObject]] = defaultdict(list)
    for fact in validated:
        groups[(fact.entity, fact.signal_type)].append(fact)

    verified_claims: list[VerifiedClaim] = []
    contradiction_flags: list[ContradictionFlag] = []

    for (entity, signal_type), group in groups.items():
        unique_domains = {_extract_domain(f.source_url) for f in group}
        has_tier1      = any(f.source_tier == 1 for f in group)

        # ClaimCheck corroboration (ACL 2025): ≥2 domains OR ≥1 Tier-1 source
        if len(unique_domains) < 2 and not has_tier1:
            logger.debug(
                "M4: dropped (%s, %s) — single domain, no tier-1 (domains=%s)",
                entity, signal_type.value, unique_domains,
            )
            continue

        sentiments      = {f.sentiment for f in group}
        is_contradicted = "positive" in sentiments and "negative" in sentiments

        factscore      = _calculate_factscore(group)
        weighted_sent  = _calculate_weighted_sentiment(group)
        recency        = _calculate_recency_score(group)
        source_tiers   = {f.source_tier for f in group}
        confidence     = _calculate_final_confidence(
            corroboration_count=len(unique_domains),
            source_tiers=source_tiers,
            recency_score=recency,
            factscore=factscore,
        )

        verified_claims.append(VerifiedClaim(
            claim_id             = f"claim_{generate_uuid()[:12]}",
            entity               = entity,
            signal_type          = signal_type,
            summary              = _generate_summary(group),
            supporting_facts     = [f.fact_id for f in group],
            corroboration_count  = len(unique_domains),
            source_tiers_present = sorted(source_tiers),
            weighted_sentiment   = round(weighted_sent, 4),
            recency_score        = round(recency, 4),
            final_confidence     = confidence,
            factscore            = round(factscore, 4),
            is_contradicted      = is_contradicted,
            contradiction_note   = None,
        ))

        if is_contradicted:
            pos_ids = [f.fact_id for f in group if f.sentiment == "positive"]
            neg_ids = [f.fact_id for f in group if f.sentiment == "negative"]
            contradiction_flags.append(ContradictionFlag(
                entity         = entity,
                signal_type    = signal_type,
                positive_facts = pos_ids,
                negative_facts = neg_ids,
                note           = "",
            ))
            logger.info(
                "M4: contradiction detected (%s, %s) pos=%d neg=%d",
                entity, signal_type.value, len(pos_ids), len(neg_ids),
            )

    logger.info(
        "M4 triangulator: %d verified claims, %d contradictions from %d groups",
        len(verified_claims), len(contradiction_flags), len(groups),
    )
    return verified_claims, contradiction_flags


# ── Standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from app.schemas.models import FactObject, SignalType
    from app.utils.helpers import generate_uuid

    def _fact(
        fact_id: str,
        entity: str,
        signal_type: SignalType,
        sentiment: str,
        sentiment_score: float,
        source_url: str,
        source_tier: int,
        confidence: float = 0.85,
        published_date: str = "2025-05-20",
    ) -> FactObject:
        claim = f"{entity} {signal_type.value} signal detected."
        return FactObject(
            fact_id         = fact_id,
            doc_id          = "doc_test",
            entity          = entity,
            signal_type     = signal_type,
            claim           = claim,
            evidence_quote  = claim,
            source_url      = source_url,
            source_tier     = source_tier,
            published_date  = published_date,
            sentiment       = sentiment,
            sentiment_score = sentiment_score,
            confidence      = confidence,
            safe_verified   = True,
            atomic_claims   = ["atomic1", "atomic2"],
        )

    # ── Test 1: 2 facts, same (entity, signal_type), different domains → 1 VerifiedClaim
    print("\n── Test 1: corroboration ─────────────────────────────────────────────")
    f1a = _fact("f1a", "Nvidia", SignalType.investor_signal, "positive", 0.85,
                "https://reuters.com/article/1", source_tier=2)
    f1b = _fact("f1b", "Nvidia", SignalType.investor_signal, "positive", 0.80,
                "https://bloomberg.com/article/1", source_tier=2)
    claims1, contras1 = triangulate([f1a, f1b])
    status1 = "PASS" if len(claims1) == 1 and len(contras1) == 0 else "FAIL"
    print(f"[{status1}] 2 facts, diff domains → {len(claims1)} VerifiedClaim(s), {len(contras1)} contradictions")
    for c in claims1:
        print(f"  claim_id={c.claim_id}  corroboration={c.corroboration_count}  factscore={c.factscore:.3f}  conf={c.final_confidence:.3f}")

    # ── Test 2: 1 fact, no Tier-1, single domain → dropped (0 VerifiedClaims)
    print("\n── Test 2: single domain, no tier-1 → dropped ──────────────────────")
    f2 = _fact("f2a", "AMD", SignalType.product_launch, "positive", 0.75,
               "https://techcrunch.com/article/1", source_tier=3)
    claims2, contras2 = triangulate([f2])
    status2 = "PASS" if len(claims2) == 0 else "FAIL"
    print(f"[{status2}] 1 fact, no tier-1 → {len(claims2)} VerifiedClaim(s)  (expected 0)")

    # ── Test 3: 1 positive + 1 negative, same (entity, signal_type) → contradiction
    print("\n── Test 3: contradiction detection ──────────────────────────────────")
    f3a = _fact("f3a", "Intel", SignalType.investor_signal, "positive",  0.85,
                "https://reuters.com/article/2", source_tier=2)
    f3b = _fact("f3b", "Intel", SignalType.investor_signal, "negative", -0.80,
                "https://bloomberg.com/article/2", source_tier=2)
    claims3, contras3 = triangulate([f3a, f3b])
    status3 = "PASS" if len(claims3) == 1 and len(contras3) == 1 and claims3[0].is_contradicted else "FAIL"
    print(f"[{status3}] 1 pos + 1 neg → {len(claims3)} VerifiedClaim(s), {len(contras3)} contradiction(s)")
    for c in claims3:
        print(f"  is_contradicted={c.is_contradicted}  weighted_sentiment={c.weighted_sentiment:.4f}  corroboration={c.corroboration_count}")
    for cf in contras3:
        print(f"  contradiction: {cf.entity} {cf.signal_type.value}  pos={cf.positive_facts} neg={cf.negative_facts}")

    print("\nAll M4 tests complete.")
