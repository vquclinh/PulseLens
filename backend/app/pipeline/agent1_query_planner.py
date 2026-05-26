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
from difflib import SequenceMatcher
from typing import Any, List, Optional
from urllib.parse import urlparse as _urlparse

from app.config.companies import COMPANIES
from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
from app.config.demo_scope import get_scope_config, is_demo_scope_enabled
from app.config.quality_gates import (
    MAX_EXPANSION_QUERIES,
    MAX_EXPANSION_ROUNDS,
    MAX_MALFORMED_QUERY_RATE,
    MAX_QUERIES,
    MIN_EXPANSION_QUERIES,
    MIN_QUERIES,
    MIN_SIGNAL_TYPES,
)
from app.config.signal_types import SIGNAL_DESCRIPTIONS, SIGNAL_WEIGHTS
from app.config.source_tiers import TOOL_MAPPING
from app.pipeline.pricing_pressure_playbook import (
    build_pricing_playbook_specs,
    pricing_playbook_audit_payload,
    specs_to_search_queries,
)
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
_RAW_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_TRACKING_URL_RE = re.compile(
    r"(links\.message\.|email\.|/url\?|utm_|mkt_tok|[?&](?:trk|tracking|redirect|url)=)",
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
        self.last_query_telemetry: dict[str, Any] = {}

    def run(
        self,
        market: str,
        companies: List[str],
        time_window: str,
        expansion_round: int = 0,
        low_signal_types: Optional[List[str]] = None,
        target_signal_types: Optional[List[str]] = None,
        min_queries: Optional[int] = None,
        max_queries: Optional[int] = None,
        demo_scope_enabled: Optional[bool] = None,
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

        demo_scope = is_demo_scope_enabled() if demo_scope_enabled is None else demo_scope_enabled
        scope = get_scope_config() if demo_scope else get_scope_config(force_full=True)
        requested_signal_types = _normalize_requested_signal_types(
            target_signal_types or (scope.core_signal_types if demo_scope else _ALL_SIGNAL_TYPES)
        )
        if not requested_signal_types:
            requested_signal_types = list(_ALL_SIGNAL_TYPES)

        expansion_signal_types = [
            signal_type for signal_type in _normalize_requested_signal_types(low_signal_types or [])
            if signal_type in set(requested_signal_types)
        ]
        is_expansion = expansion_round > 0
        signal_types = expansion_signal_types if is_expansion else requested_signal_types
        if is_expansion and not signal_types:
            signal_types = requested_signal_types
        normal_min_queries = min_queries or (scope.min_queries if demo_scope else MIN_QUERIES)
        normal_max_queries = max_queries or (scope.max_queries if demo_scope else MAX_QUERIES)
        target_count = (
            f"{MIN_EXPANSION_QUERIES} to {MAX_EXPANSION_QUERIES}"
            if is_expansion
            else f"{normal_min_queries} to {normal_max_queries}"
        )
        validation_min_queries = MIN_EXPANSION_QUERIES if is_expansion else normal_min_queries
        required_signal_types = set(signal_types)
        require_all_companies = not is_expansion
        company_coverage_rule = (
            f"cover all {len(companies)} configured companies with at least 1 query each, plus at least 1 market-level query"
            if require_all_companies
            else f"target only the low-coverage gaps; choose the most relevant configured companies, and do not force all {len(companies)}"
        )

        pricing_playbook_specs = []
        pricing_playbook_queries: list[SearchQuery] = []
        pricing_playbook_payload: list[dict[str, object]] = []
        if demo_scope and SignalType.pricing_pressure.value in required_signal_types:
            pricing_playbook_specs = build_pricing_playbook_specs(companies, time_window, include_market=not is_expansion)
            pricing_playbook_queries = specs_to_search_queries(pricing_playbook_specs)
            pricing_playbook_payload = pricing_playbook_audit_payload(
                pricing_playbook_specs,
                pricing_playbook_queries,
            )
            logger.info("Agent 1 injected %d deterministic pricing playbook queries", len(pricing_playbook_queries))
            if not is_expansion:
                llm_min = max(8, normal_min_queries - len(pricing_playbook_queries))
                llm_max = max(llm_min, normal_max_queries - len(pricing_playbook_queries))
                target_count = (
                    f"{llm_min} to {llm_max} LLM-generated queries, plus "
                    f"{len(pricing_playbook_queries)} deterministic pricing_pressure playbook queries"
                )

        companies_str = ", ".join(companies)
        entity_enum = " | ".join(f'"{company}"' for company in companies) + ' | "market"'
        company_context_block = _company_context_block_for(companies)
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
            expansion_targets = expansion_signal_types or _ALL_SIGNAL_TYPES
            expansion_note = (
                f"\n⚠ EXPANSION ROUND {expansion_round}: Generate gap-filling queries ONLY.\n"
                f"Signal types to target: {', '.join(expansion_targets)}\n"
                "Keep this to the requested 5-10 replacement queries. Avoid URLs/patterns that failed previously."
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
                company_context_block=company_context_block,
                signal_playbook_block=_SIGNAL_PLAYBOOK_BLOCK,
                entity_enum=entity_enum,
                signal_type_enum=_SIGNAL_TYPE_ENUM,
                source_type_enum=_SOURCE_TYPE_ENUM,
            )
            raw_queries = self._llm.call_json(
                system=multihyde_system,
                user="Generate the queries now. Return only the JSON array.",
                max_tokens=8192,
            )
            try:
                queries = self._parse_and_validate_with_regeneration(
                    raw_queries,
                    multihyde_system,
                    companies,
                    validation_min_queries,
                    allowed_entities=set(companies) | {"market"},
                    max_queries=MAX_EXPANSION_QUERIES if is_expansion else normal_max_queries,
                    required_signal_types=required_signal_types,
                    allowed_signal_types=required_signal_types if (is_expansion or demo_scope or target_signal_types) else _VALID_SIGNAL_TYPES,
                    require_all_companies=require_all_companies,
                    require_market_query=not is_expansion,
                    require_priority_investor_signals=not is_expansion,
                    signal_minimums=None if is_expansion else _signal_minimums_for(required_signal_types),
                    seed_queries=pricing_playbook_queries,
                    seed_telemetry={
                        "pricing_playbook_query_count": len(pricing_playbook_queries),
                        "pricing_playbook_queries": pricing_playbook_payload,
                    },
                    is_expansion=is_expansion,
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

        if is_expansion:
            signal_counts: dict[str, int] = {}
            for q in queries:
                signal_counts[q.signal_type.value] = signal_counts.get(q.signal_type.value, 0) + 1
            self.last_query_telemetry.setdefault("expansion_requested_missing_signals",
                sorted(expansion_signal_types or required_signal_types))
            self.last_query_telemetry.setdefault("expansion_generated_signal_counts", signal_counts)
            self.last_query_telemetry.setdefault("expansion_trimmed_signal_counts",
                {st: signal_counts.get(st, 0) for st in required_signal_types})
            self.last_query_telemetry.setdefault("expansion_unsatisfied_signals", [])
            self.last_query_telemetry.setdefault("expansion_failure_recovered", False)
            self.last_query_telemetry["query_cap_before_after"] = {
                "max_expansion_queries": MAX_EXPANSION_QUERIES,
                "queries_returned": len(queries),
            }

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

    def _parse_and_validate_with_regeneration(
        self,
        raw: list,
        generation_system_prompt: str,
        expected_companies: List[str],
        min_queries: int = MIN_QUERIES,
        allowed_entities: Optional[set[str]] = None,
        max_queries: Optional[int] = None,
        required_signal_types: Optional[set[str]] = None,
        allowed_signal_types: Optional[set[str]] = None,
        require_all_companies: bool = True,
        require_market_query: bool = False,
        require_priority_investor_signals: bool = False,
        signal_minimums: Optional[dict[str, int]] = None,
        seed_queries: Optional[list[SearchQuery]] = None,
        seed_telemetry: Optional[dict[str, object]] = None,
        is_expansion: bool = False,
    ) -> List[SearchQuery]:
        queries, telemetry = self._parse_candidates(
            raw,
            allowed_signal_types=allowed_signal_types,
            allowed_entities=allowed_entities,
        )
        queries = _merge_seed_queries(seed_queries or [], queries, telemetry, seed_telemetry or {})
        malformed_rate = _rejection_rate(telemetry)

        if malformed_rate > MAX_MALFORMED_QUERY_RATE:
            logger.warning(
                "Agent 1 rejected %.0f%% of generated queries; requesting one replacement batch",
                malformed_rate * 100,
            )
            replacement_raw = self._llm.call_json(
                system=generation_system_prompt,
                user=self._replacement_prompt(
                    accepted=queries,
                    min_queries=min_queries,
                    max_queries=max_queries,
                    required_signal_types=required_signal_types or set(),
                    signal_minimums=signal_minimums or {},
                    expected_companies=expected_companies,
                    require_market_query=require_market_query,
                    require_priority_investor_signals=require_priority_investor_signals,
                ),
                max_tokens=4096,
            )
            replacements, replacement_telemetry = self._parse_candidates(
                replacement_raw,
                allowed_signal_types=allowed_signal_types,
                allowed_entities=allowed_entities,
                existing_queries=queries,
            )
            telemetry = _merge_telemetry(telemetry, replacement_telemetry)
            telemetry["regeneration_attempted"] = True
            telemetry["regeneration_query_count"] = (
                len(replacement_raw) if isinstance(replacement_raw, list) else 0
            )
            queries.extend(replacements)
        else:
            telemetry["regeneration_attempted"] = False
            telemetry["regeneration_query_count"] = 0

        queries = self._enforce_final_quality(
            queries=queries,
            telemetry=telemetry,
            expected_companies=expected_companies,
            min_queries=min_queries,
            max_queries=max_queries,
            required_signal_types=required_signal_types,
            require_all_companies=require_all_companies,
            require_market_query=require_market_query,
            require_priority_investor_signals=require_priority_investor_signals,
            signal_minimums=signal_minimums,
            is_expansion=is_expansion,
        )
        return queries

    def _parse_and_validate(
        self,
        raw: list,
        expected_companies: List[str],
        min_queries: int = MIN_QUERIES,
        allowed_entities: Optional[set[str]] = None,
        max_queries: Optional[int] = None,
        required_signal_types: Optional[set[str]] = None,
        allowed_signal_types: Optional[set[str]] = None,
        require_all_companies: bool = True,
        require_market_query: bool = False,
        require_priority_investor_signals: bool = False,
        signal_minimums: Optional[dict[str, int]] = None,
    ) -> List[SearchQuery]:
        queries, telemetry = self._parse_candidates(
            raw,
            allowed_signal_types=allowed_signal_types,
            allowed_entities=allowed_entities,
        )
        return self._enforce_final_quality(
            queries=queries,
            telemetry=telemetry,
            expected_companies=expected_companies,
            min_queries=min_queries,
            max_queries=max_queries,
            required_signal_types=required_signal_types,
            require_all_companies=require_all_companies,
            require_market_query=require_market_query,
            require_priority_investor_signals=require_priority_investor_signals,
            signal_minimums=signal_minimums,
        )

    def _parse_candidates(
        self,
        raw: object,
        allowed_signal_types: Optional[set[str]] = None,
        allowed_entities: Optional[set[str]] = None,
        existing_queries: Optional[list[SearchQuery]] = None,
    ) -> tuple[list[SearchQuery], dict[str, Any]]:
        telemetry: dict[str, Any] = {
            "original_query_count": len(raw) if isinstance(raw, list) else 0,
            "accepted_query_count": 0,
            "rejected_query_count": 0,
            "rejected_reasons_by_type": defaultdict(int),
            "signal_coverage_after_planning": [],
        }

        if not isinstance(raw, list):
            telemetry["rejected_reasons_by_type"]["not_json_array"] += 1
            telemetry["rejected_query_count"] += 1
            self.last_query_telemetry = _finalize_telemetry_dict(telemetry)
            raise ValueError(f"LLM returned {type(raw).__name__}, expected list")

        queries: list[SearchQuery] = []
        seen_texts = [_normalize_query_text(q.query_text) for q in (existing_queries or [])]

        def reject(reason: str, idx: int, detail: object = "") -> None:
            telemetry["rejected_reasons_by_type"][reason] += 1
            telemetry["rejected_query_count"] += 1
            logger.debug("Skipping query %d: %s %s", idx, reason, detail)

        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                reject("malformed_item", i, type(item).__name__)
                continue

            query_text = str(item.get("query_text", "")).strip()
            target_entity = str(item.get("target_entity", "")).strip()
            signal_type_raw = str(item.get("signal_type", "")).strip()
            source_type = str(item.get("source_type", "")).strip()

            if not query_text or not target_entity or not signal_type_raw or not source_type:
                reject("empty_required_field", i)
                continue
            if target_entity not in _VALID_ENTITIES:
                reject("invalid_target_entity", i, target_entity)
                continue
            if allowed_entities and target_entity not in allowed_entities:
                reject("target_entity_outside_requested_scope", i, target_entity)
                continue
            if signal_type_raw not in _VALID_SIGNAL_TYPES:
                reject("unsupported_signal_type", i, signal_type_raw)
                continue
            if allowed_signal_types and signal_type_raw not in allowed_signal_types:
                reject("signal_type_outside_requested_set", i, signal_type_raw)
                continue
            if source_type not in _AGENT1_SOURCE_TYPES:
                reject("invalid_source_type", i, source_type)
                continue
            if _has_disallowed_url(query_text):
                reject("raw_or_tracking_url_in_query_text", i, query_text[:120])
                continue
            if not _has_time_anchor(query_text):
                reject("missing_time_anchor", i, query_text)
                continue

            try:
                priority = int(item.get("priority"))
                expected_source_tier = int(item.get("expected_source_tier"))
            except (TypeError, ValueError):
                reject("invalid_numeric_field", i)
                continue
            if priority not in _VALID_PRIORITIES:
                reject("invalid_priority", i, priority)
                continue
            if expected_source_tier not in _VALID_TIERS:
                reject("invalid_expected_source_tier", i, expected_source_tier)
                continue

            normalized_text = _normalize_query_text(query_text)
            if not normalized_text:
                reject("empty_normalized_query_text", i)
                continue
            if _is_near_duplicate(normalized_text, seen_texts):
                reject("duplicate_or_near_duplicate_query_text", i, query_text)
                continue
            seen_texts.append(normalized_text)

            queries.append(
                SearchQuery(
                    query_id=f"q_{generate_uuid()[:8]}",
                    query_text=query_text,
                    target_entity=target_entity,
                    signal_type=SignalType(signal_type_raw),
                    source_type=source_type,
                    priority=priority,
                    expected_source_tier=expected_source_tier,
                )
            )

        telemetry["accepted_query_count"] = len(queries)
        telemetry["signal_coverage_after_planning"] = sorted({q.signal_type.value for q in queries})
        if telemetry["rejected_query_count"]:
            logger.warning(
                "Skipped %d malformed/duplicate queries from LLM output",
                telemetry["rejected_query_count"],
            )
        return queries, telemetry

    def _enforce_final_quality(
        self,
        queries: list[SearchQuery],
        telemetry: dict[str, Any],
        expected_companies: list[str],
        min_queries: int,
        max_queries: Optional[int],
        required_signal_types: Optional[set[str]],
        require_all_companies: bool,
        require_market_query: bool,
        require_priority_investor_signals: bool,
        signal_minimums: Optional[dict[str, int]],
        is_expansion: bool = False,
    ) -> list[SearchQuery]:
        if max_queries and len(queries) > max_queries:
            before_trim = len(queries)
            queries = _trim_queries_to_limit(
                queries,
                max_queries=max_queries,
                expected_companies=expected_companies,
                required_signal_types=required_signal_types or set(),
                require_market_query=require_market_query,
                require_priority_investor_signals=require_priority_investor_signals,
                signal_minimums=signal_minimums or {},
            )
            telemetry["trimmed_query_count"] = before_trim - len(queries)
            if len(queries) < before_trim:
                logger.info("Trimmed query plan from %d to %d queries", before_trim, len(queries))
        else:
            telemetry["trimmed_query_count"] = 0

        telemetry["accepted_query_count"] = len(queries)
        telemetry["signal_coverage_after_planning"] = sorted({q.signal_type.value for q in queries})
        self.last_query_telemetry = _finalize_telemetry_dict(telemetry)

        if len(queries) < min_queries:
            raise ValueError(
                f"Quality gate FAIL: generated {len(queries)} queries, minimum is {min_queries}. "
                "The LLM output did not meet the minimum query count requirement."
            )

        covered_signal_types = {q.signal_type.value for q in queries}
        if required_signal_types:
            missing_signals = required_signal_types - covered_signal_types
            if missing_signals:
                if is_expansion:
                    # Non-fatal in expansion mode: near-duplicate rejection may prevent full
                    # signal coverage. Return best-effort queries and let Quality Gate decide.
                    telemetry["expansion_unsatisfied_signals"] = sorted(missing_signals)
                    telemetry["expansion_failure_recovered"] = True
                    logger.warning(
                        "agent1: expansion best-effort: unsatisfied signal types=%s "
                        "(near-duplicate rejection prevented full coverage); returning %d queries",
                        sorted(missing_signals),
                        len(queries),
                    )
                    self.last_query_telemetry = _finalize_telemetry_dict(telemetry)
                    return queries
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

        self.last_query_telemetry = _finalize_telemetry_dict(telemetry)
        return queries

    def _replacement_prompt(
        self,
        accepted: list[SearchQuery],
        min_queries: int,
        max_queries: Optional[int],
        required_signal_types: set[str],
        signal_minimums: dict[str, int],
        expected_companies: list[str],
        require_market_query: bool,
        require_priority_investor_signals: bool,
    ) -> str:
        accepted_payload = [
            {
                "query_text": q.query_text,
                "target_entity": q.target_entity,
                "signal_type": q.signal_type.value,
                "source_type": q.source_type,
            }
            for q in accepted
        ]
        covered_signals = {q.signal_type.value for q in accepted}
        signal_counts: dict[str, int] = defaultdict(int)
        for q in accepted:
            signal_counts[q.signal_type.value] += 1
        signal_deficits = {
            sig: max(0, minimum - signal_counts.get(sig, 0))
            for sig, minimum in signal_minimums.items()
            if signal_counts.get(sig, 0) < minimum
        }
        missing_companies = sorted(set(expected_companies) - {q.target_entity for q in accepted})
        investor_entities = {
            q.target_entity for q in accepted if q.signal_type == SignalType.investor_signal
        }
        missing_investor = sorted((_PRIORITY_INVESTOR_COMPANIES & set(expected_companies)) - investor_entities)
        needed_count = max(
            min_queries - len(accepted),
            len(required_signal_types - covered_signals),
            sum(signal_deficits.values()),
            len(missing_companies),
            len(missing_investor) if require_priority_investor_signals else 0,
            1,
        )
        return (
            "The previous JSON array contained malformed, duplicate, or unusable queries. "
            "Generate ONLY replacement queries for the invalid/missing slots. Do not repeat any accepted query.\n"
            f"Accepted query count: {len(accepted)}\n"
            f"Replacement target: {needed_count} to {min(max(needed_count + 5, needed_count), max_queries or 999)} queries\n"
            f"Missing signal types: {sorted(required_signal_types - covered_signals)}\n"
            f"Signal minimum deficits: {signal_deficits}\n"
            f"Missing company coverage: {missing_companies}\n"
            f"Missing investor_signal priority companies: {missing_investor if require_priority_investor_signals else []}\n"
            f"Market-level query required: {require_market_query and not any(q.target_entity == 'market' for q in accepted)}\n"
            "Accepted queries to avoid duplicating:\n"
            f"{json.dumps(accepted_payload, indent=2)}\n"
            "Return ONLY a JSON array of SearchQuery objects."
        )


def _has_time_anchor(query_text: str) -> bool:
    return bool(_TIME_ANCHOR_RE.search(query_text))


def _has_disallowed_url(query_text: str) -> bool:
    """Agent 1 should emit search queries, not raw/tracking URLs."""
    return bool(_RAW_URL_RE.search(query_text) or _TRACKING_URL_RE.search(query_text))


def _normalize_query_text(query_text: str) -> str:
    text = query_text.lower()
    text = re.sub(r"\bsite:\S+", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_near_duplicate(candidate: str, existing: list[str]) -> bool:
    candidate_tokens = set(candidate.split())
    for previous in existing:
        if candidate == previous:
            return True
        previous_tokens = set(previous.split())
        if candidate_tokens and previous_tokens:
            overlap = len(candidate_tokens & previous_tokens) / max(len(candidate_tokens | previous_tokens), 1)
            if overlap >= 0.82:
                return True
        if SequenceMatcher(None, candidate, previous).ratio() >= 0.88:
            return True
    return False


def _rejection_rate(telemetry: dict[str, Any]) -> float:
    total = int(telemetry.get("original_query_count") or 0)
    if total <= 0:
        return 1.0
    return int(telemetry.get("rejected_query_count") or 0) / total


def _merge_telemetry(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    merged["original_query_count"] = int(base.get("original_query_count") or 0)
    merged["accepted_query_count"] = int(base.get("accepted_query_count") or 0) + int(
        extra.get("accepted_query_count") or 0
    )
    merged["rejected_query_count"] = int(base.get("rejected_query_count") or 0) + int(
        extra.get("rejected_query_count") or 0
    )
    reasons: defaultdict[str, int] = defaultdict(int)
    for source in (base.get("rejected_reasons_by_type") or {}, extra.get("rejected_reasons_by_type") or {}):
        for key, count in dict(source).items():
            reasons[str(key)] += int(count)
    merged["rejected_reasons_by_type"] = reasons
    return merged


def _normalize_requested_signal_types(values: list[str] | tuple[str, ...] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        signal_type = str(value).strip()
        if signal_type in _VALID_SIGNAL_TYPES and signal_type not in seen:
            normalized.append(signal_type)
            seen.add(signal_type)
    return normalized


def _signal_minimums_for(required_signal_types: set[str]) -> dict[str, int]:
    return {
        signal_type: minimum
        for signal_type, minimum in _NORMAL_SIGNAL_QUERY_MINIMUMS.items()
        if signal_type in required_signal_types
    }


def _company_context_block_for(companies: list[str]) -> str:
    requested = set(companies)
    rows = []
    for company in COMPANIES:
        if company.name not in requested:
            continue
        rows.append(
            f"  {company.name} ({company.ticker}): primary_domain={company.domain}; "
            f"ir_domain={_urlparse(company.ir_url).netloc}; "
            f"careers_domain={_urlparse(company.careers_url).netloc}; "
            f"aliases={', '.join(company.known_aliases)}"
        )
    return "\n".join(rows) if rows else _COMPANY_CONTEXT_BLOCK


def _merge_seed_queries(
    seed_queries: list[SearchQuery],
    generated_queries: list[SearchQuery],
    telemetry: dict[str, Any],
    seed_telemetry: dict[str, object],
) -> list[SearchQuery]:
    if not seed_queries:
        return generated_queries

    merged: list[SearchQuery] = []
    seen: list[str] = []
    for query in seed_queries + generated_queries:
        normalized = _normalize_query_text(query.query_text)
        if _is_near_duplicate(normalized, seen):
            if query in generated_queries:
                telemetry["rejected_reasons_by_type"]["duplicate_or_near_duplicate_query_text"] += 1
                telemetry["rejected_query_count"] += 1
            continue
        seen.append(normalized)
        merged.append(query)

    telemetry["accepted_query_count"] = len(merged)
    telemetry["signal_coverage_after_planning"] = sorted({q.signal_type.value for q in merged})
    telemetry.update(seed_telemetry)
    return merged


def _trim_queries_to_limit(
    queries: list[SearchQuery],
    *,
    max_queries: int,
    expected_companies: list[str],
    required_signal_types: set[str],
    require_market_query: bool,
    require_priority_investor_signals: bool,
    signal_minimums: dict[str, int],
) -> list[SearchQuery]:
    """Keep the most important coverage-preserving queries when an LLM overshoots."""
    if len(queries) <= max_queries:
        return queries

    selected: list[SearchQuery] = []
    selected_ids: set[str] = set()

    def add(query: SearchQuery) -> None:
        if len(selected) >= max_queries or query.query_id in selected_ids:
            return
        selected.append(query)
        selected_ids.add(query.query_id)

    # Reserve one slot per required signal type FIRST so pricing playbook cannot crowd them out.
    for signal_type in required_signal_types:
        if any(q.signal_type.value == signal_type for q in selected):
            continue
        for query in queries:
            if query.signal_type.value == signal_type:
                add(query)
                break

    # Then fill remaining capacity with deterministic pricing playbook queries.
    for query in queries:
        if query.query_id.startswith("q_price_"):
            add(query)

    for company in expected_companies:
        if any(q.target_entity == company for q in selected):
            continue
        for query in queries:
            if query.target_entity == company:
                add(query)
                break

    if require_market_query and not any(q.target_entity == "market" for q in selected):
        for query in queries:
            if query.target_entity == "market":
                add(query)
                break

    if require_priority_investor_signals:
        expected_priority = _PRIORITY_INVESTOR_COMPANIES & set(expected_companies)
        for company in expected_priority:
            if any(q.target_entity == company and q.signal_type == SignalType.investor_signal for q in selected):
                continue
            for query in queries:
                if query.target_entity == company and query.signal_type == SignalType.investor_signal:
                    add(query)
                    break

    for signal_type, minimum in signal_minimums.items():
        while sum(1 for q in selected if q.signal_type.value == signal_type) < minimum:
            before = len(selected)
            for query in queries:
                if query.signal_type.value == signal_type and query.query_id not in selected_ids:
                    add(query)
                    break
            if len(selected) == before:
                break

    weighted_remaining = sorted(
        (query for query in queries if query.query_id not in selected_ids),
        key=lambda q: (q.priority, -SIGNAL_WEIGHTS.get(q.signal_type.value, 0.0)),
    )
    for query in weighted_remaining:
        add(query)
        if len(selected) >= max_queries:
            break

    return selected


def _finalize_telemetry_dict(telemetry: dict[str, Any]) -> dict[str, Any]:
    result = dict(telemetry)
    result["rejected_reasons_by_type"] = dict(telemetry.get("rejected_reasons_by_type") or {})
    result["signal_coverage_after_planning"] = list(telemetry.get("signal_coverage_after_planning") or [])
    return result


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
