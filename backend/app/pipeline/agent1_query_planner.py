# Agent 1 — Query Planner
# Research methods: Step-Back Prompting (arXiv:2310.06117)
#                   Multi-HyDE-inspired query fan-out (arXiv:2509.16369, step 1 only — see FIX 4)
# Two-phase: (1) abstract signal identification via Step-Back, (2) non-equivalent query fan-out
from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse as _urlparse

from app.config.companies import COMPANIES
from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
from app.config.quality_gates import MAX_EXPANSION_ROUNDS, MIN_EXPANSION_QUERIES, MIN_QUERIES, MIN_SIGNAL_TYPES
from app.config.signal_types import SIGNAL_DESCRIPTIONS, SIGNAL_WEIGHTS
from app.config.source_tiers import TOOL_MAPPING
from app.schemas.models import SearchQuery, SignalType
from app.utils.helpers import generate_uuid
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class _CoverageValidationError(ValueError):
    """Raised when one or more companies have zero query coverage."""
    def __init__(self, zero_coverage: set[str]) -> None:
        super().__init__(f"Coverage FAIL: companies with 0 queries: {sorted(zero_coverage)}")
        self.zero_coverage = zero_coverage


class _InvestorSignalCoverageValidationError(ValueError):
    """Raised when priority companies have no investor_signal query."""
    def __init__(self, missing_companies: list[str]) -> None:
        super().__init__(
            "Quality gate FAIL: missing investor_signal coverage for priority companies. "
            f"Missing: {missing_companies}"
        )
        self.missing_companies = missing_companies


# ── Valid values for LLM output validation ───────────────────────────────────
_ALL_SIGNAL_TYPES = [st.value for st in SignalType]
_VALID_SIGNAL_TYPES = set(_ALL_SIGNAL_TYPES)
_VALID_SOURCE_TYPES = set(TOOL_MAPPING.keys())
_VALID_ENTITIES = {c.name for c in COMPANIES} | {"market"}
_VALID_TIERS = {1, 2, 3, 4}
_VALID_PRIORITIES = {1, 2, 3}
PRIORITY_COMPANIES = ["Nvidia", "AMD", "Intel", "Dell", "HPE", "Micron"]
_PRIORITY_INVESTOR_COMPANIES = set(PRIORITY_COMPANIES)
_TIME_ANCHOR_RE = re.compile(
    r"(\b(?:2025|2026)\b|\blast\s+7\s+days\b|\bQ[12]\b)",
    re.IGNORECASE,
)
_NORMAL_SIGNAL_QUERY_MINIMUMS = {
    SignalType.investor_signal.value: 5,
    SignalType.news_sentiment.value: 4,
    SignalType.pricing_pressure.value: 4,
    SignalType.strategic_messaging.value: 3,
    SignalType.hiring_momentum.value: 3,
    SignalType.product_launch.value: 3,
    SignalType.supplier_risk.value: 2,
}

# ── Prompt fragments built from config and domain playbooks ───────────────────
_SIGNAL_TYPES_BLOCK = "\n".join(
    f"  {name:<20} ({weight:.2f}) — {SIGNAL_DESCRIPTIONS[name]}"
    for name, weight in sorted(SIGNAL_WEIGHTS.items(), key=lambda x: -x[1])
)
_ENTITY_ENUM = " | ".join(f'"{c.name}"' for c in COMPANIES) + ' | "market"'
_SIGNAL_TYPE_ENUM = " | ".join(f'"{st}"' for st in _ALL_SIGNAL_TYPES)
# "protected" (Web Unlocker) is excluded from Agent 1 — it is not a searchable source type
_SOURCE_TYPE_ENUM = " | ".join(f'"{k}"' for k in TOOL_MAPPING if k != "protected")
_AGENT1_SOURCE_TYPES = {k for k in TOOL_MAPPING if k != "protected"}

# Company metadata for site: operator suggestions and company-specific query text.
_COMPANY_CONTEXT_BLOCK = "\n".join(
    (
        f"  {c.name} ({c.ticker}): primary_domain={c.domain}; "
        f"ir_domain={_urlparse(c.ir_url).netloc}; "
        f"careers_domain={_urlparse(c.careers_url).netloc}; "
        f"aliases={', '.join(c.known_aliases)}"
    )
    for c in COMPANIES
)

_SIGNAL_PLAYBOOK_BLOCK = """\
  investor_signal      min 5  sources: ir_pages, serp_news
    angles: 13F/institutional ownership, 8-K/10-Q/10-K, guidance revision, earnings transcript, analyst upgrade/downgrade
    operators: site:sec.gov, company IR domain, "earnings call transcript", "guidance", "13F", ticker
  news_sentiment       min 4  sources: serp_news
    angles: Reuters/Bloomberg/WSJ-style coverage, analyst notes, customer wins/losses, regulatory or competitive pressure
    operators: company alias + "last 7 days", ticker, "AI server", "accelerator", "data center"
  pricing_pressure     min 4  sources: pricing_pages, dynamic_pages, serp_news
    angles: GPU/server discounts, distributor availability, lead times, cloud GPU price changes, margin pressure
    operators: "price", "discount", "availability", "lead time", CDW, Insight, distributor, cloud GPU
  strategic_messaging  min 3  sources: ir_pages, dynamic_pages, serp_news
    angles: CEO/CFO comments, investor day, earnings call, AI roadmap, capex/data-center positioning
    operators: "investor day", "earnings call", "AI strategy", "data center", company IR domain
  hiring_momentum      min 3  sources: job_pages, dynamic_pages
    angles: AI accelerator roles, GPU architects, data-center sales/solutions roles, hiring freeze or layoffs
    operators: careers domain, site:linkedin.com, "GPU architect", "AI accelerator", "CUDA", "data center"
  product_launch       min 3  sources: ir_pages, dynamic_pages, serp_news
    angles: AI chip/server launch, roadmap update, benchmark claim, partner launch, availability announcement
    operators: product name, "launch", "available", "press release", "AI accelerator", company domain
  supplier_risk        min 2  sources: serp_news, ir_pages
    angles: memory/HBM constraints, foundry packaging constraints, export controls, supplier concentration, component shortages
    operators: "supply risk", "shortage", "export control", "HBM", "CoWoS", "supplier concentration"\
"""

_STEP_BACK_REQUIRED_FIELDS = {
    "positive_evidence",
    "negative_evidence",
    "reliable_sources",
    "query_angles",
    "source_domains",
    "search_terms",
    "avoid_patterns",
}

# ── System prompts ────────────────────────────────────────────────────────────

_STEP_BACK_SYSTEM = """\
You are a financial market research strategist specialising in AI hardware and semiconductor markets.

STEP-BACK ABSTRACTION (arXiv:2310.06117):
Instead of immediately generating search queries, first reason at a higher level of abstraction.

Answer this step-back question:
  "What would the web evidence landscape look like for the {market} market
   under different conditions — accelerating, decelerating, or under structural stress?"

For EACH of the 7 signal types below, describe the evidence patterns:
  - "positive_evidence": what web evidence looks like if the signal is accelerating
  - "negative_evidence": what web evidence looks like if the signal is decelerating
  - "reliable_sources":  which source types carry the highest signal and why
  - "query_angles":      concrete query angles that would retrieve different documents
  - "source_domains":    reliable domains or domain patterns to prefer
  - "search_terms":      domain-specific words, ticker terms, filing terms, product terms
  - "avoid_patterns":    vague or misleading query patterns to avoid

Signal types (with their scoring weights — higher weight = more important):
{signal_types_block}

Company universe: exactly these 8 tracked companies only — {companies}
Time window: {time_window}

Signal-specific retrieval playbook:
{signal_playbook_block}

EXAMPLE (hiring_momentum):
{{
  "hiring_momentum": {{
    "positive_evidence": "High volume AI-specific role postings on LinkedIn and company career pages — GPU architects, CUDA engineers, AI accelerator designers. Multiple postings for identical senior roles signal urgency. Headcount guidance increases in earnings materials confirm momentum.",
    "negative_evidence": "Layoff announcements in AI/GPU divisions, hiring freezes in tech press, removal of previously posted AI hardware positions, WARN Act notices filed with state labor departments.",
    "reliable_sources": "LinkedIn job postings, company career pages, company IR hiring comments, and credible layoff trackers.",
    "query_angles": ["company career page AI accelerator roles", "LinkedIn GPU architect postings", "layoff or hiring freeze coverage"],
    "source_domains": ["company careers domain", "linkedin.com/jobs", "reuters.com"],
    "search_terms": ["GPU architect", "AI accelerator", "CUDA", "data center solutions", "hiring freeze"],
    "avoid_patterns": ["generic company jobs", "old evergreen job pages without date anchors"]
  }}
}}

Return ONLY a valid JSON object with exactly 7 keys — one per signal type listed above.
Each signal object must contain exactly the 7 fields shown in the example.
Do NOT generate search queries in this step. Only describe what evidence would look like.\
"""

_MULTIHYDE_SYSTEM = """\
You are a financial intelligence query planner applying a Multi-HyDE-inspired query fan-out
approach (adapted from arXiv:2509.16369 — diverse query generation step only).

Core principle: generate MULTIPLE NON-EQUIVALENT queries per signal dimension.
Each query must target a DIFFERENT evidence source — distinct source type, angle, or company —
so that the union of retrieved documents covers the full evidence space.

━━━ STEP-BACK CONTEXT (abstract signal patterns identified in prior reasoning step) ━━━
{abstract_principles}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK: Generate {target_count} search queries decomposed across 3 dimensions:
  1. Company dimension  — {company_coverage_rule}
  2. Signal dimension   — follow the signal playbook minimums, using different angles
  3. Source dimension   — match source_type to where this signal actually appears

Company universe: exactly these 8 tracked companies only — {companies}
Signal types to cover: {signal_types}
Time window: {time_window}
Current date: {current_date}
{expansion_note}{low_coverage_note}{quality_retry_note}

COMPANY METADATA (use domains for site: operators and aliases inside query_text):
{company_context_block}
  SEC filings: site:sec.gov

SIGNAL PLAYBOOK AND NORMAL-MODE MINIMUMS:
{signal_playbook_block}

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

GOOD query examples (specific, time-anchored, source-targeted):
  ✓ "Nvidia Q1 2026 13F institutional holdings Vanguard BlackRock site:sec.gov"
  ✓ "AMD MI300X AI accelerator engineer hiring site:linkedin.com May 2026"
  ✓ "Intel Gaudi 3 GPU pricing CDW Insight distributor availability May 2026"

BAD query examples (too vague, no time anchor, no source target):
  ✗ "Nvidia news" — too vague, no time anchor, no source
  ✗ "AI hardware market" — no company, no signal type, no source

RULES — READ CAREFULLY:
  ✓ Every query MUST include a time anchor: month+year, quarter+year, or "last 7 days"
  ✓ Each query targets exactly ONE (entity × signal_type × source_type) triple
  ✓ No two queries retrieve the same documents — vary entity, angle, and source
  ✓ Use site: operators from company metadata when targeting IR/careers/SEC sources
  ✓ Use the abstract patterns from Step-Back to guide query hypotheses
  ✓ Normal mode MUST cover every one of the 8 companies and every one of the 7 signal types
  ✓ Normal mode MUST satisfy the signal minimums in the playbook
  ✓ Normal mode MUST include at least 1 investor_signal query for each priority company: Nvidia, AMD, Intel, Dell, HPE, Micron
  ✓ Use target_entity="market" only for broad sector queries; company-specific queries must name one company
  ✓ Do not introduce untracked companies as target_entity; competitors/suppliers may appear only inside query_text context
  ✗ Do NOT generate paraphrases of the same query
  ✗ Do NOT use a ticker alone when the company name or alias would improve retrieval
  ✗ Do NOT include any prose, explanation, or markdown outside the JSON array

Return ONLY a valid JSON array. Each element must have exactly these fields:
[
  {{
    "query_text":           "the actual search query string",
    "target_entity":        {entity_enum},
    "signal_type":          {signal_type_enum},
    "source_type":          {source_type_enum},
    "priority":             1 | 2 | 3,
    "expected_source_tier": 1 | 2 | 3 | 4
  }}
]\
"""


class QueryPlanner:
    def __init__(self, api_key: str | None = None) -> None:
        self._llm = LLMClient(api_key=api_key, agent_name="agent1")
        self.last_step_back_output: str = ""

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
          1. Step-Back abstraction — identify abstract signal patterns (JSON output)
          2. Multi-HyDE-inspired fan-out — generate non-equivalent queries
          3. Validate quality constraints (count, signal types, company coverage)

        On expansion_round >= 1 and low_signal_types provided, generates gap-filling
        queries targeting only underrepresented signal types (5–10 queries).
        """
        if expansion_round >= MAX_EXPANSION_ROUNDS:
            raise ValueError(
                f"expansion_round={expansion_round} >= MAX_EXPANSION_ROUNDS={MAX_EXPANSION_ROUNDS}. "
                "Hard stop — do not call run() again."
            )

        expansion_signal_types = low_signal_types or []
        is_expansion = expansion_round > 0 and bool(expansion_signal_types)
        signal_types = expansion_signal_types if is_expansion else _ALL_SIGNAL_TYPES
        target_count = "5 to 10" if is_expansion else "40 to 50"
        min_queries = MIN_EXPANSION_QUERIES if is_expansion else MIN_QUERIES
        required_signal_types = set(signal_types)
        require_all_companies = not is_expansion
        company_coverage_rule = (
            "cover all 8 tracked companies with at least 1 query each, plus at least 1 market-level query"
            if require_all_companies
            else "target only the low-coverage gaps; choose the most relevant tracked companies, and do not force all 8"
        )

        companies_str = ", ".join(companies)
        current_date = datetime.now().strftime("%B %d, %Y")

        # ── Phase 1: Step-Back abstraction (arXiv:2310.06117) — runs once ─────
        logger.info("Phase 1: Step-Back abstraction (round=%d)", expansion_round)
        step_back_system = _STEP_BACK_SYSTEM.format(
            market=market,
            companies=companies_str,
            time_window=time_window,
            signal_types_block=_SIGNAL_TYPES_BLOCK,
            signal_playbook_block=_SIGNAL_PLAYBOOK_BLOCK,
        )
        raw_step_back = self._llm.call_json(
            system=step_back_system,
            user=f"Identify the abstract signal patterns for {market} ({time_window}). Return only the JSON object.",
            max_tokens=4096,
        )
        step_back = self._validate_step_back(raw_step_back)
        abstract_principles = json.dumps(step_back, indent=2)
        self.last_step_back_output = abstract_principles
        logger.info("Step-Back returned structured JSON (%d signal keys)", len(step_back))
        logger.info("Step-Back complete (%d chars)", len(abstract_principles))

        expansion_note = ""
        if is_expansion:
            expansion_note = (
                f"\n⚠ EXPANSION ROUND {expansion_round}: Generate gap-filling queries ONLY.\n"
                f"Low-coverage signal types to target: {', '.join(expansion_signal_types)}\n"
                "Do NOT generate queries for other signal types."
            )

        # ── Phase 2+3: Multi-HyDE + validation, with per-company coverage retry ─
        logger.info("Phase 2: Multi-HyDE-inspired query generation (target=%s queries)", target_count)
        low_coverage_companies: list[str] = []
        quality_retry_note = ""
        for _attempt in range(2):
            low_coverage_note = (
                f"\n⚠ COVERAGE RETRY: These companies had 0 queries in the previous attempt — "
                f"you MUST include at least 1 query for each: {', '.join(low_coverage_companies)}"
                if low_coverage_companies else ""
            )
            multihyde_system = _MULTIHYDE_SYSTEM.format(
                abstract_principles=abstract_principles,
                target_count=target_count,
                company_coverage_rule=company_coverage_rule,
                companies=companies_str,
                signal_types=", ".join(signal_types),
                time_window=time_window,
                current_date=current_date,
                expansion_note=expansion_note,
                low_coverage_note=low_coverage_note,
                quality_retry_note=quality_retry_note,
                company_context_block=_COMPANY_CONTEXT_BLOCK,
                signal_playbook_block=_SIGNAL_PLAYBOOK_BLOCK,
                entity_enum=_ENTITY_ENUM,
                signal_type_enum=_SIGNAL_TYPE_ENUM,
                source_type_enum=_SOURCE_TYPE_ENUM,
            )
            raw_queries = self._llm.call_json(
                system=multihyde_system,
                user="Generate the queries now. Return only the JSON array.",
                max_tokens=8192,
            )
            try:
                queries = self._parse_and_validate(
                    raw_queries,
                    companies,
                    min_queries,
                    required_signal_types=required_signal_types,
                    allowed_signal_types=required_signal_types if is_expansion else _VALID_SIGNAL_TYPES,
                    require_all_companies=require_all_companies,
                    require_market_query=not is_expansion,
                    require_priority_investor_signals=not is_expansion,
                    signal_minimums=None if is_expansion else _NORMAL_SIGNAL_QUERY_MINIMUMS,
                )
                break
            except _CoverageValidationError as exc:
                if _attempt == 0:
                    low_coverage_companies = sorted(exc.zero_coverage)
                    logger.warning("Company coverage retry: 0-query companies: %s", low_coverage_companies)
                    continue
                raise
            except _InvestorSignalCoverageValidationError as exc:
                if _attempt == 0:
                    low_coverage_companies = exc.missing_companies
                    quality_retry_note = (
                        "\n⚠ INVESTOR SIGNAL RETRY: These priority companies had no "
                        "investor_signal query. Generate at least 1 query for each with "
                        f'signal_type="investor_signal": {", ".join(low_coverage_companies)}'
                    )
                    logger.warning(
                        "Investor-signal coverage retry: missing priority companies: %s",
                        low_coverage_companies,
                    )
                    continue
                raise
            except ValueError as exc:
                if _attempt == 0:
                    quality_retry_note = (
                        "\n⚠ QUALITY RETRY: The previous JSON failed validation. "
                        f"Correct this exact issue: {exc}"
                    )
                    logger.warning("Query quality retry: %s", exc)
                    continue
                raise

        logger.info(
            "Generated %d queries covering %d signal types, %d companies",
            len(queries),
            len({q.signal_type for q in queries}),
            len({q.target_entity for q in queries if q.target_entity != "market"}),
        )
        return queries

    # ── Internal ──────────────────────────────────────────────────────────────

    def _validate_step_back(self, raw: object) -> dict[str, object]:
        if not isinstance(raw, dict):
            raise ValueError(f"Step-Back returned {type(raw).__name__}, expected JSON object")

        keys = set(raw.keys())
        missing_signals = _VALID_SIGNAL_TYPES - keys
        extra_signals = keys - _VALID_SIGNAL_TYPES
        if missing_signals or extra_signals:
            raise ValueError(
                "Step-Back JSON must contain exactly the 7 configured signal types. "
                f"Missing={sorted(missing_signals)} extra={sorted(extra_signals)}"
            )

        for signal_type, entry in raw.items():
            if not isinstance(entry, dict):
                raise ValueError(f"Step-Back field '{signal_type}' must be an object")
            fields = set(entry.keys())
            missing_fields = _STEP_BACK_REQUIRED_FIELDS - fields
            extra_fields = fields - _STEP_BACK_REQUIRED_FIELDS
            if missing_fields or extra_fields:
                raise ValueError(
                    f"Step-Back field '{signal_type}' must contain exactly "
                    f"{sorted(_STEP_BACK_REQUIRED_FIELDS)}. "
                    f"Missing={sorted(missing_fields)} extra={sorted(extra_fields)}"
                )
            for field in _STEP_BACK_REQUIRED_FIELDS:
                value = entry[field]
                if isinstance(value, str) and value.strip():
                    continue
                if isinstance(value, list) and value and all(isinstance(v, str) and v.strip() for v in value):
                    continue
                raise ValueError(
                    f"Step-Back field '{signal_type}.{field}' must be a non-empty string or string list"
                )

        return raw

    def _parse_and_validate(
        self,
        raw: list,
        expected_companies: List[str],
        min_queries: int = MIN_QUERIES,
        required_signal_types: Optional[set[str]] = None,
        allowed_signal_types: Optional[set[str]] = None,
        require_all_companies: bool = True,
        require_market_query: bool = False,
        require_priority_investor_signals: bool = False,
        signal_minimums: Optional[dict[str, int]] = None,
    ) -> List[SearchQuery]:
        if not isinstance(raw, list):
            raise ValueError(f"LLM returned {type(raw).__name__}, expected list")

        parsed: List[SearchQuery] = []
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
                # FIX 1: entity must be a tracked company or "market"
                if q.target_entity not in _VALID_ENTITIES:
                    logger.warning("Skipping query %d: invalid target_entity '%s'", i, q.target_entity)
                    skipped += 1
                    continue
                if allowed_signal_types and q.signal_type.value not in allowed_signal_types:
                    logger.debug("Skipping query %d: signal_type '%s' outside requested set", i, q.signal_type.value)
                    skipped += 1
                    continue
                if q.source_type not in _AGENT1_SOURCE_TYPES:
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
                if not _has_time_anchor(q.query_text):
                    logger.debug("Skipping query %d: missing time anchor '%s'", i, q.query_text)
                    skipped += 1
                    continue
                parsed.append(q)
            except (KeyError, ValueError) as exc:
                logger.debug("Skipping malformed query %d: %s", i, exc)
                skipped += 1

        # FIX 9: deduplicate by (entity, signal_type, source_type) triple — keep first occurrence
        seen_triples: set[tuple] = set()
        queries: List[SearchQuery] = []
        for q in parsed:
            triple = (q.target_entity, q.signal_type, q.source_type)
            if triple in seen_triples:
                logger.debug("Deduplicating repeated triple %s", triple)
                skipped += 1
                continue
            seen_triples.add(triple)
            queries.append(q)

        if skipped:
            logger.warning("Skipped %d malformed/duplicate queries from LLM output", skipped)

        # Quality gates — FIX 2: use caller-supplied min_queries threshold
        if len(queries) < min_queries:
            raise ValueError(
                f"Quality gate FAIL: generated {len(queries)} queries, minimum is {min_queries}. "
                "The LLM output did not meet the minimum query count requirement."
            )

        covered_signal_types = {q.signal_type.value for q in queries}
        if required_signal_types:
            missing_signals = required_signal_types - covered_signal_types
            if missing_signals:
                raise ValueError(
                    "Quality gate FAIL: missing required signal types. "
                    f"Missing: {sorted(missing_signals)}"
                )
        elif len(covered_signal_types) < MIN_SIGNAL_TYPES:
            raise ValueError(
                f"Quality gate FAIL: queries cover {len(covered_signal_types)} signal types, "
                f"minimum is {MIN_SIGNAL_TYPES}. "
                f"Missing: {_VALID_SIGNAL_TYPES - covered_signal_types}"
            )

        if signal_minimums:
            signal_counts: dict[str, int] = defaultdict(int)
            for q in queries:
                signal_counts[q.signal_type.value] += 1
            under_minimum = {
                signal_type: {"actual": signal_counts.get(signal_type, 0), "minimum": minimum}
                for signal_type, minimum in signal_minimums.items()
                if signal_counts.get(signal_type, 0) < minimum
            }
            if under_minimum:
                raise ValueError(
                    "Quality gate FAIL: signal query minimums not met. "
                    f"Under minimum: {under_minimum}"
                )

        covered_entities = {q.target_entity for q in queries}
        if require_market_query and "market" not in covered_entities:
            raise ValueError("Quality gate FAIL: missing required market-level query")

        if require_all_companies:
            zero_coverage = {c for c in expected_companies if c not in covered_entities}
            if zero_coverage:
                raise _CoverageValidationError(zero_coverage)

        if require_priority_investor_signals:
            investor_entities = {
                q.target_entity
                for q in queries
                if q.signal_type == SignalType.investor_signal
            }
            expected_priority = _PRIORITY_INVESTOR_COMPANIES & set(expected_companies)
            missing_investor = sorted(expected_priority - investor_entities)
            if missing_investor:
                raise _InvestorSignalCoverageValidationError(missing_investor)

        return queries


def _has_time_anchor(query_text: str) -> bool:
    return bool(_TIME_ANCHOR_RE.search(query_text))


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s  %(name)s  %(message)s",
    )
    load_dotenv()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set in environment / .env", file=sys.stderr)
        sys.exit(1)

    companies = [c.name for c in COMPANIES]
    planner = QueryPlanner(api_key=api_key)

    print("\nRunning Query Planner — Step-Back + Multi-HyDE-inspired fan-out\n" + "=" * 60)
    queries = planner.run(
        market=DEFAULT_MARKET,
        companies=companies,
        time_window=DEFAULT_TIME_WINDOW,
    )

    # Group by signal_type for review
    groups: dict = defaultdict(list)
    for q in queries:
        groups[q.signal_type.value].append(q)

    company_counts = defaultdict(int)
    for q in queries:
        if q.target_entity != "market":
            company_counts[q.target_entity] += 1
    zero_coverage = [c for c in companies if company_counts[c] == 0]

    total_signal_types = len(groups)
    print(f"\nTotal queries         : {len(queries)}")
    print(f"Signal types covered  : {total_signal_types} / 7")
    print(f"Companies covered     : {len(companies) - len(zero_coverage)} / {len(companies)}")
    if zero_coverage:
        print(f"⚠ Zero-coverage      : {zero_coverage}")
    print(f"{'=' * 60}\n")

    for signal_type in sorted(groups.keys(), key=lambda s: -SIGNAL_WEIGHTS.get(s, 0)):
        qs = groups[signal_type]
        weight = SIGNAL_WEIGHTS.get(signal_type, 0)
        print(f"[{signal_type.upper()}]  weight={weight}  ({len(qs)} queries)")
        for q in sorted(qs, key=lambda x: x.priority):
            tier_badge = f"T{q.expected_source_tier}"
            print(f"  P{q.priority} {tier_badge}  [{q.source_type:14s}]  [{q.target_entity:12s}]  {q.query_text}")
        print()
