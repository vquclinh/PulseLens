# Node — M5 Signal Scorer
# Pure Python deterministic weighted formula: tier × confidence × factscore × sentiment.
# No LLM — deterministic, testable, fast.
from __future__ import annotations

import logging
from statistics import mean
from typing import Any

from app.config.signal_types import SIGNAL_WEIGHTS
from app.schemas.models import PulseStatus, SignalType, VerifiedClaim

logger = logging.getLogger(__name__)

_TIER_RANK: dict[int, int] = {1: 4, 2: 3, 3: 2, 4: 1}


def calculate_signal_score(claims: list[VerifiedClaim], signal_type: str) -> float:
    relevant = [c for c in claims if c.signal_type.value == signal_type]
    if not relevant:
        return 0.0

    total_w = 0.0
    weighted_sum = 0.0
    for c in relevant:
        base_w = (
            c.final_confidence
            * c.factscore
            * max(_TIER_RANK.get(t, 1) for t in c.source_tiers_present)
        )
        w = base_w * (0.5 if c.is_contradicted else 1.0)
        weighted_sum += c.weighted_sentiment * w
        total_w += w

    return weighted_sum / total_w if total_w > 0 else 0.0


def calculate_pulse_score(claims: list[VerifiedClaim]) -> tuple[float, float]:
    signal_scores = {st: calculate_signal_score(claims, st) for st in SIGNAL_WEIGHTS}
    raw = sum(signal_scores[st] * w for st, w in SIGNAL_WEIGHTS.items())
    pulse = (raw + 1) / 2 * 100   # normalize [-1, 1] → [0, 100]
    if claims:
        confidence = mean(c.final_confidence * c.factscore for c in claims)
    else:
        confidence = 0.0
    return round(pulse, 1), round(confidence, 3)


def classify_pulse_status(
    score: float,
    has_supplier_risk: bool,
    contradiction_rate: float,
) -> PulseStatus:
    if contradiction_rate > 0.4:
        return PulseStatus.volatile
    if has_supplier_risk and score < 55:
        return PulseStatus.risk_rising
    if score >= 70:
        return PulseStatus.heating_up
    if score >= 45:
        return PulseStatus.stable
    return PulseStatus.cooling_down


def run_signal_scorer(verified_claims: list[VerifiedClaim]) -> dict[str, Any]:
    """
    Compute market-level and per-company pulse scores from VerifiedClaims.
    Returns the `signal_scores` dict stored in PipelineState.
    """
    if not verified_claims:
        return {
            "pulse_score":      50.0,
            "pulse_status":     PulseStatus.stable,
            "pulse_confidence": 0.0,
            "breakdown": {"by_signal": {}, "by_company": {}},
        }

    pulse_score, pulse_confidence = calculate_pulse_score(verified_claims)

    # Market-level signal breakdown
    by_signal: dict[str, float] = {
        st: round(calculate_signal_score(verified_claims, st), 4)
        for st in SIGNAL_WEIGHTS
    }

    # Per-company breakdown
    companies = sorted({c.entity for c in verified_claims})
    by_company: dict[str, dict[str, Any]] = {}
    for company in companies:
        company_claims = [c for c in verified_claims if c.entity == company]
        c_pulse, c_conf = calculate_pulse_score(company_claims)
        c_signals = {
            st: round(calculate_signal_score(company_claims, st), 4)
            for st in SIGNAL_WEIGHTS
        }
        c_contradicted = sum(1 for c in company_claims if c.is_contradicted)
        c_rate = c_contradicted / len(company_claims) if company_claims else 0.0
        c_supplier_risk = any(
            c.signal_type == SignalType.supplier_risk for c in company_claims
        )
        by_company[company] = {
            "pulse_score":      c_pulse,
            "pulse_confidence": c_conf,
            "pulse_status":     classify_pulse_status(c_pulse, c_supplier_risk, c_rate).value,
            "signal_scores":    c_signals,
            "claim_count":      len(company_claims),
            "contradiction_rate": round(c_rate, 3),
        }

    total = len(verified_claims)
    contradicted = sum(1 for c in verified_claims if c.is_contradicted)
    contradiction_rate = contradicted / total if total > 0 else 0.0
    has_supplier_risk = any(
        c.signal_type == SignalType.supplier_risk for c in verified_claims
    )
    pulse_status = classify_pulse_status(pulse_score, has_supplier_risk, contradiction_rate)

    logger.info(
        "M5 Signal Scorer: pulse_score=%.1f status=%s confidence=%.3f claims=%d contradicted=%d",
        pulse_score, pulse_status.value, pulse_confidence, total, contradicted,
    )

    return {
        "pulse_score":      pulse_score,
        "pulse_status":     pulse_status,
        "pulse_confidence": pulse_confidence,
        "breakdown": {
            "by_signal":  by_signal,
            "by_company": by_company,
        },
    }


# ── Standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from app.schemas.models import SignalType, VerifiedClaim, PulseStatus

    def _vc(
        cid: str, entity: str, sig: SignalType, sentiment: float,
        confidence: float, factscore: float, tiers: list[int],
        contradicted: bool = False,
    ) -> VerifiedClaim:
        return VerifiedClaim(
            claim_id=cid, entity=entity, signal_type=sig, summary="test",
            supporting_facts=[], corroboration_count=len(tiers),
            source_tiers_present=tiers, weighted_sentiment=sentiment,
            recency_score=0.8, final_confidence=confidence, factscore=factscore,
            is_contradicted=contradicted, contradiction_note=None,
        )

    mock_claims = [
        # Nvidia — strong positive across signals
        _vc("vc1", "Nvidia", SignalType.hiring_momentum,   +0.85, 0.92, 0.90, [1, 2]),
        _vc("vc2", "Nvidia", SignalType.investor_signal,   +0.78, 0.95, 0.88, [1]),
        _vc("vc3", "Nvidia", SignalType.product_launch,    +0.70, 0.88, 0.82, [2]),
        _vc("vc4", "Nvidia", SignalType.news_sentiment,    +0.65, 0.85, 0.80, [2, 3]),
        # AMD — mixed, contradicted pricing pressure
        _vc("vc5", "AMD",    SignalType.pricing_pressure,  -0.40, 0.87, 0.78, [1, 2], contradicted=True),
        _vc("vc6", "AMD",    SignalType.hiring_momentum,   +0.50, 0.80, 0.75, [2, 3]),
        _vc("vc7", "AMD",    SignalType.investor_signal,   +0.30, 0.82, 0.77, [1]),
        # Intel — supplier risk
        _vc("vc8", "Intel",  SignalType.supplier_risk,     -0.60, 0.78, 0.72, [2, 3]),
        _vc("vc9", "Intel",  SignalType.news_sentiment,    -0.50, 0.75, 0.70, [3]),
    ]

    print("\n── M5 Signal Scorer test ────────────────────────────────────")
    result = run_signal_scorer(mock_claims)

    print(f"\n  pulse_score      : {result['pulse_score']}")
    print(f"  pulse_status     : {result['pulse_status'].value}")
    print(f"  pulse_confidence : {result['pulse_confidence']}")

    print("\n  Signal breakdown:")
    for sig, score in result["breakdown"]["by_signal"].items():
        print(f"    {sig:<22}: {score:+.4f}")

    print("\n  Company breakdown:")
    for company, data in result["breakdown"]["by_company"].items():
        print(f"    {company}: pulse={data['pulse_score']} status={data['pulse_status']} "
              f"conf={data['pulse_confidence']} contradiction_rate={data['contradiction_rate']}")

    # Assertions
    assert 0.0 <= result["pulse_score"] <= 100.0, "pulse_score out of range"
    assert isinstance(result["pulse_status"], PulseStatus), "pulse_status wrong type"
    assert 0.0 <= result["pulse_confidence"] <= 1.0, "pulse_confidence out of range"
    assert "Nvidia" in result["breakdown"]["by_company"], "Nvidia missing from breakdown"
    assert "AMD" in result["breakdown"]["by_company"], "AMD missing from breakdown"
    assert "Intel" in result["breakdown"]["by_company"], "Intel missing from breakdown"

    # Nvidia should score higher than Intel (positive vs negative signals)
    nvidia_score = result["breakdown"]["by_company"]["Nvidia"]["pulse_score"]
    intel_score  = result["breakdown"]["by_company"]["Intel"]["pulse_score"]
    assert nvidia_score > intel_score, f"Expected Nvidia ({nvidia_score}) > Intel ({intel_score})"

    # Intel has supplier_risk + low score → should be risk_rising
    intel_status = result["breakdown"]["by_company"]["Intel"]["pulse_status"]
    assert intel_status == PulseStatus.risk_rising.value, f"Expected risk_rising, got {intel_status}"

    # Empty input → stable 50.0
    empty_result = run_signal_scorer([])
    assert empty_result["pulse_score"] == 50.0
    assert empty_result["pulse_status"] == PulseStatus.stable

    print("\n✅ All assertions passed")
