# Agent 4 — FinBERT Scorer (ProsusAI/finbert)
# Batch financial sentiment scoring — no LLM API cost, deterministic, fast on CPU.
# Yang et al., 2020 — HuggingFace ProsusAI/finbert (arXiv: FinBERT)
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from app.schemas.models import FactObject

logger = logging.getLogger(__name__)

_BATCH_SIZE = int(os.getenv("FINBERT_BATCH_SIZE", "32"))
_DEVICE     = os.getenv("FINBERT_DEVICE", "cpu")
_MODEL_ID   = "ProsusAI/finbert"

_finbert: Optional[object] = None


def _get_finbert():
    global _finbert
    if _finbert is None:
        from transformers import pipeline as hf_pipeline
        logger.info("Loading FinBERT model %s on device=%s", _MODEL_ID, _DEVICE)
        _finbert = hf_pipeline(
            "sentiment-analysis",
            model=_MODEL_ID,
            tokenizer=_MODEL_ID,
            device=_DEVICE,
            truncation=True,
            max_length=512,
        )
        logger.info("FinBERT loaded")
    return _finbert


def score_facts(facts: list[FactObject]) -> tuple[list[FactObject], list[str]]:
    """
    Score each fact.claim with FinBERT. Mutates sentiment + sentiment_score in place.
    Returns (scored_facts, error_messages). Failed facts are marked safe_verified=False
    so M4 filters them out rather than treating them as unscored-but-valid.
    Synchronous — wrap in asyncio.to_thread for async contexts.
    """
    if not facts:
        return facts, []

    errors: list[str] = []
    model = _get_finbert()
    claims = [f.claim for f in facts]

    try:
        results = model(claims, batch_size=_BATCH_SIZE, truncation=True)
    except Exception as exc:
        for fact in facts:
            logger.warning(
                "FinBERT inference failed for fact %s: %s — marking unreliable",
                fact.fact_id, exc,
            )
            fact.sentiment = "neutral"
            fact.sentiment_score = 0.0
            fact.safe_verified = False
            errors.append(f"FinBERT inference failed for fact {fact.fact_id}: {exc}")
        return facts, errors

    for fact, result in zip(facts, results):
        try:
            label: str = result["label"].lower()   # "positive" | "negative" | "neutral"
            score: float = float(result["score"])   # 0.0–1.0 confidence from FinBERT
            fact.sentiment = label  # type: ignore[assignment]
            fact.sentiment_score = (
                 score if label == "positive" else
                -score if label == "negative" else
                 0.0
            )
        except Exception as exc:
            logger.warning(
                "FinBERT result parse failed for fact %s: %s — marking unreliable",
                fact.fact_id, exc,
            )
            fact.sentiment = "neutral"
            fact.sentiment_score = 0.0
            fact.safe_verified = False
            errors.append(f"FinBERT result parse failed for fact {fact.fact_id}: {exc}")

    logger.info(
        "FinBERT scored %d facts — pos=%d neg=%d neu=%d errors=%d",
        len(facts),
        sum(1 for f in facts if f.sentiment == "positive"),
        sum(1 for f in facts if f.sentiment == "negative"),
        sum(1 for f in facts if f.sentiment == "neutral"),
        len(errors),
    )
    return facts, errors


async def run_finbert_scorer(facts: list[FactObject]) -> tuple[list[FactObject], list[str]]:
    """Async entry point — runs FinBERT in thread pool (model inference is sync).
    Returns (scored_facts, error_messages) — errors must be written to state by caller."""
    if not facts:
        return facts, []
    return await asyncio.to_thread(score_facts, facts)


# ── Standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from app.schemas.models import SignalType
    from app.utils.helpers import generate_uuid

    _test_cases = [
        # Positive
        ("Nvidia",    SignalType.investor_signal,
         "Nvidia raised revenue guidance for Q2 2025 to record highs above analyst consensus."),
        ("AMD",       SignalType.product_launch,
         "AMD announced a major AI accelerator breakthrough far exceeding all benchmark targets."),
        ("Intel",     SignalType.investor_signal,
         "Intel reported strong earnings beating analyst expectations by a wide margin."),
        # Negative
        ("AMD",       SignalType.investor_signal,
         "AMD missed quarterly earnings and slashed its revenue guidance significantly."),
        ("Intel",     SignalType.hiring_momentum,
         "Intel announced mass layoffs eliminating fifteen percent of its global workforce."),
        ("Nvidia",    SignalType.supplier_risk,
         "Nvidia faces severe supply chain disruptions and critical inventory shortages."),
        # Neutral — purely factual/administrative statements FinBERT scores near 0
        ("market",    SignalType.news_sentiment,
         "The US semiconductor market report was filed with the SEC on schedule."),
        ("Broadcom",  SignalType.news_sentiment,
         "Broadcom's earnings call is scheduled for the third Tuesday of next month."),
        ("Dell",      SignalType.strategic_messaging,
         "Dell submitted its annual Form 10-K to the SEC on the required filing date."),
        ("Micron",    SignalType.strategic_messaging,
         "Micron listed its upcoming investor day on the corporate events calendar."),
    ]

    def _make_fact(entity: str, signal_type: SignalType, claim: str) -> FactObject:
        return FactObject(
            fact_id=f"fact_{generate_uuid()[:12]}",
            doc_id="doc_test",
            entity=entity,
            signal_type=signal_type,
            claim=claim,
            evidence_quote=claim[:200],
            source_url="https://example.com/test",
            source_tier=2,
            published_date="2025-05-01",
            sentiment="neutral",
            sentiment_score=0.0,
            confidence=0.85,
            safe_verified=True,
        )

    facts = [_make_fact(e, st, c) for e, st, c in _test_cases]
    scored, errs = score_facts(facts)
    if errs:
        print("Errors:", errs)

    print(f"\n{'Entity':<12} {'Sentiment':<10} {'Score':>7}  Claim")
    print("-" * 90)
    for f in scored:
        print(f"{f.entity:<12} {f.sentiment:<10} {f.sentiment_score:>+7.3f}  {f.claim[:60]}")

    sentiments_seen = {f.sentiment for f in scored}
    print(f"\nSentiment values seen: {sorted(sentiments_seen)}")
    assert "positive" in sentiments_seen, "FAIL: no positive sentiment in test output"
    assert "negative" in sentiments_seen, "FAIL: no negative sentiment in test output"
    assert "neutral"  in sentiments_seen, "FAIL: no neutral sentiment in test output"
    print("PASS: all 3 sentiment values present")
