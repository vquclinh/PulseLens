# Agent 1 — Query Planner
# Research methods: Step-Back Prompting (arXiv:2310.06117) + Multi-HyDE (arXiv:2509.16369)
# Two-phase: (1) abstract signal identification, (2) non-equivalent query fan-out
from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import datetime
from typing import List, Optional

from app.config.companies import COMPANIES
from app.config.signal_types import SIGNAL_WEIGHTS
from app.config.source_tiers import TOOL_MAPPING
from app.schemas.models import SearchQuery, SignalType
from app.utils.helpers import generate_uuid
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ── Quality constraints (ARCHITECTURE.md §3) ─────────────────────────────────
MIN_QUERIES = 15
MIN_SIGNAL_TYPES = 5       # must cover at least 5 of 7 signal types
MAX_EXPANSION_ROUNDS = 2   # hard stop — prevents infinite pipeline loops

# ── Valid values for LLM output validation ───────────────────────────────────
_VALID_SIGNAL_TYPES = {st.value for st in SignalType}
_VALID_SOURCE_TYPES = set(TOOL_MAPPING.keys())
_VALID_ENTITIES = {c.name for c in COMPANIES} | {"market"}
_VALID_TIERS = {1, 2, 3, 4}
_VALID_PRIORITIES = {1, 2, 3}

# ── System prompts ────────────────────────────────────────────────────────────

_STEP_BACK_SYSTEM = """\
You are a financial market research strategist specialising in AI hardware and semiconductor markets.

STEP-BACK ABSTRACTION (arXiv:2310.06117):
Instead of immediately generating search queries, first reason at a higher level of abstraction.

Answer this step-back question:
  "What would the web evidence landscape look like for the {market} market
   under different conditions — accelerating, decelerating, or under structural stress?"

For EACH of the 7 signal types below, describe in 2-4 sentences:
  (a) What positive/accelerating evidence would look like on the web
  (b) What negative/decelerating evidence would look like
  (c) Which source types carry the most reliable signal and why

Signal types (with their scoring weights — higher weight = more important):
  hiring_momentum      (0.12) — workforce signals on job boards, LinkedIn
  product_launch       (0.07) — press releases, product pages, IR announcements
  pricing_pressure     (0.18) — GPU/server pricing, distributor listings, deal announcements
  strategic_messaging  (0.15) — CEO comments, earnings calls, investor day presentations
  investor_signal      (0.25) — SEC 8-K/10-K/13F filings, earnings guidance, analyst upgrades
  news_sentiment       (0.20) — Reuters/Bloomberg/WSJ coverage, analyst reports
  supplier_risk        (0.03) — supply chain news, component shortages, concentration mentions

Companies to track: {companies}
Time window: {time_window}

Write plain text. This analysis will directly guide query generation — be specific and actionable.\
"""

_MULTIHYDE_SYSTEM = """\
You are a financial intelligence query planner applying Multi-HyDE methodology (arXiv:2509.16369).

Multi-HyDE principle: generate MULTIPLE NON-EQUIVALENT queries per signal dimension.
Unlike multi-query methods that produce similar paraphrases, each query here must target
a DIFFERENT hypothetical document — distinct source type, angle, or company — so that
the union of retrieved documents covers the full evidence space.

━━━ STEP-BACK CONTEXT (abstract signal patterns identified in prior reasoning step) ━━━
{abstract_principles}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK: Generate {target_count} search queries decomposed across 3 dimensions:
  1. Company dimension  — at least 1 query per company + 1 market-level query
  2. Signal dimension   — 2-3 queries per signal type, using different angles
  3. Source dimension   — match source_type to where this signal actually appears

Companies: {companies}
Signal types to cover: {signal_types}
Time window: {time_window}
Current date: {current_date}
{expansion_note}

SOURCE TYPE DEFINITIONS (must use exactly these values):
  "serp_news"     → news search, press coverage          → expected tier: 2-3
  "job_pages"     → LinkedIn / Glassdoor / Indeed posts  → expected tier: 4
  "ir_pages"      → SEC EDGAR, company IR pages          → expected tier: 1
  "pricing_pages" → pricing pages, distributor listings  → expected tier: 4
  "dynamic_pages" → JS-rendered earnings/product sites   → expected tier: 1-2

PRIORITY (assign based on signal weight and source tier):
  1 = high importance (investor_signal, tier-1/2 sources)
  2 = medium (news_sentiment, hiring, pricing)
  3 = supplementary (product_launch, supplier_risk, tier-4 sources)

RULES — READ CAREFULLY:
  ✓ Each query targets exactly ONE (entity × signal_type × source_type) triple
  ✓ No two queries retrieve the same documents — vary entity, angle, and source
  ✓ Phrase each query as it would be typed into a search engine or API call
  ✓ Use the abstract patterns from Step-Back to guide query hypotheses
  ✗ Do NOT generate paraphrases of the same query
  ✗ Do NOT include any prose, explanation, or markdown outside the JSON array

Return ONLY a valid JSON array. Each element must have exactly these fields:
[
  {{
    "query_text":           "the actual search query string",
    "target_entity":        "Nvidia" | "AMD" | "Intel" | "Broadcom" | "Supermicro" | "Dell" | "HPE" | "Micron" | "market",
    "signal_type":          "hiring_momentum" | "product_launch" | "pricing_pressure" | "strategic_messaging" | "investor_signal" | "news_sentiment" | "supplier_risk",
    "source_type":          "serp_news" | "job_pages" | "ir_pages" | "pricing_pages" | "dynamic_pages",
    "priority":             1 | 2 | 3,
    "expected_source_tier": 1 | 2 | 3 | 4
  }}
]\
"""


class QueryPlanner:
    def __init__(self, api_key: str) -> None:
        self._llm = LLMClient(api_key=api_key)

    def run(
        self,
        market: str,
        companies: List[str],
        time_window: str,
        expansion_round: int = 0,
        low_signal_types: Optional[List[str]] = None,
    ) -> List[SearchQuery]:
        """
        Full query planning pipeline:
          1. Step-Back abstraction — identify abstract signal patterns
          2. Multi-HyDE decomposition — generate non-equivalent queries
          3. Validate quality constraints

        On expansion_round >= 1 and low_signal_types provided, generates gap-filling
        queries targeting only underrepresented signal types (5–10 queries).
        """
        if expansion_round >= MAX_EXPANSION_ROUNDS:
            raise ValueError(
                f"expansion_round={expansion_round} >= MAX_EXPANSION_ROUNDS={MAX_EXPANSION_ROUNDS}. "
                "Hard stop — do not call run() again."
            )

        is_expansion = bool(low_signal_types and expansion_round > 0)
        signal_types = low_signal_types if is_expansion else list(_VALID_SIGNAL_TYPES)
        target_count = "5 to 10" if is_expansion else "15 to 20"

        companies_str = ", ".join(companies)
        current_date = datetime.now().strftime("%B %d, %Y")

        # ── Phase 1: Step-Back abstraction (arXiv:2310.06117) ─────────────────
        logger.info("Phase 1: Step-Back abstraction (round=%d)", expansion_round)
        step_back_system = _STEP_BACK_SYSTEM.format(
            market=market,
            companies=companies_str,
            time_window=time_window,
        )
        abstract_principles = self._llm.call_text(
            system=step_back_system,
            user=f"Identify the abstract signal patterns for {market} ({time_window}).",
        )
        logger.info("Step-Back complete (%d chars)", len(abstract_principles))

        # ── Phase 2: Multi-HyDE decomposition (arXiv:2509.16369) ──────────────
        logger.info("Phase 2: Multi-HyDE query generation (target=%s queries)", target_count)
        expansion_note = ""
        if is_expansion:
            expansion_note = (
                f"\n⚠ EXPANSION ROUND {expansion_round}: Generate gap-filling queries ONLY.\n"
                f"Low-coverage signal types to target: {', '.join(low_signal_types)}\n"
                "Do NOT generate queries for other signal types."
            )

        multihyde_system = _MULTIHYDE_SYSTEM.format(
            abstract_principles=abstract_principles,
            target_count=target_count,
            companies=companies_str,
            signal_types=", ".join(signal_types),
            time_window=time_window,
            current_date=current_date,
            expansion_note=expansion_note,
        )
        raw_queries = self._llm.call_json(
            system=multihyde_system,
            user="Generate the queries now. Return only the JSON array.",
            max_tokens=4096,
        )

        # ── Phase 3: Parse, assign IDs, validate ──────────────────────────────
        queries = self._parse_and_validate(raw_queries, market)
        logger.info(
            "Generated %d queries covering %d signal types",
            len(queries),
            len({q.signal_type for q in queries}),
        )
        return queries

    # ── Internal ──────────────────────────────────────────────────────────────

    def _parse_and_validate(self, raw: list, market: str) -> List[SearchQuery]:
        if not isinstance(raw, list):
            raise ValueError(f"LLM returned {type(raw).__name__}, expected list")

        queries: List[SearchQuery] = []
        skipped = 0
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                skipped += 1
                continue
            try:
                q = SearchQuery(
                    query_id=f"q_{generate_uuid()[:8]}",
                    query_text=item["query_text"].strip(),
                    target_entity=item["target_entity"],
                    signal_type=SignalType(item["signal_type"]),
                    source_type=item["source_type"],
                    priority=int(item["priority"]),
                    expected_source_tier=int(item["expected_source_tier"]),
                )
                # Field-level sanity checks
                if q.source_type not in _VALID_SOURCE_TYPES:
                    logger.debug("Skipping query %d: invalid source_type '%s'", i, q.source_type)
                    skipped += 1
                    continue
                if q.expected_source_tier not in _VALID_TIERS:
                    skipped += 1
                    continue
                if q.priority not in _VALID_PRIORITIES:
                    skipped += 1
                    continue
                if not q.query_text:
                    skipped += 1
                    continue
                queries.append(q)
            except (KeyError, ValueError) as exc:
                logger.debug("Skipping malformed query %d: %s", i, exc)
                skipped += 1

        if skipped:
            logger.warning("Skipped %d malformed queries from LLM output", skipped)

        # Quality gates
        if len(queries) < MIN_QUERIES:
            raise ValueError(
                f"Quality gate FAIL: generated {len(queries)} queries, minimum is {MIN_QUERIES}. "
                "The LLM output did not meet the minimum query count requirement."
            )

        covered = {q.signal_type for q in queries}
        if len(covered) < MIN_SIGNAL_TYPES:
            raise ValueError(
                f"Quality gate FAIL: queries cover {len(covered)} signal types, "
                f"minimum is {MIN_SIGNAL_TYPES}. "
                f"Missing: {_VALID_SIGNAL_TYPES - {s.value for s in covered}}"
            )

        return queries


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s  %(name)s  %(message)s",
    )
    load_dotenv()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in environment / .env", file=sys.stderr)
        sys.exit(1)

    companies = [c.name for c in COMPANIES]
    planner = QueryPlanner(api_key=api_key)

    print("\nRunning Query Planner — Step-Back + Multi-HyDE\n" + "=" * 60)
    queries = planner.run(
        market="US AI Hardware / Semiconductor",
        companies=companies,
        time_window="last 7 days",
    )

    # Group by signal_type for review
    groups: dict = defaultdict(list)
    for q in queries:
        groups[q.signal_type.value].append(q)

    total_signal_types = len(groups)
    print(f"\nTotal queries : {len(queries)}")
    print(f"Signal types covered : {total_signal_types} / 7")
    print(f"{'=' * 60}\n")

    for signal_type in sorted(groups.keys(), key=lambda s: -SIGNAL_WEIGHTS.get(s, 0)):
        qs = groups[signal_type]
        weight = SIGNAL_WEIGHTS.get(signal_type, 0)
        print(f"[{signal_type.upper()}]  weight={weight}  ({len(qs)} queries)")
        for q in sorted(qs, key=lambda x: x.priority):
            tier_badge = f"T{q.expected_source_tier}"
            print(f"  P{q.priority} {tier_badge}  [{q.source_type:14s}]  [{q.target_entity:12s}]  {q.query_text}")
        print()
