"""
Sprint 8 — Pricing browser routing zero-cost static tests.

Tests the BrightData Web Unlocker + Browser API escalation logic added to agent2_web_workers.py:
  T1-T4:  should_escalate_pricing_page — escalation decision logic
  T5-T9:  should_allow_browser_pricing_domain — domain allowlist
  T10:    choose_better_pricing_payload — content selection
  T11:    _maybe_browser_escalate_pricing — async escalation (browser failure path)
  T12:    count_pricing_patterns — regex pattern matching

All tests: zero API calls, zero BrightData calls. Synchronous helpers tested directly;
async helper tested with asyncio.run + a mock client that raises.

Output: prints PASS/FAIL per test, exits with code 0 (all pass) or 1 (any fail).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.pipeline.agent2_web_workers import (
    MIN_CONTENT_CHARS,
    _PRICING_UNLOCKER_MIN_CONTENT_CHARS,
    _PRICING_MIN_PRICE_PATTERN_COUNT,
    count_pricing_patterns,
    should_allow_browser_pricing_domain,
    should_escalate_pricing_page,
    choose_better_pricing_payload,
    _maybe_browser_escalate_pricing,
)

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

P = "✅ PASS"
F = "❌ FAIL"

_failures: list[str] = []


def _check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  {P}  {label}")
    else:
        msg = f"{label}" + (f": {detail}" if detail else "")
        print(f"  {F}  {msg}")
        _failures.append(msg)


# ── T1: snippet_only content triggers escalation ─────────────────────────────

print("\n── T1: snippet_only content triggers escalation ────────────────────")
short = "x" * (MIN_CONTENT_CHARS - 1)  # 119 chars — below MIN_CONTENT_CHARS
esc, reason = should_escalate_pricing_page(short, "https://coreweave.com/pricing", "pricing_pages", 0)
_check("snippet_only → should_escalate=True", esc is True, f"got {esc}")
_check("snippet_only → reason='snippet_only'", reason == "snippet_only", f"got {reason!r}")


# ── T2: short content (> MIN but < UNLOCKER_MIN) triggers escalation ─────────

print("\n── T2: short content triggers escalation ───────────────────────────")
medium = "x" * 200  # 200 chars: > MIN_CONTENT_CHARS but < _PRICING_UNLOCKER_MIN_CONTENT_CHARS (1500)
esc2, reason2 = should_escalate_pricing_page(medium, "https://runpod.io/pricing", "pricing_pages", 0)
_check("content_too_short → should_escalate=True", esc2 is True, f"got {esc2}")
_check("content_too_short → reason='content_too_short'", reason2 == "content_too_short", f"got {reason2!r}")


# ── T3: long content with 0 price patterns triggers escalation ───────────────

print("\n── T3: long content with no price patterns triggers escalation ─────")
long_no_price = "GPU instance compute cloud availability AI accelerator " * 50  # > 1500 chars, no $ patterns
long_no_price_len = len(long_no_price)
price_count_3 = count_pricing_patterns(long_no_price)
esc3, reason3 = should_escalate_pricing_page(long_no_price, "https://coreweave.com/cloud", "pricing_pages", price_count_3)
_check(
    f"no_pricing_patterns (len={long_no_price_len}) → should_escalate=True",
    esc3 is True,
    f"got {esc3}",
)
_check("no_pricing_patterns → reason='no_pricing_patterns'", reason3 == "no_pricing_patterns", f"got {reason3!r}")


# ── T4: long content with price patterns → no escalation ─────────────────────

print("\n── T4: sufficient pricing content → no escalation ──────────────────")
good_content = (
    "NVIDIA H100 GPU cloud instance $2.50/hr on-demand pricing. "
    "H200 available at $3.00/hr. Reserved instances from $1.80/hr. "
    "MI300X instances available at $2.20/hr with 10% discount for annual commitment. "
) * 20  # > 1500 chars, multiple price patterns
price_count_4 = count_pricing_patterns(good_content)
esc4, reason4 = should_escalate_pricing_page(good_content, "https://coreweave.com/pricing", "pricing_pages", price_count_4)
_check(
    f"sufficient content (len={len(good_content)}, patterns={price_count_4}) → should_escalate=False",
    esc4 is False,
    f"got {esc4}",
)
_check("sufficient_content → reason='sufficient_content'", reason4 == "sufficient_content", f"got {reason4!r}")


# ── T5: sec.gov → never escalate ─────────────────────────────────────────────

print("\n── T5: sec.gov → should_allow_browser_pricing_domain=False ─────────")
sec_result = should_allow_browser_pricing_domain("https://sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=nvda")
_check("sec.gov → not allowed", sec_result is False, f"got {sec_result}")


# ── T6: ir.amd.com → never escalate ──────────────────────────────────────────

print("\n── T6: ir.amd.com → should_allow_browser_pricing_domain=False ──────")
ir_result = should_allow_browser_pricing_domain("https://ir.amd.com/news-releases/news-release-details/amd-reports-q1-2026")
_check("ir.amd.com → not allowed", ir_result is False, f"got {ir_result}")


# ── T7: source_type != pricing_pages → no escalation ─────────────────────────

print("\n── T7: source_type=serp_news → should_escalate=False ───────────────")
esc7, reason7 = should_escalate_pricing_page("x" * 50, "https://coreweave.com/pricing", "serp_news", 0)
_check("serp_news → should_escalate=False", esc7 is False, f"got {esc7}")
_check("serp_news → reason='not_pricing_pages'", reason7 == "not_pricing_pages", f"got {reason7!r}")


# ── T8: coreweave.com → allowed ───────────────────────────────────────────────

print("\n── T8: coreweave.com → should_allow_browser_pricing_domain=True ────")
coreweave_result = should_allow_browser_pricing_domain("https://coreweave.com/cloud/pricing/gpu-instances")
_check("coreweave.com → allowed", coreweave_result is True, f"got {coreweave_result}")


# ── T9: random domain → not allowed ─────────────────────────────────────────

print("\n── T9: example.com → should_allow_browser_pricing_domain=False ─────")
random_result = should_allow_browser_pricing_domain("https://example.com/pricing")
_check("example.com → not allowed", random_result is False, f"got {random_result}")


# ── T10: choose_better_pricing_payload prefers browser when more patterns ────

print("\n── T10: choose_better_pricing_payload → prefers browser with more patterns")
normal_payload = {"content": "H100 GPU compute cloud. " * 30}   # no price patterns
browser_payload = {"content": "H100 $2.50/hr, H200 $3.00/hr. " * 30}  # has price patterns
better = choose_better_pricing_payload(normal_payload, browser_payload)
_check("browser has more patterns → returns browser_payload", better is browser_payload)

# Also test that normal is kept when browser has fewer patterns
normal_with_prices = {"content": "H100 $2.50/hr H200 $3.00/hr MI300X $2.20/hr available. " * 30}
browser_no_prices = {"content": "GPU instance compute cloud available regions. " * 30}
better2 = choose_better_pricing_payload(normal_with_prices, browser_no_prices)
_check("normal has more patterns → returns normal_payload", better2 is normal_with_prices)


# ── T11: browser exception → returns normal_payload, browser_error recorded ──

print("\n── T11: _maybe_browser_escalate_pricing — browser exception path ───")

class _FailingClient:
    has_browser_zone = True
    async def scrape_dynamic_page(self, url: str) -> dict[str, Any]:
        raise RuntimeError("Simulated browser API timeout")


async def _run_t11() -> None:
    client = _FailingClient()
    # Use short content so escalation is attempted
    thin_payload: dict[str, Any] = {"content": "x" * 50, "url": "https://coreweave.com/pricing"}
    query_audit: dict[str, Any] = {}
    result = await _maybe_browser_escalate_pricing(
        client,  # type: ignore[arg-type]
        "https://coreweave.com/pricing",
        thin_payload,
        query_audit,
    )
    _check("browser exception → returns original normal_payload", result is thin_payload)
    escalations = query_audit.get("pricing_escalations", [])
    _check("escalation record written to query_audit", len(escalations) == 1, f"got {len(escalations)}")
    if escalations:
        rec = escalations[0]
        _check("escalated_to_browser=True recorded", rec.get("escalated_to_browser") is True)
        _check(
            "browser_error is non-empty string",
            isinstance(rec.get("browser_error"), str) and len(rec["browser_error"]) > 0,
            f"got {rec.get('browser_error')!r}",
        )
        _check("final_scrape_method remains 'normal'", rec.get("final_scrape_method") == "normal", f"got {rec.get('final_scrape_method')!r}")

asyncio.run(_run_t11())


# ── T12: count_pricing_patterns — pattern matching ────────────────────────────

print("\n── T12: count_pricing_patterns — regex patterns ─────────────────────")
samples = [
    ("H100 $2.50/hr on-demand", 1),            # $2.50/hr matches
    ("Price: $1,200.00 USD for GPU server", 1), # $1,200.00 matches
    ("No pricing info available here today", 0),
    ("$100 $200 $300", 3),
    ("per hour rental available per month subscription", 2),  # per.*hour + per.*month
]
for text, expected_min in samples:
    cnt = count_pricing_patterns(text)
    # Use >= expected_min to allow for overlapping patterns
    _check(
        f"count_pricing_patterns({text[:40]!r}) >= {expected_min}",
        cnt >= expected_min,
        f"got {cnt}",
    )

# Empty string
_check("empty string → 0 patterns", count_pricing_patterns("") == 0)


# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'─' * 60}")
if _failures:
    print(f"❌ {len(_failures)} test(s) FAILED:")
    for f_msg in _failures:
        print(f"   • {f_msg}")
    sys.exit(1)
else:
    print(f"✅ All 12 pricing browser routing tests passed")
    sys.exit(0)
