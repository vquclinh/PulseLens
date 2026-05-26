# Node — Quality Gate: strict coverage diagnostics, routes to expand or proceed.
# Pure Python conditional — no LLM cost. Hard stop at MAX_EXPANSION_ROUNDS.
from __future__ import annotations

import logging
from typing import Literal

from app.config.quality_gates import MAX_EXPANSION_ROUNDS, QUALITY_GATE_CONFIG
from app.pipeline.state import PipelineState
from app.schemas.models import SignalType

logger = logging.getLogger(__name__)

def run_quality_gate(state: PipelineState) -> dict:
    """
    Compute quality status and diagnostics.

    Status values:
      PASS         strict thresholds satisfied
      FAIL_EXPAND  coverage is low and expansion rounds remain
      PARTIAL_PASS max rounds exhausted but enough evidence exists to assemble a cautious report
    """
    facts = state.get("scored_facts") or []
    rounds = state.get("query_expansion_rounds", 0)
    companies = state.get("companies") or []
    web_audit = state.get("web_collection_audit") or {}
    fetch_summary = state.get("fetch_error_summary") or {}
    required_signal_values = _required_signal_values(state)

    covered_signals = {f.signal_type for f in facts}
    covered_signal_values = sorted(st.value for st in covered_signals)
    covered_required_values = sorted(st.value for st in covered_signals if st.value in required_signal_values)
    missing_signal_values = sorted(required_signal_values - {st.value for st in covered_signals})
    source_count = len({getattr(f, "source_url", "") for f in facts if getattr(f, "source_url", "")})

    fact_entities = {getattr(f, "entity", "") for f in facts}
    tracked_companies = [company for company in companies if company != "market"]
    company_coverage = (
        len([company for company in tracked_companies if company in fact_entities]) / len(tracked_companies)
        if tracked_companies else 0.0
    )

    query_audits = web_audit.get("queries") if isinstance(web_audit, dict) else []
    query_count = len(query_audits) if isinstance(query_audits, list) else int(web_audit.get("query_count") or 0)
    zero_doc_queries = (
        sum(1 for item in query_audits if int(item.get("accepted_doc_count") or 0) == 0)
        if isinstance(query_audits, list) else int(web_audit.get("zero_doc_query_count") or 0)
    )
    zero_doc_query_rate = zero_doc_queries / max(query_count, 1)

    total_fetch_attempts = int(fetch_summary.get("total_fetch_attempts") or 0)
    failed_fetches = int(fetch_summary.get("failed_fetches") or 0)
    fetch_error_rate = failed_fetches / max(total_fetch_attempts, 1)

    reasons: list[str] = []
    cfg = QUALITY_GATE_CONFIG
    if len(facts) < cfg.min_facts:
        reasons.append(f"fact_count {len(facts)} < {cfg.min_facts}")
    required_signal_count = len(required_signal_values) or cfg.min_signal_types
    if len(covered_required_values) < required_signal_count:
        reasons.append(f"required_signal_types {len(covered_required_values)} < {required_signal_count}")
    if company_coverage < cfg.min_company_coverage_ratio:
        reasons.append(f"company_coverage {company_coverage:.2f} < {cfg.min_company_coverage_ratio:.2f}")
    if zero_doc_query_rate > cfg.max_zero_doc_query_rate:
        reasons.append(f"zero_doc_query_rate {zero_doc_query_rate:.2f} > {cfg.max_zero_doc_query_rate:.2f}")
    if fetch_error_rate > cfg.max_fetch_error_rate:
        reasons.append(f"fetch_error_rate {fetch_error_rate:.2f} > {cfg.max_fetch_error_rate:.2f}")
    if source_count < cfg.min_source_count:
        reasons.append(f"source_count {source_count} < {cfg.min_source_count}")

    logger.info(
        "quality_gate: facts=%d signal_types=%d companies=%.0f%% zero_doc=%.0f%% fetch_errors=%.0f%% sources=%d round=%d",
        len(facts),
        len(covered_signals),
        company_coverage * 100,
        zero_doc_query_rate * 100,
        fetch_error_rate * 100,
        source_count,
        rounds,
    )

    diagnostics = {
        "quality_reasons": reasons,
        "covered_signal_types": covered_signal_values,
        "missing_signal_types": missing_signal_values,
        "company_coverage": round(company_coverage, 4),
        "zero_doc_query_rate": round(zero_doc_query_rate, 4),
        "fetch_error_rate": round(fetch_error_rate, 4),
        "source_count": source_count,
        "fact_count": len(facts),
        "low_signal_types": missing_signal_values,
    }

    if not reasons:
        logger.info("quality_gate: PASS")
        return {
            **diagnostics,
            "quality_status": "PASS",
            "quality_passed": True,
        }

    if rounds + 1 < MAX_EXPANSION_ROUNDS:
        logger.info("quality_gate: FAIL_EXPAND round=%d reasons=%s", rounds, reasons)
        return {
            **diagnostics,
            "quality_status": "FAIL_EXPAND",
            "quality_passed": False,
            "query_expansion_rounds": rounds + 1,
        }

    status = "PARTIAL_PASS"
    logger.info("quality_gate: %s after max rounds reasons=%s", status, reasons)
    return {
        **diagnostics,
        "quality_status": status,
        "quality_passed": True,
    }


def quality_gate_router(state: PipelineState) -> Literal["expand_queries", "proceed"]:
    """Conditional edge router — expand only on explicit FAIL_EXPAND."""
    if state.get("quality_status") == "FAIL_EXPAND" or not state.get("quality_passed", True):
        return "expand_queries"
    return "proceed"


def _required_signal_values(state: PipelineState) -> set[str]:
    configured = state.get("core_signal_types") or state.get("target_signal_types") or []
    values = {str(value) for value in configured if str(value) in {signal.value for signal in SignalType}}
    return values or {signal.value for signal in SignalType}


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
