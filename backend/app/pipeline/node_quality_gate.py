# Node — Quality Gate: fact count + signal coverage check, routes to expand or proceed
# Pure Python conditional — no LLM cost. Hard stop at MAX_EXPANSION_ROUNDS.
from __future__ import annotations

import logging
from typing import Literal

from app.config.quality_gates import MAX_EXPANSION_ROUNDS
from app.pipeline.state import PipelineState
from app.schemas.models import SignalType

logger = logging.getLogger(__name__)

_MIN_FACTS        = 50
_MIN_SIGNAL_TYPES = 4


def run_quality_gate(state: PipelineState) -> dict:
    """
    Node function — computes gate decision, writes quality_passed + low_signal_types.
    The conditional edge router reads quality_passed from state after this node runs.
    """
    facts           = state.get("scored_facts") or []
    rounds          = state.get("query_expansion_rounds", 0)
    covered_signals = {f.signal_type for f in facts}

    logger.info(
        "quality_gate: facts=%d signal_types=%d round=%d",
        len(facts), len(covered_signals), rounds,
    )

    # Hard stop — prevent infinite loop
    if rounds >= MAX_EXPANSION_ROUNDS:
        logger.info("quality_gate: hard stop at round=%d → proceed", rounds)
        return {"quality_passed": True}

    # Signal coverage or volume insufficient
    if len(facts) < _MIN_FACTS or len(covered_signals) < _MIN_SIGNAL_TYPES:
        missing = sorted(st.value for st in SignalType if st not in covered_signals)
        logger.info(
            "quality_gate: FAIL (facts=%d<%d OR signal_types=%d<%d) → expand, missing=%s",
            len(facts), _MIN_FACTS, len(covered_signals), _MIN_SIGNAL_TYPES, missing,
        )
        return {
            "quality_passed": False,
            "low_signal_types": missing,
            "query_expansion_rounds": rounds + 1,
        }

    logger.info("quality_gate: PASS → proceed")
    return {"quality_passed": True}


def quality_gate_router(state: PipelineState) -> Literal["expand_queries", "proceed"]:
    """Conditional edge router — reads quality_passed written by run_quality_gate node."""
    if not state.get("quality_passed", True):
        return "expand_queries"
    return "proceed"


# ── Standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from app.schemas.models import FactObject, SignalType
    from app.utils.helpers import generate_uuid
    from datetime import datetime, timezone

    def _make_fact(signal_type: SignalType, sentiment: str = "neutral") -> FactObject:
        return FactObject(
            fact_id=f"fact_{generate_uuid()[:8]}",
            doc_id="doc_test",
            entity="Nvidia",
            signal_type=signal_type,
            claim="Nvidia reported strong results in Q1 2025.",
            evidence_quote="Nvidia reported strong results in Q1 2025.",
            source_url="https://example.com",
            source_tier=2,
            published_date="2025-05-01",
            sentiment=sentiment,
            sentiment_score=0.0,
            confidence=0.85,
            safe_verified=True,
        )

    signal_types = list(SignalType)

    # Test 1: 10 facts, 2 signal types → expand_queries
    facts_10_2sig = [_make_fact(signal_types[i % 2]) for i in range(10)]
    state1: dict = {"scored_facts": facts_10_2sig, "query_expansion_rounds": 0}
    result1 = run_quality_gate(state1)
    state1.update(result1)
    route1 = quality_gate_router(state1)
    status1 = "PASS" if route1 == "expand_queries" else "FAIL"
    print(f"[{status1}] 10 facts, 2 signal types → {route1!r}  (expected 'expand_queries')")

    # Test 2: 60 facts, 5 signal types → proceed
    facts_60_5sig = [_make_fact(signal_types[i % 5]) for i in range(60)]
    state2: dict = {"scored_facts": facts_60_5sig, "query_expansion_rounds": 0}
    result2 = run_quality_gate(state2)
    state2.update(result2)
    route2 = quality_gate_router(state2)
    status2 = "PASS" if route2 == "proceed" else "FAIL"
    print(f"[{status2}] 60 facts, 5 signal types → {route2!r}  (expected 'proceed')")

    # Test 3: 10 facts, round=2 → proceed (hard stop)
    facts_10_round2 = [_make_fact(signal_types[i % 2]) for i in range(10)]
    state3: dict = {"scored_facts": facts_10_round2, "query_expansion_rounds": 2}
    result3 = run_quality_gate(state3)
    state3.update(result3)
    route3 = quality_gate_router(state3)
    status3 = "PASS" if route3 == "proceed" else "FAIL"
    print(f"[{status3}] 10 facts, round=2 → {route3!r}  (expected 'proceed' — hard stop)")
