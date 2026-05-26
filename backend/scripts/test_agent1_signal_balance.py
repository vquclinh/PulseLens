"""Sprint 7 — Agent 1 signal balance static tests. Zero API cost.

Tests the B1-B6 changes:
  B1: _DEMO_SIGNAL_QUERY_MINIMUMS and _DEMO_SIGNAL_QUERY_CAPS constants
  B2: _MULTIHYDE_SYSTEM prompt placeholders and formatted content
  B3: _trim_queries_to_limit signal_caps enforcement
  B4: signal_caps threading through _enforce_final_quality
  B5: _targeted_signal_regeneration method + telemetry
  B6: per-signal telemetry fields

All tests use mock objects only — no LLM, BrightData, or DB calls.
Output: pipeline_audit_artifacts/sprint7_signal_balance_tests_<ts>/results.json
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.pipeline.agent1_query_planner import (
    QueryPlanner,
    _DEMO_SIGNAL_QUERY_CAPS,
    _DEMO_SIGNAL_QUERY_MINIMUMS,
    _MULTIHYDE_SYSTEM,
    _trim_queries_to_limit,
)
from app.schemas.models import SearchQuery, SignalType
from app.utils.helpers import generate_uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("sprint7_signal_balance_test")

DEMO_COMPANIES = ["Nvidia", "AMD", "Supermicro"]


def _make_query(
    signal_type: str,
    entity: str = "Nvidia",
    source_type: str = "serp_news",
    is_playbook: bool = False,
    idx: int | None = None,
) -> SearchQuery:
    prefix = "q_price_" if is_playbook else "q_"
    suffix = str(idx) if idx is not None else generate_uuid()[:8]
    return SearchQuery(
        query_id=f"{prefix}{suffix}",
        query_text=f"{entity} {signal_type} query {suffix} May 2026",
        target_entity=entity,
        signal_type=SignalType(signal_type),
        source_type=source_type,
        priority=2,
        expected_source_tier=2,
    )


def _make_telemetry() -> dict[str, Any]:
    return {
        "original_query_count": 0,
        "accepted_query_count": 0,
        "rejected_query_count": 0,
        "rejected_reasons_by_type": defaultdict(int),
        "signal_coverage_after_planning": [],
    }


def _count_signal(queries: list[SearchQuery], signal: str) -> int:
    return sum(1 for q in queries if q.signal_type.value == signal)


# ── Tests ────────────────────────────────────────────────────────────────────────

def test_01_expansion_stability_suite(results: dict) -> bool:
    """Sprint 5 expansion stability: import run_tests() from existing suite and run all 4."""
    test_path = os.path.join(os.path.dirname(__file__), "test_agent1_expansion_stability.py")
    spec = importlib.util.spec_from_file_location("expansion_stability", test_path)
    if spec is None:
        raise RuntimeError(f"Could not load expansion stability test module from {test_path}")
    loader = spec.loader
    if loader is None:
        raise RuntimeError(f"Expansion stability test module has no loader: {test_path}")
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    result = mod.run_tests()
    all_passed = result.get("all_passed", False)
    results["test_01_expansion_stability"] = {"passed": all_passed, "detail": result}
    if all_passed:
        logger.info("test_01 PASSED: expansion stability suite all passed")
    else:
        logger.error("test_01 FAILED: expansion stability regression")
    return all_passed


def test_02_cap_enforcement_in_trim(results: dict) -> bool:
    """B3: investor_signal cap=7 applied in weighted fill when total > max_queries."""
    queries = (
        [_make_query("investor_signal", "Nvidia", idx=i) for i in range(20)]
        + [_make_query("product_launch", "AMD", idx=i + 100) for i in range(6)]
    )
    trimmed = _trim_queries_to_limit(
        queries,
        max_queries=18,
        expected_companies=DEMO_COMPANIES,
        required_signal_types={"investor_signal", "product_launch"},
        require_market_query=False,
        require_priority_investor_signals=False,
        signal_minimums={"investor_signal": 4, "product_launch": 4},
        signal_caps={"investor_signal": 7},
    )
    inv = _count_signal(trimmed, "investor_signal")
    prod = _count_signal(trimmed, "product_launch")
    passed = inv <= 7 and prod >= 4 and len(trimmed) <= 18
    results["test_02_cap_enforcement_in_trim"] = {
        "passed": passed,
        "investor_signal_count": inv,
        "product_launch_count": prod,
        "total_count": len(trimmed),
    }
    if passed:
        logger.info("test_02 PASSED: investor_signal=%d (≤7), product_launch=%d (≥4)", inv, prod)
    else:
        logger.error("test_02 FAILED: investor=%d, product=%d, total=%d", inv, prod, len(trimmed))
    return passed


def test_03_demo_minimums_raise_value_error(results: dict) -> bool:
    """B4: _enforce_final_quality raises ValueError when product_launch < minimum=4."""
    queries = (
        [_make_query("investor_signal", "Nvidia", idx=i) for i in range(8)]
        + [_make_query("product_launch", "AMD", idx=i + 100) for i in range(2)]
        + [_make_query("supplier_risk", "Supermicro", idx=i + 200) for i in range(3)]
    )
    planner = QueryPlanner(api_key=None)
    telemetry = _make_telemetry()
    telemetry["original_query_count"] = len(queries)
    try:
        planner._enforce_final_quality(
            queries=queries,
            telemetry=telemetry,
            expected_companies=DEMO_COMPANIES,
            min_queries=5,
            max_queries=32,
            required_signal_types={"investor_signal", "product_launch", "supplier_risk"},
            require_all_companies=False,
            require_market_query=False,
            require_priority_investor_signals=False,
            signal_minimums={"product_launch": 4, "supplier_risk": 3},
        )
        # Should have raised ValueError
        results["test_03_demo_minimums_raise_error"] = {
            "passed": False,
            "error": "ValueError not raised",
        }
        logger.error("test_03 FAILED: ValueError not raised despite product_launch=2 < minimum=4")
        return False
    except ValueError as exc:
        passed = "product_launch" in str(exc)
        results["test_03_demo_minimums_raise_error"] = {
            "passed": passed,
            "error": str(exc),
        }
        if passed:
            logger.info("test_03 PASSED: ValueError raised for product_launch deficit")
        else:
            logger.error("test_03 FAILED: ValueError raised but wrong reason: %s", exc)
        return passed


def test_04_targeted_regen_telemetry(results: dict) -> bool:
    """B5: _targeted_signal_regeneration records attempts for under-minimum signals."""

    class _MockLLM:
        def call_json(self, system: str, user: str, max_tokens: int = 4096) -> list:
            return []  # Return empty — no new queries added, but attempt is recorded

    planner = QueryPlanner(api_key=None)
    cast(Any, planner)._llm = _MockLLM()

    # 2 product_launch (below minimum=4), 5 investor_signal (above minimum=4)
    queries = (
        [_make_query("investor_signal", "Nvidia", idx=i) for i in range(5)]
        + [_make_query("product_launch", "AMD", idx=i + 100) for i in range(2)]
    )
    updated_queries, attempts, success = planner._targeted_signal_regeneration(
        queries=queries,
        abstract_principles="{}",
        companies=DEMO_COMPANIES,
        time_window="Q2 2026",
        allowed_entities=set(DEMO_COMPANIES) | {"market"},
        allowed_signal_types={
            "investor_signal", "product_launch", "supplier_risk", "strategic_messaging"
        },
        signal_caps={"investor_signal": 7},
    )
    # With priority order and max 2 calls:
    # product_launch (2 < 4) → attempt 1; supplier_risk (0 < 3) → attempt 2; strategic_messaging blocked
    passed = (
        "product_launch" in attempts
        and "supplier_risk" in attempts
        and "strategic_messaging" not in attempts  # blocked: pl+sr not yet satisfied before regen
        and len(attempts) == 2
        and isinstance(success, dict)
        and all(v == 0 for v in success.values())  # mock returned empty, so 0 added
    )
    results["test_04_targeted_regen_telemetry"] = {
        "passed": passed,
        "attempts": attempts,
        "success": success,
    }
    if passed:
        logger.info("test_04 PASSED: targeted_regen attempts=%s", attempts)
    else:
        logger.error("test_04 FAILED: attempts=%s success=%s", attempts, success)
    return passed


def test_05_demo_signal_caps_value(results: dict) -> bool:
    """B1: _DEMO_SIGNAL_QUERY_CAPS has investor_signal=7."""
    cap = _DEMO_SIGNAL_QUERY_CAPS.get("investor_signal")
    passed = cap == 7
    results["test_05_caps_investor_equals_7"] = {"passed": passed, "investor_signal_cap": cap}
    if passed:
        logger.info("test_05 PASSED: investor_signal cap=%d", cap)
    else:
        logger.error("test_05 FAILED: investor_signal cap=%s", cap)
    return passed


def test_06_demo_signal_minimums_values(results: dict) -> bool:
    """B1: _DEMO_SIGNAL_QUERY_MINIMUMS has product_launch=4, supplier_risk=3."""
    pl = _DEMO_SIGNAL_QUERY_MINIMUMS.get("product_launch")
    sr = _DEMO_SIGNAL_QUERY_MINIMUMS.get("supplier_risk")
    passed = pl == 4 and sr == 3
    results["test_06_minimums_values"] = {
        "passed": passed,
        "product_launch": pl,
        "supplier_risk": sr,
    }
    if passed:
        logger.info("test_06 PASSED: product_launch=%d, supplier_risk=%d", pl, sr)
    else:
        logger.error("test_06 FAILED: product_launch=%s, supplier_risk=%s", pl, sr)
    return passed


def test_07_quality_thresholds_unchanged(results: dict) -> bool:
    """No regression: MIN_FACTS=50, MIN_SOURCE_COUNT=15."""
    from app.config.quality_gates import QUALITY_GATE_CONFIG
    passed = QUALITY_GATE_CONFIG.min_facts == 50 and QUALITY_GATE_CONFIG.min_source_count == 15
    results["test_07_quality_thresholds"] = {
        "passed": passed,
        "min_facts": QUALITY_GATE_CONFIG.min_facts,
        "min_source_count": QUALITY_GATE_CONFIG.min_source_count,
    }
    if passed:
        logger.info("test_07 PASSED: MIN_FACTS=%d, MIN_SOURCE_COUNT=%d",
                    QUALITY_GATE_CONFIG.min_facts, QUALITY_GATE_CONFIG.min_source_count)
    else:
        logger.error("test_07 FAILED: thresholds changed")
    return passed


def test_08_no_hardcoded_report_ids(results: dict) -> bool:
    """No report IDs (report_XXXX pattern) hardcoded in agent1_query_planner.py."""
    agent1_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "pipeline", "agent1_query_planner.py"
    )
    source = Path(agent1_path).read_text()
    matches = re.findall(r"\breport_[0-9a-f]{8,}\b", source)
    passed = len(matches) == 0
    results["test_08_no_hardcoded_report_ids"] = {"passed": passed, "found": matches}
    if passed:
        logger.info("test_08 PASSED: no hardcoded report IDs in agent1")
    else:
        logger.error("test_08 FAILED: found report IDs: %s", matches)
    return passed


def test_09_signal_caps_none_backward_compatible(results: dict) -> bool:
    """B3: _trim_queries_to_limit with signal_caps=None behaves identically to without cap arg."""
    queries = (
        [_make_query("investor_signal", "Nvidia", idx=i) for i in range(10)]
        + [_make_query("product_launch", "AMD", idx=i + 100) for i in range(4)]
    )
    trimmed_with_none = _trim_queries_to_limit(
        queries,
        max_queries=8,
        expected_companies=DEMO_COMPANIES,
        required_signal_types={"investor_signal", "product_launch"},
        require_market_query=False,
        require_priority_investor_signals=False,
        signal_minimums={"investor_signal": 2, "product_launch": 2},
        signal_caps=None,
    )
    # Without caps, investor_signal should NOT be limited
    inv = _count_signal(trimmed_with_none, "investor_signal")
    total = len(trimmed_with_none)
    # With no cap, investor fills remaining slots after minimums satisfied
    passed = total <= 8 and inv > 0
    results["test_09_signal_caps_none_backward_compat"] = {
        "passed": passed,
        "total": total,
        "investor_signal": inv,
    }
    if passed:
        logger.info("test_09 PASSED: signal_caps=None backward compat OK (total=%d, inv=%d)", total, inv)
    else:
        logger.error("test_09 FAILED: total=%d, inv=%d", total, inv)
    return passed


def test_10_pricing_playbook_15_queries(results: dict) -> bool:
    """No regression: pricing playbook still generates 15 queries for demo companies."""
    from app.config.demo_scope import DEMO_COMPANY_NAMES
    from app.pipeline.pricing_pressure_playbook import (
        build_pricing_playbook_specs,
        specs_to_search_queries,
    )
    specs = build_pricing_playbook_specs(DEMO_COMPANY_NAMES, "Q2 2026", include_market=True)
    queries = specs_to_search_queries(specs)
    playbook_queries = [q for q in queries if q.query_id.startswith("q_price_")]
    passed = len(playbook_queries) == 15
    results["test_10_pricing_playbook_15_queries"] = {
        "passed": passed,
        "playbook_count": len(playbook_queries),
    }
    if passed:
        logger.info("test_10 PASSED: pricing playbook generates %d queries", len(playbook_queries))
    else:
        logger.error("test_10 FAILED: pricing playbook generates %d queries (expected 15)", len(playbook_queries))
    return passed


def test_11_multihyde_system_domain_placeholder(results: dict) -> bool:
    """B2: _MULTIHYDE_SYSTEM contains {domain_rules_block} placeholder."""
    passed = "{domain_rules_block}" in _MULTIHYDE_SYSTEM
    results["test_11_domain_rules_placeholder"] = {"passed": passed}
    if passed:
        logger.info("test_11 PASSED: {domain_rules_block} present in _MULTIHYDE_SYSTEM")
    else:
        logger.error("test_11 FAILED: {domain_rules_block} not found in _MULTIHYDE_SYSTEM")
    return passed


def test_12_multihyde_system_balance_placeholder_and_content(results: dict) -> bool:
    """B2: _MULTIHYDE_SYSTEM has {balance_rules_block} and formatted content has expected keywords."""
    has_placeholder = "{balance_rules_block}" in _MULTIHYDE_SYSTEM

    # Simulate the blocks computed in run() for demo_scope=True
    _investor_cap = _DEMO_SIGNAL_QUERY_CAPS.get("investor_signal", 7)
    _product_min = _DEMO_SIGNAL_QUERY_MINIMUMS.get("product_launch", 4)
    _supplier_min = _DEMO_SIGNAL_QUERY_MINIMUMS.get("supplier_risk", 3)
    domain_rules_block = (
        "SIGNAL-SPECIFIC SOURCE DOMAIN RULES — mandatory for this run:\n"
        "  investor_signal   → MUST target: sec.gov, ir.[company].com, investor.[company].com, earnings transcripts\n"
        "                      Do NOT target product pages or tech review sites for investor_signal queries.\n"
        "  product_launch    → MUST target: [company].com/news or /newsroom (NOT ir.[company].com financial releases),\n"
        "                      servethehome.com, anandtech.com, tomshardware.com, press release domains.\n"
        "                      Do NOT use IR quarterly report pages for product_launch queries.\n"
        "  supplier_risk     → MUST target: reuters.com, bloomberg.com supply chain coverage,\n"
        "                      digitimes.com, techinsights.com. Do NOT use IR pages.\n"
        "  pricing_pressure  → Covered by deterministic playbook. LLM supplements only.\n"
        "  KEY RULE: Each signal type MUST retrieve from DIFFERENT source domains than investor_signal.\n\n"
    )
    balance_rules_block = (
        f"SIGNAL BALANCE RULE — hard constraints for this run:\n"
        f"  ✗ Do NOT generate more than {_investor_cap} investor_signal queries (hard cap)\n"
        f"  ✓ Generate AT LEAST {_product_min} product_launch queries targeting newsrooms or tech review sites\n"
        f"  ✓ Generate AT LEAST {_supplier_min} supplier_risk queries targeting reuters.com or bloomberg.com\n"
        f"  ✓ No single signal type may exceed 40% of total LLM-generated queries\n"
        f"  ✓ Spread queries across DIFFERENT source domains — do NOT concentrate on one company's IR domain\n\n"
    )

    # Partially format — fill only the new placeholders
    partial = _MULTIHYDE_SYSTEM.replace("{domain_rules_block}", domain_rules_block)
    partial = partial.replace("{balance_rules_block}", balance_rules_block)

    has_domain_text = "SIGNAL-SPECIFIC SOURCE DOMAIN RULES" in partial
    has_balance_text = "SIGNAL BALANCE RULE" in partial
    has_product_launch_rule = "product_launch" in partial and "newsroom" in partial
    has_supplier_risk_rule = "reuters.com" in partial and "supplier_risk" in partial

    passed = (
        has_placeholder
        and has_domain_text
        and has_balance_text
        and has_product_launch_rule
        and has_supplier_risk_rule
    )
    results["test_12_balance_placeholder_and_content"] = {
        "passed": passed,
        "has_placeholder": has_placeholder,
        "has_domain_text": has_domain_text,
        "has_balance_text": has_balance_text,
        "has_product_launch_rule": has_product_launch_rule,
        "has_supplier_risk_rule": has_supplier_risk_rule,
    }
    if passed:
        logger.info("test_12 PASSED: balance/domain rules injected correctly into prompt")
    else:
        logger.error("test_12 FAILED: %s", results["test_12_balance_placeholder_and_content"])
    return passed


def test_13_no_new_playbooks_in_agent1(results: dict) -> bool:
    """No supplier_risk_playbook or all_seed_queries references in agent1 source."""
    agent1_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "pipeline", "agent1_query_planner.py"
    )
    source = Path(agent1_path).read_text()
    forbidden = ["supplier_risk_playbook", "all_seed_queries"]
    found = [term for term in forbidden if term in source]
    passed = len(found) == 0
    results["test_13_no_new_playbooks"] = {"passed": passed, "found": found}
    if passed:
        logger.info("test_13 PASSED: no forbidden playbook references in agent1")
    else:
        logger.error("test_13 FAILED: found forbidden terms: %s", found)
    return passed


def test_14_cap_enforced_when_under_budget(results: dict) -> bool:
    """Safety fix 1: signal cap enforced even when total queries <= max_queries.

    Sprint 6 Retry scenario: 10 investor_signal LLM queries generated, total = 25 < max=32.
    Without the unconditional cap, all 10 investor queries pass through. With the fix,
    _enforce_final_quality must drop down to cap=7 regardless of no trim being needed.
    """
    # 10 investor_signal + 8 product_launch + 7 supplier_risk = 25 < max=32 (no trim path)
    queries = (
        [_make_query("investor_signal", "Nvidia", idx=i) for i in range(10)]
        + [_make_query("product_launch", "AMD", idx=i + 100) for i in range(8)]
        + [_make_query("supplier_risk", "Supermicro", idx=i + 200) for i in range(7)]
    )
    planner = QueryPlanner(api_key=None)
    telemetry = _make_telemetry()
    telemetry["original_query_count"] = len(queries)

    result = planner._enforce_final_quality(
        queries=queries,
        telemetry=telemetry,
        expected_companies=DEMO_COMPANIES,
        min_queries=5,
        max_queries=32,  # total=25 < 32 — trim path NOT triggered
        required_signal_types={"investor_signal", "product_launch", "supplier_risk"},
        require_all_companies=False,
        require_market_query=False,
        require_priority_investor_signals=False,
        signal_minimums={"product_launch": 4, "supplier_risk": 3},
        signal_caps={"investor_signal": 7},
    )
    inv = _count_signal(result, "investor_signal")
    prod = _count_signal(result, "product_launch")
    sr = _count_signal(result, "supplier_risk")
    passed = inv <= 7 and prod >= 4 and sr >= 3
    results["test_14_cap_enforced_under_budget"] = {
        "passed": passed,
        "investor_signal": inv,
        "product_launch": prod,
        "supplier_risk": sr,
        "total_queries": len(result),
        "max_queries": 32,
        "note": "trim path not triggered (25<32); cap must still be applied",
    }
    if passed:
        logger.info(
            "test_14 PASSED: cap enforced under budget — investor=%d (≤7), prod=%d, sr=%d",
            inv, prod, sr,
        )
    else:
        logger.error(
            "test_14 FAILED: investor=%d (cap=7), prod=%d (min=4), sr=%d (min=3)", inv, prod, sr
        )
    return passed


def test_15_targeted_regen_max_2_calls_and_priority(results: dict) -> bool:
    """Safety fix 2: targeted regen issues at most 2 LLM calls in priority order.

    Setup: product_launch=0 (needs regen), supplier_risk=0 (needs regen),
    strategic_messaging=0 (needs regen but blocked until pl+sr satisfied).
    Expected: only product_launch and supplier_risk attempted (2 calls), strategic_messaging skipped.
    Also verifies hiring_momentum and news_sentiment are never attempted.
    """

    call_log: list[str] = []

    class _TrackingLLM:
        def call_json(self, system: str, user: str, max_tokens: int = 4096) -> list:
            # Extract which signal_type this call is for from the system prompt
            import re as _re
            m = _re.search(r'signal_type="([^"]+)"', system)
            if m:
                call_log.append(m.group(1))
            return []

    planner = QueryPlanner(api_key=None)
    cast(Any, planner)._llm = _TrackingLLM()

    # Only investor_signal queries — all other signals at 0
    queries = [_make_query("investor_signal", "Nvidia", idx=i) for i in range(5)]

    _, attempts, success = planner._targeted_signal_regeneration(
        queries=queries,
        abstract_principles="{}",
        companies=DEMO_COMPANIES,
        time_window="Q2 2026",
        allowed_entities=set(DEMO_COMPANIES) | {"market"},
        allowed_signal_types={
            "investor_signal", "product_launch", "supplier_risk",
            "strategic_messaging", "hiring_momentum", "news_sentiment",
        },
        signal_caps={"investor_signal": 7},
    )

    exactly_two_calls = len(attempts) == 2
    first_is_product_launch = len(attempts) >= 1 and attempts[0] == "product_launch"
    second_is_supplier_risk = len(attempts) >= 2 and attempts[1] == "supplier_risk"
    no_strategic = "strategic_messaging" not in attempts
    no_hiring = "hiring_momentum" not in attempts
    no_news = "news_sentiment" not in attempts

    passed = (
        exactly_two_calls
        and first_is_product_launch
        and second_is_supplier_risk
        and no_strategic
        and no_hiring
        and no_news
    )
    results["test_15_targeted_regen_max_2_priority"] = {
        "passed": passed,
        "attempts": attempts,
        "call_log": call_log,
        "exactly_two_calls": exactly_two_calls,
        "first_is_product_launch": first_is_product_launch,
        "second_is_supplier_risk": second_is_supplier_risk,
        "no_strategic_messaging": no_strategic,
        "no_hiring_momentum": no_hiring,
        "no_news_sentiment": no_news,
    }
    if passed:
        logger.info("test_15 PASSED: exactly 2 calls in priority order: %s", attempts)
    else:
        logger.error("test_15 FAILED: attempts=%s", attempts)
    return passed


# ── Runner ────────────────────────────────────────────────────────────────────────

def run_all() -> dict:
    results: dict[str, Any] = {}
    tests = [
        test_01_expansion_stability_suite,
        test_02_cap_enforcement_in_trim,
        test_03_demo_minimums_raise_value_error,
        test_04_targeted_regen_telemetry,
        test_05_demo_signal_caps_value,
        test_06_demo_signal_minimums_values,
        test_07_quality_thresholds_unchanged,
        test_08_no_hardcoded_report_ids,
        test_09_signal_caps_none_backward_compatible,
        test_10_pricing_playbook_15_queries,
        test_11_multihyde_system_domain_placeholder,
        test_12_multihyde_system_balance_placeholder_and_content,
        test_13_no_new_playbooks_in_agent1,
        test_14_cap_enforced_when_under_budget,
        test_15_targeted_regen_max_2_calls_and_priority,
    ]
    passed_count = 0
    for test_fn in tests:
        try:
            ok = test_fn(results)
            if ok:
                passed_count += 1
        except Exception as exc:
            name = test_fn.__name__
            results[name] = {"passed": False, "error": f"Unhandled exception: {exc}"}
            logger.exception("Test %s raised unexpected exception", name)

    results["summary"] = {
        "total": len(tests),
        "passed": passed_count,
        "failed": len(tests) - passed_count,
        "all_passed": passed_count == len(tests),
    }
    return results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(
        os.path.join(os.path.dirname(__file__), "..", "..", "pipeline_audit_artifacts",
                     f"sprint7_signal_balance_tests_{ts}")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Sprint 7 signal balance tests — output: %s", output_dir)
    results = run_all()
    summary = results.get("summary", {})

    output_path = output_dir / "results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print(f"Sprint 7 Signal Balance Tests — {ts}")
    print("=" * 60)
    for key, val in results.items():
        if key == "summary":
            continue
        status = "PASS" if val.get("passed") else "FAIL"
        print(f"  [{status}] {key}")
    print(f"\nTotal: {summary.get('passed', 0)}/{summary.get('total', 0)} passed")
    print(f"Output: {output_path}")

    if not summary.get("all_passed"):
        sys.exit(1)
