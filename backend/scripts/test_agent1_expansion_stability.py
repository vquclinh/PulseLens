"""Agent 1 expansion stability test — zero API cost.

Tests that the Sprint 5 fixes to _trim_queries_to_limit and _enforce_final_quality
prevent the Agent 1 ValueError crash that occurred during expansion rounds when
pricing playbook queries crowd out required signal types.

Does NOT call OpenRouter or BrightData. Uses mock SearchQuery objects only.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.pipeline.agent1_query_planner import (
    QueryPlanner,
    _trim_queries_to_limit,
)
from app.schemas.models import SearchQuery, SignalType
from app.utils.helpers import generate_uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("agent1_expansion_test")

DEMO_COMPANIES = ["Nvidia", "AMD", "Supermicro"]
REQUIRED_SIGNAL_TYPES = {
    SignalType.investor_signal.value,
    SignalType.product_launch.value,
    SignalType.pricing_pressure.value,
    SignalType.supplier_risk.value,
}
MAX_EXPANSION_QUERIES = 10


def _make_query(
    signal_type: str,
    entity: str = "Nvidia",
    source_type: str = "serp_news",
    is_playbook: bool = False,
) -> SearchQuery:
    prefix = "q_price_" if is_playbook else "q_"
    return SearchQuery(
        query_id=f"{prefix}{generate_uuid()[:8]}",
        query_text=f"{entity} {signal_type} test query 2026",
        target_entity=entity,
        signal_type=SignalType(signal_type),
        source_type=source_type,
        priority=2,
        expected_source_tier=2,
    )


def run_tests() -> dict:
    results = {}
    all_passed = True

    # ── Test 1 ──────────────────────────────────────────────────────────────────
    # 12 pricing playbook queries (q_price_*) + 0 non-pricing LLM queries.
    # _trim_queries_to_limit must handle gracefully: at most MAX_EXPANSION_QUERIES returned,
    # all pricing_pressure (since no other signal types available).
    # _enforce_final_quality(is_expansion=True) must NOT raise ValueError.
    logger.info("Test 1: 12 pricing playbook + 0 non-pricing → no crash in expansion mode")
    queries_t1 = [
        _make_query(SignalType.pricing_pressure.value, entity=e, is_playbook=True)
        for i, e in enumerate(["Nvidia"] * 5 + ["AMD"] * 4 + ["Supermicro"] * 3)
    ]
    trimmed_t1 = _trim_queries_to_limit(
        queries_t1,
        max_queries=MAX_EXPANSION_QUERIES,
        expected_companies=DEMO_COMPANIES,
        required_signal_types=REQUIRED_SIGNAL_TYPES,
        require_market_query=False,
        require_priority_investor_signals=False,
        signal_minimums={},
    )
    assert len(trimmed_t1) <= MAX_EXPANSION_QUERIES, f"Test 1 trim: expected ≤{MAX_EXPANSION_QUERIES}, got {len(trimmed_t1)}"

    planner = QueryPlanner(api_key=None)
    telemetry_t1: dict = {
        "original_query_count": len(queries_t1),
        "accepted_query_count": len(trimmed_t1),
        "rejected_query_count": 0,
        "rejected_reasons_by_type": defaultdict(int),
        "signal_coverage_after_planning": [q.signal_type.value for q in trimmed_t1],
    }
    try:
        result_t1 = planner._enforce_final_quality(
            queries=trimmed_t1,
            telemetry=telemetry_t1,
            expected_companies=DEMO_COMPANIES,
            min_queries=1,
            max_queries=MAX_EXPANSION_QUERIES,
            required_signal_types=REQUIRED_SIGNAL_TYPES,
            require_all_companies=False,
            require_market_query=False,
            require_priority_investor_signals=False,
            signal_minimums=None,
            is_expansion=True,
        )
        unsatisfied = planner.last_query_telemetry.get("expansion_unsatisfied_signals", [])
        recovered = planner.last_query_telemetry.get("expansion_failure_recovered", False)
        assert recovered is True, "Test 1: expansion_failure_recovered should be True"
        assert set(unsatisfied) == {"investor_signal", "product_launch", "supplier_risk"}, \
            f"Test 1: unexpected unsatisfied signals: {unsatisfied}"
        results["test1_no_crash_on_pricing_only"] = {
            "passed": True,
            "queries_returned": len(result_t1),
            "expansion_unsatisfied_signals": unsatisfied,
            "expansion_failure_recovered": recovered,
        }
        logger.info("Test 1 PASSED: no ValueError; best-effort returned; unsatisfied=%s", unsatisfied)
    except ValueError as exc:
        results["test1_no_crash_on_pricing_only"] = {"passed": False, "error": str(exc)}
        logger.error("Test 1 FAILED: ValueError raised: %s", exc)
        all_passed = False

    # ── Test 2 ──────────────────────────────────────────────────────────────────
    # 12 pricing playbook + 1 each of investor_signal, product_launch, supplier_risk.
    # After fix, _trim_queries_to_limit must preserve required signal types before playbook.
    # All 4 required signal types must be present after trim.
    logger.info("Test 2: 12 pricing playbook + 1 each of 3 non-pricing → required types preserved after trim")
    pricing_queries_t2 = [
        _make_query(SignalType.pricing_pressure.value, entity=e, is_playbook=True)
        for e in ["Nvidia"] * 5 + ["AMD"] * 4 + ["Supermicro"] * 3
    ]
    non_pricing_t2 = [
        _make_query(SignalType.investor_signal.value, entity="Nvidia"),
        _make_query(SignalType.product_launch.value, entity="AMD"),
        _make_query(SignalType.supplier_risk.value, entity="Supermicro"),
    ]
    queries_t2 = pricing_queries_t2 + non_pricing_t2
    trimmed_t2 = _trim_queries_to_limit(
        queries_t2,
        max_queries=MAX_EXPANSION_QUERIES,
        expected_companies=DEMO_COMPANIES,
        required_signal_types=REQUIRED_SIGNAL_TYPES,
        require_market_query=False,
        require_priority_investor_signals=False,
        signal_minimums={},
    )
    covered_t2 = {q.signal_type.value for q in trimmed_t2}
    missing_t2 = REQUIRED_SIGNAL_TYPES - covered_t2
    assert len(trimmed_t2) <= MAX_EXPANSION_QUERIES, f"Test 2: expected ≤{MAX_EXPANSION_QUERIES}, got {len(trimmed_t2)}"
    if missing_t2:
        results["test2_required_types_preserved"] = {
            "passed": False,
            "error": f"missing required signal types after trim: {sorted(missing_t2)}",
            "covered": sorted(covered_t2),
        }
        logger.error("Test 2 FAILED: missing required types after trim: %s", sorted(missing_t2))
        all_passed = False
    else:
        results["test2_required_types_preserved"] = {
            "passed": True,
            "trimmed_count": len(trimmed_t2),
            "covered_signal_types": sorted(covered_t2),
        }
        logger.info("Test 2 PASSED: all required types preserved; count=%d covered=%s",
                    len(trimmed_t2), sorted(covered_t2))

    # ── Test 3 ──────────────────────────────────────────────────────────────────
    # Expansion where only pricing_pressure is the missing type (single missing).
    # Playbook queries cover pricing_pressure; other signal types already covered.
    # _enforce_final_quality(is_expansion=True) should pass cleanly (no unsatisfied signals).
    logger.info("Test 3: single missing signal = pricing_pressure → playbook covers it, clean pass")
    pricing_queries_t3 = [
        _make_query(SignalType.pricing_pressure.value, entity=e, is_playbook=True)
        for e in ["Nvidia"] * 3 + ["AMD"] * 2 + ["Supermicro"] * 2
    ]
    other_queries_t3 = [
        _make_query(SignalType.investor_signal.value, entity="Nvidia"),
        _make_query(SignalType.product_launch.value, entity="AMD"),
        _make_query(SignalType.supplier_risk.value, entity="Supermicro"),
    ]
    queries_t3 = pricing_queries_t3 + other_queries_t3
    trimmed_t3 = _trim_queries_to_limit(
        queries_t3,
        max_queries=MAX_EXPANSION_QUERIES,
        expected_companies=DEMO_COMPANIES,
        required_signal_types=REQUIRED_SIGNAL_TYPES,
        require_market_query=False,
        require_priority_investor_signals=False,
        signal_minimums={},
    )
    telemetry_t3: dict = {
        "original_query_count": len(queries_t3),
        "accepted_query_count": len(trimmed_t3),
        "rejected_query_count": 0,
        "rejected_reasons_by_type": defaultdict(int),
        "signal_coverage_after_planning": [q.signal_type.value for q in trimmed_t3],
    }
    try:
        result_t3 = planner._enforce_final_quality(
            queries=trimmed_t3,
            telemetry=telemetry_t3,
            expected_companies=DEMO_COMPANIES,
            min_queries=1,
            max_queries=MAX_EXPANSION_QUERIES,
            required_signal_types=REQUIRED_SIGNAL_TYPES,
            require_all_companies=False,
            require_market_query=False,
            require_priority_investor_signals=False,
            signal_minimums=None,
            is_expansion=True,
        )
        unsatisfied_t3 = planner.last_query_telemetry.get("expansion_unsatisfied_signals", [])
        recovered_t3 = planner.last_query_telemetry.get("expansion_failure_recovered", False)
        covered_t3 = {q.signal_type.value for q in result_t3}
        if missing_t3 := (REQUIRED_SIGNAL_TYPES - covered_t3):
            results["test3_single_missing_pricing"] = {
                "passed": False,
                "error": f"required types missing after expansion: {sorted(missing_t3)}",
            }
            logger.error("Test 3 FAILED: missing after expansion: %s", sorted(missing_t3))
            all_passed = False
        else:
            results["test3_single_missing_pricing"] = {
                "passed": True,
                "queries_returned": len(result_t3),
                "expansion_unsatisfied_signals": unsatisfied_t3,
                "expansion_failure_recovered": recovered_t3,
                "covered_signal_types": sorted(covered_t3),
            }
            logger.info("Test 3 PASSED: pricing_pressure covered by playbook; covered=%s", sorted(covered_t3))
    except ValueError as exc:
        results["test3_single_missing_pricing"] = {"passed": False, "error": str(exc)}
        logger.error("Test 3 FAILED: ValueError raised: %s", exc)
        all_passed = False

    # ── Test 4 ──────────────────────────────────────────────────────────────────
    # Round 0 (non-expansion) with missing signal type MUST still raise ValueError.
    # is_expansion=False → fatal path preserved.
    logger.info("Test 4: round 0 (is_expansion=False) with missing types → must still raise ValueError")
    pricing_only_t4 = [
        _make_query(SignalType.pricing_pressure.value, entity="Nvidia", is_playbook=True)
        for _ in range(5)
    ]
    telemetry_t4: dict = {
        "original_query_count": 5,
        "accepted_query_count": 5,
        "rejected_query_count": 0,
        "rejected_reasons_by_type": defaultdict(int),
        "signal_coverage_after_planning": [SignalType.pricing_pressure.value],
    }
    try:
        planner._enforce_final_quality(
            queries=pricing_only_t4,
            telemetry=telemetry_t4,
            expected_companies=DEMO_COMPANIES,
            min_queries=1,
            max_queries=50,
            required_signal_types=REQUIRED_SIGNAL_TYPES,
            require_all_companies=False,
            require_market_query=False,
            require_priority_investor_signals=False,
            signal_minimums=None,
            is_expansion=False,
        )
        results["test4_round0_still_raises"] = {
            "passed": False,
            "error": "Expected ValueError but none was raised",
        }
        logger.error("Test 4 FAILED: expected ValueError but none raised")
        all_passed = False
    except ValueError as exc:
        results["test4_round0_still_raises"] = {
            "passed": True,
            "error_message": str(exc),
        }
        logger.info("Test 4 PASSED: ValueError raised as expected: %s", exc)

    return {"all_passed": all_passed, "tests": results}


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "pipeline_audit_artifacts", f"agent1_expansion_test_{ts}"
    )
    os.makedirs(output_dir, exist_ok=True)

    log_path = os.path.join(output_dir, "agent1_expansion_test.log")
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(file_handler)

    logger.info("Agent 1 expansion stability test — Sprint 5")
    logger.info("Output dir: %s", output_dir)

    results = run_tests()

    results_path = os.path.join(output_dir, "agent1_expansion_test_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("Results written to %s", results_path)

    if results["all_passed"]:
        logger.info("ALL TESTS PASSED — safe to proceed with demo pipeline")
        print("\nALL TESTS PASSED — safe to proceed with demo pipeline")
        sys.exit(0)
    else:
        failed = [name for name, r in results["tests"].items() if not r.get("passed")]
        logger.error("TESTS FAILED: %s — do NOT run demo pipeline", failed)
        print(f"\nTESTS FAILED: {failed} — do NOT run demo pipeline")
        sys.exit(1)


if __name__ == "__main__":
    main()
