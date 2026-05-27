# Agent 2 — Web Collection Workers
# Fetches raw web content with Bright Data and emits RawDocument objects for Agent 3.
from __future__ import annotations

import asyncio
import copy
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urlparse

import diskcache

from app.config.source_tiers import TIER_2_DOMAINS, assign_tier
from app.schemas.models import RawDocument, SearchQuery
from app.utils.brightdata_client import BrightDataClient, BrightDataError, DEFAULT_NUM_RESULTS
from app.utils.helpers import extract_domain, generate_uuid, now_iso
from app.utils.url_scorer import PRICING_HARDWARE_TERMS, PRICING_SIGNAL_TERMS, URLScorer

logger = logging.getLogger(__name__)

_HERE = Path(__file__).resolve()
_BACKEND_DIR = _HERE.parents[2]

MAX_CONCURRENT_BATCHES = int(os.getenv("BRIGHTDATA_MAX_CONCURRENCY", "10"))
QUERIES_PER_BATCH = int(os.getenv("BRIGHTDATA_QUERIES_PER_BATCH", "5"))
NUM_RESULTS_PER_QUERY = int(os.getenv("BRIGHTDATA_NUM_RESULTS", str(DEFAULT_NUM_RESULTS)))
CACHE_TTL_SECONDS = int(float(os.getenv("CACHE_TTL_HOURS", "4")) * 3600)
TIER2_METADATA_DOMAINS = set(TIER_2_DOMAINS)


def _resolve_cache_dir() -> Path:
    configured = os.getenv("BRIGHTDATA_CACHE_DIR")
    if not configured:
        return _BACKEND_DIR / "cache" / "brightdata"
    path = Path(configured)
    return path if path.is_absolute() else _BACKEND_DIR / path


MIN_CONTENT_CHARS = int(os.getenv("BRIGHTDATA_MIN_CONTENT_CHARS", "120"))
MAX_CONTENT_CHARS = int(os.getenv("BRIGHTDATA_MAX_CONTENT_CHARS", "200000"))

_PRICING_USE_UNLOCKER = os.getenv("PRICING_USE_UNLOCKER", "true").lower() == "true"
_PRICING_USE_BROWSER_FALLBACK = os.getenv("PRICING_USE_BROWSER_FALLBACK", "true").lower() == "true"
_PRICING_UNLOCKER_MIN_CONTENT_CHARS = int(os.getenv("PRICING_UNLOCKER_MIN_CONTENT_CHARS", "1500"))
_PRICING_MIN_PRICE_PATTERN_COUNT = int(os.getenv("PRICING_MIN_PRICE_PATTERN_COUNT", "1"))

# Keywords that identify EDGAR index pages — they list filing metadata, not filing content.
_EDGAR_INDEX_MARKERS = ("13F-HR", "13F-NT", "filed by", "Accession Number", "Filing Date", "Form Type")

# ── Pricing escalation helpers ────────────────────────────────────────────────

_PRICE_PATTERNS = re.compile(
    r"\$[\d,]+(?:\.\d+)?(?:/hr|/hour|/mo|/month)?\b"
    r"|\b[\d,]+\s*(?:USD|EUR|cents?)\b"
    r"|\bper.{0,20}hour\b"
    r"|\bper.{0,20}month\b",
    re.IGNORECASE,
)

_BROWSER_ALLOWED_PRICING_DOMAINS: frozenset[str] = frozenset({
    "coreweave.com",
    "runpod.io",
    "lambdalabs.com",
    "lambda.ai",
    "aws.amazon.com",
    "azure.microsoft.com",
    "cloud.google.com",
    "oracle.com",
    "supermicro.com",
    "thinkmate.com",
})

_NEVER_ESCALATE_DOMAINS: frozenset[str] = frozenset({
    "sec.gov",
    "ir.nvidia.com",
    "ir.amd.com",
    "ir.supermicro.com",
    "investor.nvidia.com",
})


def count_pricing_patterns(content: str) -> int:
    """Count distinct price-like patterns in content. Deterministic, no I/O."""
    return len(_PRICE_PATTERNS.findall(content))


def should_allow_browser_pricing_domain(url: str) -> bool:
    """True only for domains where browser rendering can improve pricing content."""
    domain = extract_domain(url)
    if any(domain == d or domain.endswith("." + d) for d in _NEVER_ESCALATE_DOMAINS):
        return False
    return any(domain == d or domain.endswith("." + d) for d in _BROWSER_ALLOWED_PRICING_DOMAINS)


def should_escalate_pricing_page(
    content: str,
    url: str,
    source_type: str,
    price_count: int,
) -> tuple[bool, str]:
    """
    Returns (should_escalate, reason). True when content quality is insufficient
    for a pricing page and browser rendering might help.
    Does NOT check domain allowlist — call should_allow_browser_pricing_domain separately.
    """
    if source_type != "pricing_pages":
        return False, "not_pricing_pages"
    if len(content) < MIN_CONTENT_CHARS:
        return True, "snippet_only"
    if len(content) < _PRICING_UNLOCKER_MIN_CONTENT_CHARS:
        return True, "content_too_short"
    if price_count < _PRICING_MIN_PRICE_PATTERN_COUNT:
        return True, "no_pricing_patterns"
    return False, "sufficient_content"


def choose_better_pricing_payload(
    normal_payload: dict[str, Any],
    browser_payload: dict[str, Any],
) -> dict[str, Any]:
    """Prefer browser payload only when it yields more price patterns or materially longer content."""
    normal_content = str(normal_payload.get("content") or "")
    browser_content = str(browser_payload.get("content") or "")
    normal_price_count = count_pricing_patterns(normal_content)
    browser_price_count = count_pricing_patterns(browser_content)
    if browser_price_count > normal_price_count:
        return browser_payload
    if len(browser_content) > len(normal_content) * 1.2 and len(browser_content) >= MIN_CONTENT_CHARS:
        return browser_payload
    return normal_payload


def is_useful_document(doc: RawDocument) -> bool:
    """
    Pre-extraction content quality filter.

    Returns False for documents that contain filing metadata lists rather than
    actionable content: EDGAR index pages produce zero-signal facts like
    "Institutional managers filed quarterly reports on Feb 11, 2026."
    """
    content = doc.content.strip()
    if doc.content_quality in {"metadata_only", "snippet_only"}:
        return len(content) >= 30
    if len(content) < 500:
        return False
    if "sec.gov" in doc.domain and any(marker in content for marker in _EDGAR_INDEX_MARKERS):
        return False
    return True

async def _maybe_browser_escalate_pricing(
    client: BrightDataClient,
    url: str,
    normal_payload: dict[str, Any],
    query_audit: dict[str, Any],
) -> dict[str, Any]:
    """
    Attempt Browser API fetch for a pricing page when normal fetch yielded thin content.
    Returns the better of the two payloads. Never raises — failures are recorded in query_audit.
    """
    normal_content = str(normal_payload.get("content") or "")
    normal_price_count = count_pricing_patterns(normal_content)
    quality = "snippet_only" if len(normal_content) < MIN_CONTENT_CHARS else "full_text"

    escalation_record: dict[str, Any] = {
        "url": url,
        "normal_scrape_content_length": len(normal_content),
        "normal_scrape_content_quality": quality,
        "normal_scrape_price_pattern_count": normal_price_count,
        "escalated_to_browser": False,
        "browser_content_length": 0,
        "browser_price_pattern_count": 0,
        "browser_error": None,
        "final_scrape_method": "normal",
        "pricing_escalation_reason": "",
        "pricing_escalation_improved_content": False,
    }

    should_esc, reason = should_escalate_pricing_page(
        normal_content, url, "pricing_pages", normal_price_count
    )
    escalation_record["pricing_escalation_reason"] = reason

    if not should_esc:
        query_audit.setdefault("pricing_escalations", []).append(escalation_record)
        return normal_payload

    escalation_record["escalated_to_browser"] = True
    try:
        browser_payload = await client.scrape_dynamic_page(url)
        browser_content = str(browser_payload.get("content") or "")
        browser_price_count = count_pricing_patterns(browser_content)
        escalation_record["browser_content_length"] = len(browser_content)
        escalation_record["browser_price_pattern_count"] = browser_price_count

        better = choose_better_pricing_payload(normal_payload, browser_payload)
        if better is browser_payload:
            escalation_record["final_scrape_method"] = "browser"
            escalation_record["pricing_escalation_improved_content"] = True
            logger.info(
                "Pricing browser escalation improved %s: %d→%d price patterns, %d→%d chars",
                url, normal_price_count, browser_price_count,
                len(normal_content), len(browser_content),
            )
            query_audit.setdefault("pricing_escalations", []).append(escalation_record)
            return browser_payload
        else:
            logger.info("Pricing browser escalation did NOT improve content for %s", url)
    except Exception as exc:
        escalation_record["browser_error"] = f"{type(exc).__name__}: {exc}"
        logger.warning("Pricing browser escalation failed for %s: %s", url, exc)

    query_audit.setdefault("pricing_escalations", []).append(escalation_record)
    return normal_payload


_cache: diskcache.Cache | None = None
_url_locks: dict[str, asyncio.Lock] = {}
_collection_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)
_LAST_COLLECTION_AUDIT: dict[str, Any] = {}
_LAST_FETCH_ERROR_SUMMARY: dict[str, Any] = {}


def get_last_collection_audit() -> dict[str, Any]:
    return copy.deepcopy(_LAST_COLLECTION_AUDIT)


def get_last_fetch_error_summary() -> dict[str, Any]:
    return copy.deepcopy(_LAST_FETCH_ERROR_SUMMARY)


async def collect_documents(queries: list[SearchQuery]) -> list[RawDocument]:
    """
    Collect documents for a batch of SearchQuery objects.

    This function is also used by tests and the LangGraph Agent 2 node. It
    performs internal async batching while Agent 2 is the active build target.
    """
    global _LAST_COLLECTION_AUDIT, _LAST_FETCH_ERROR_SUMMARY
    _LAST_COLLECTION_AUDIT = {
        "query_count": len(queries),
        "queries": [],
        "accepted_doc_count": 0,
        "failed_query_count": 0,
        "zero_doc_query_count": 0,
    }
    _LAST_FETCH_ERROR_SUMMARY = _new_fetch_summary()

    if not queries:
        return []

    scorer = URLScorer()  # one instance per pipeline run — error memory shared across all queries

    batches = [queries[i : i + QUERIES_PER_BATCH] for i in range(0, len(queries), QUERIES_PER_BATCH)]
    results: list[RawDocument] = []
    for batch in batches:
        batch_results = await asyncio.gather(
            *(
                collect_documents_for_query(
                    query,
                    scorer=scorer,
                    fetch_summary=_LAST_FETCH_ERROR_SUMMARY,
                )
                for query in batch
            )
        )
        for docs in batch_results:
            results.extend(docs)
    all_docs = _dedupe_documents(results)
    useful = [d for d in all_docs if is_useful_document(d)]
    if len(useful) < len(all_docs):
        logger.info(
            "Agent 2 filtered %d/%d documents as low-quality before extraction",
            len(all_docs) - len(useful), len(all_docs),
        )
    _LAST_COLLECTION_AUDIT["accepted_doc_count"] = len(useful)
    _LAST_COLLECTION_AUDIT["metadata_only_count"] = sum(1 for d in useful if d.content_quality == "metadata_only")
    _LAST_COLLECTION_AUDIT["full_text_count"] = sum(1 for d in useful if d.content_quality == "full_text")
    _LAST_COLLECTION_AUDIT["snippet_only_count"] = sum(1 for d in useful if d.content_quality == "snippet_only")
    _LAST_COLLECTION_AUDIT["extraction_allowed_doc_count"] = sum(
        1 for d in useful if getattr(d, "extraction_allowed", True)
    )
    _LAST_COLLECTION_AUDIT["failed_query_count"] = sum(
        1 for q in _LAST_COLLECTION_AUDIT["queries"] if q.get("accepted_doc_count", 0) == 0
    )
    _LAST_COLLECTION_AUDIT["zero_doc_query_count"] = _LAST_COLLECTION_AUDIT["failed_query_count"]
    _LAST_COLLECTION_AUDIT["low_quality_discard_count"] = len(all_docs) - len(useful)
    all_escalations = [
        e
        for q in _LAST_COLLECTION_AUDIT.get("queries", [])
        for e in q.get("pricing_escalations", [])
    ]
    _LAST_COLLECTION_AUDIT["pricing_browser_escalation_attempts"] = sum(
        1 for e in all_escalations if e.get("escalated_to_browser")
    )
    _LAST_COLLECTION_AUDIT["pricing_browser_escalation_successes"] = sum(
        1 for e in all_escalations if e.get("pricing_escalation_improved_content")
    )
    _LAST_COLLECTION_AUDIT["pricing_browser_escalation_failures"] = sum(
        1 for e in all_escalations if e.get("escalated_to_browser") and e.get("browser_error")
    )
    _LAST_COLLECTION_AUDIT["pricing_browser_improved_docs"] = (
        _LAST_COLLECTION_AUDIT["pricing_browser_escalation_successes"]
    )
    _LAST_FETCH_ERROR_SUMMARY = _finalize_fetch_summary(_LAST_FETCH_ERROR_SUMMARY)
    return useful


async def collect_documents_for_query(
    query: SearchQuery,
    scorer: URLScorer | None = None,
    fetch_summary: dict[str, Any] | None = None,
) -> list[RawDocument]:
    async with _collection_semaphore:
        global _LAST_COLLECTION_AUDIT, _LAST_FETCH_ERROR_SUMMARY
        if fetch_summary is None:
            _LAST_COLLECTION_AUDIT = {
                "query_count": 1,
                "queries": [],
                "accepted_doc_count": 0,
                "failed_query_count": 0,
                "zero_doc_query_count": 0,
            }
            _LAST_FETCH_ERROR_SUMMARY = _new_fetch_summary()
            fetch_summary = _LAST_FETCH_ERROR_SUMMARY
        query_audit = _new_query_audit(query)
        try:
            client = BrightDataClient.from_env()
        except ValueError as exc:
            logger.error("Agent 2 Bright Data configuration error: %s", exc)
            query_audit["fetch_errors"].append({"url": "", "status": None, "error": str(exc)})
            _record_query_audit(query_audit)
            return []

        candidates = await _discover_candidate_urls(client, query)

        if scorer is not None and candidates:
            pre_filter = len(candidates)
            kept: list[dict[str, Any]] = []
            for candidate in candidates:
                reason = scorer.rejection_reason(candidate, query)
                if reason:
                    query_audit["rejected_urls"].append(
                        {"url": candidate.get("url") or candidate.get("link") or "", "reason": reason}
                    )
                    continue
                query_audit["accepted_urls"].append(
                    {
                        "url": candidate.get("url") or candidate.get("link") or "",
                        "reason": scorer.acceptance_reason(candidate, query),
                    }
                )
                kept.append(candidate)
            candidates = kept
            skipped = pre_filter - len(candidates)
            if skipped > 0:
                logger.info(
                    "Agent 2 skipped %d/%d SERP results for query %s — below relevance threshold",
                    skipped, pre_filter, query.query_id,
                )

        docs: list[RawDocument] = []

        for candidate in candidates:
            url = _normalize_url(candidate.get("url", ""))
            if not url:
                query_audit["rejected_urls"].append({"url": candidate.get("url", ""), "reason": "invalid_url"})
                continue
            if _prefer_metadata_only(url, query):
                metadata_doc = _metadata_only_document(candidate, query, url)
                if metadata_doc is not None:
                    query_audit["accepted_urls"].append({"url": url, "reason": "pricing_metadata_only_accepted" if query.source_type == "pricing_pages" else "metadata_only_accepted"})
                    docs.append(metadata_doc)
                    continue
            try:
                payload = await _fetch_page_with_cache(client, url, query.source_type, fetch_summary, query_audit)
            except BrightDataError as exc:
                if scorer is not None:
                    scorer.record_http_result(url, exc.status_code or 0)
                _record_fetch_error(fetch_summary, url, exc.status_code, type(exc).__name__, str(exc))
                query_audit["fetch_errors"].append(
                    {"url": url, "status": exc.status_code, "error": f"{type(exc).__name__}: {exc}"}
                )
                metadata_doc = _metadata_only_document(candidate, query, url)
                if metadata_doc is not None:
                    docs.append(metadata_doc)
                    logger.info("Agent 2 kept metadata-only Tier 2 result for blocked URL %s", url)
                else:
                    logger.warning("Agent 2 skipped %s for query %s: %s", url, query.query_id, exc)
                continue
            except Exception as exc:
                _record_fetch_error(fetch_summary, url, None, type(exc).__name__, str(exc))
                query_audit["fetch_errors"].append(
                    {"url": url, "status": None, "error": f"{type(exc).__name__}: {exc}"}
                )
                logger.warning("Agent 2 skipped %s for query %s: %s: %s", url, query.query_id, type(exc).__name__, exc)
                continue

            content = str(payload.get("content") or "").strip()
            content_quality = "full_text"

            # Browser escalation for pricing pages (only for allowed domains)
            if (
                query.source_type == "pricing_pages"
                and _PRICING_USE_BROWSER_FALLBACK
                and client.has_browser_zone
                and should_allow_browser_pricing_domain(url)
            ):
                payload = await _maybe_browser_escalate_pricing(client, url, payload, query_audit)
                content = str(payload.get("content") or "").strip()
                content_quality = "full_text"

            if len(content) < MIN_CONTENT_CHARS:
                content = str(candidate.get("snippet") or content).strip()
                content_quality = "snippet_only"
            if len(content) < MIN_CONTENT_CHARS:
                logger.debug("Agent 2 skipped low-content URL %s (%d chars)", url, len(content))
                query_audit["rejected_urls"].append({"url": url, "reason": "low_content"})
                continue

            final_url = _normalize_url(str(payload.get("url") or url))
            docs.append(
                RawDocument(
                    doc_id=f"doc_{generate_uuid()[:12]}",
                    url=final_url,
                    domain=extract_domain(final_url),
                    title=(str(payload.get("title") or candidate.get("title") or "")[:300]),
                    content=content[:MAX_CONTENT_CHARS],
                    published_date=_first_non_empty(payload.get("published_date"), candidate.get("published_date")),
                    fetched_at=now_iso(),
                    source_tier=assign_tier(final_url),
                    content_quality=content_quality,
                    extraction_allowed=content_quality != "metadata_only",
                    collection_query=query.query_text,
                    signal_type_hint=query.signal_type,
                )
            )

        if not docs:
            fallback_docs = await _run_per_query_fallbacks(client, query, scorer, fetch_summary, query_audit)
            if fallback_docs:
                docs.extend(fallback_docs)
                query_audit["fallback_produced_documents"] = True

        query_audit["accepted_doc_count"] = len(docs)
        _record_query_audit(query_audit)
        if _LAST_COLLECTION_AUDIT.get("query_count") == 1:
            _LAST_COLLECTION_AUDIT["accepted_doc_count"] = len(docs)
            _LAST_COLLECTION_AUDIT["failed_query_count"] = 1 if len(docs) == 0 else 0
            _LAST_COLLECTION_AUDIT["zero_doc_query_count"] = _LAST_COLLECTION_AUDIT["failed_query_count"]
            _LAST_FETCH_ERROR_SUMMARY = _finalize_fetch_summary(fetch_summary)
        logger.info("Agent 2 collected %d documents for query %s", len(docs), query.query_id)
        return _dedupe_documents(docs)


async def _run_per_query_fallbacks(
    client: BrightDataClient,
    query: SearchQuery,
    scorer: URLScorer | None,
    fetch_summary: dict[str, Any],
    query_audit: dict[str, Any],
) -> list[RawDocument]:
    """Run one bounded fallback pass when the primary query yields no documents."""
    fallback_queries = _per_query_fallbacks(query)
    if not fallback_queries:
        return []
    query_audit["fallback_used"] = True
    query_audit["fallback_policy"] = (
        "pricing_relaxed_site_constraint"
        if query.signal_type.value == "pricing_pressure" or query.source_type == "pricing_pages"
        else "standard"
    )
    docs: list[RawDocument] = []

    for fallback_query in fallback_queries:
        scoring_query = query.model_copy(update={"query_text": fallback_query})
        try:
            candidates = await client.serp_search(fallback_query, num_results=NUM_RESULTS_PER_QUERY)
        except Exception as exc:
            query_audit["fetch_errors"].append(
                {"url": f"SERP:{fallback_query}", "status": None, "error": f"{type(exc).__name__}: {exc}"}
            )
            continue

        for candidate in candidates:
            if scorer is not None:
                reason = scorer.rejection_reason(candidate, scoring_query)
                if reason:
                    query_audit["rejected_urls"].append(
                        {"url": candidate.get("url") or candidate.get("link") or "", "reason": f"fallback:{reason}"}
                    )
                    continue
                query_audit["accepted_urls"].append(
                    {
                        "url": candidate.get("url") or candidate.get("link") or "",
                        "reason": f"fallback:{scorer.acceptance_reason(candidate, scoring_query)}",
                    }
                )
            url = _normalize_url(candidate.get("url", ""))
            if not url:
                continue
            if _prefer_metadata_only(url, query):
                metadata_doc = _metadata_only_document(candidate, query, url)
                if metadata_doc is not None:
                    query_audit["accepted_urls"].append({"url": url, "reason": "fallback:pricing_metadata_only_accepted" if query.source_type == "pricing_pages" else "fallback:metadata_only_accepted"})
                    docs.append(metadata_doc)
                    continue
            try:
                payload = await _fetch_page_with_cache(client, url, query.source_type, fetch_summary, query_audit)
            except BrightDataError as exc:
                if scorer is not None:
                    scorer.record_http_result(url, exc.status_code or 0)
                _record_fetch_error(fetch_summary, url, exc.status_code, type(exc).__name__, str(exc))
                query_audit["fetch_errors"].append(
                    {"url": url, "status": exc.status_code, "error": f"{type(exc).__name__}: {exc}"}
                )
                metadata_doc = _metadata_only_document(candidate, query, url)
                if metadata_doc is not None:
                    docs.append(metadata_doc)
                continue
            except Exception as exc:
                _record_fetch_error(fetch_summary, url, None, type(exc).__name__, str(exc))
                query_audit["fetch_errors"].append(
                    {"url": url, "status": None, "error": f"{type(exc).__name__}: {exc}"}
                )
                continue

            content = str(payload.get("content") or "").strip()
            content_quality = "full_text"
            if len(content) < MIN_CONTENT_CHARS:
                content = str(candidate.get("snippet") or content).strip()
                content_quality = "snippet_only"
            if len(content) < MIN_CONTENT_CHARS:
                query_audit["rejected_urls"].append({"url": url, "reason": "fallback:low_content"})
                continue

            final_url = _normalize_url(str(payload.get("url") or url))
            docs.append(
                RawDocument(
                    doc_id=f"doc_{generate_uuid()[:12]}",
                    url=final_url,
                    domain=extract_domain(final_url),
                    title=(str(payload.get("title") or candidate.get("title") or "")[:300]),
                    content=content[:MAX_CONTENT_CHARS],
                    published_date=_first_non_empty(payload.get("published_date"), candidate.get("published_date")),
                    fetched_at=now_iso(),
                    source_tier=assign_tier(final_url),
                    content_quality=content_quality,
                    extraction_allowed=content_quality != "metadata_only",
                    collection_query=fallback_query,
                    signal_type_hint=query.signal_type,
                )
            )
        if docs:
            break

    return _dedupe_documents(docs)


async def _discover_candidate_urls(client: BrightDataClient, query: SearchQuery) -> list[dict[str, Any]]:
    direct_url = _extract_direct_url(query.query_text)
    if direct_url:
        if URLScorer().rejection_reason({"url": direct_url}, query):
            return []
        return [{"url": direct_url, "title": "", "snippet": "", "published_date": None}]

    for search_query in _query_fallbacks(query.query_text):
        try:
            results = await client.serp_search(search_query, num_results=NUM_RESULTS_PER_QUERY)
        except Exception as exc:
            logger.warning("Agent 2 SERP discovery failed for query %s: %s", query.query_id, exc)
            continue
        if results:
            if search_query != query.query_text:
                logger.info("Agent 2 SERP fallback succeeded for query %s", query.query_id)
            return results
    return []


async def _fetch_page_with_cache(
    client: BrightDataClient,
    url: str,
    source_type: str,
    fetch_summary: dict[str, Any] | None = None,
    query_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    key = _cache_key(url, source_type)
    lock = _url_locks.setdefault(key, asyncio.Lock())
    async with lock:
        cache = _get_cache()
        cached = cache.get(key)
        if isinstance(cached, dict):
            return cached

        if fetch_summary is not None:
            fetch_summary["total_fetch_attempts"] += 1
        if query_audit is not None:
            query_audit["attempted_urls"].append(url)
        payload = await _scrape_by_source_type(client, url, source_type)
        if fetch_summary is not None:
            fetch_summary["successful_fetches"] += 1
        cache.set(key, payload, expire=CACHE_TTL_SECONDS)
        return payload


async def _scrape_by_source_type(client: BrightDataClient, url: str, source_type: str) -> dict[str, Any]:
    if source_type == "job_pages":
        return await client.scrape_job_page(url)
    if source_type == "dynamic_pages":
        return await client.scrape_dynamic_page(url)
    if source_type == "protected":
        return await client.scrape_protected_page(url)
    if source_type == "pricing_pages" and _PRICING_USE_UNLOCKER:
        return await client.scrape_protected_page(url)
    return await client.scrape_page(url)


def _cache_key(url: str, source_type: str = "") -> str:
    date_key = datetime.now(timezone.utc).date().isoformat()
    parts = [_normalize_url(url), source_type, date_key] if source_type else [_normalize_url(url), date_key]
    return ":".join(parts)


def _get_cache() -> diskcache.Cache:
    global _cache
    if _cache is None:
        _cache = diskcache.Cache(str(_resolve_cache_dir()))
    return _cache


def _extract_direct_url(query_text: str) -> str | None:
    words = query_text.split()
    for word in words:
        cleaned = word.strip("\"'()[]{}<>,")
        if cleaned.startswith(("http://", "https://")):
            return _normalize_url(cleaned)
    return None


def _query_fallbacks(query_text: str) -> list[str]:
    fallbacks = [query_text]
    without_site = re.sub(r"\s*site:\S+", "", query_text).strip()
    if without_site and without_site != query_text:
        fallbacks.append(without_site)
    return fallbacks


def _per_query_fallbacks(query: SearchQuery) -> list[str]:
    company = query.target_entity if query.target_entity != "market" else "AI hardware semiconductor market"
    time_anchor = _extract_time_anchor(query.query_text) or "last 7 days"
    signal_phrase = query.signal_type.value.replace("_", " ")
    if query.signal_type.value == "pricing_pressure" or query.source_type == "pricing_pages":
        if company == "Nvidia":
            return [
                f"Nvidia H100 H200 B200 GPU cloud pricing availability {time_anchor}",
                f"Nvidia GPU instance discount availability AWS Azure CoreWeave Lambda Labs {time_anchor}",
            ]
        if company == "AMD":
            return [
                f"AMD Instinct MI300X MI325X cloud GPU pricing availability {time_anchor}",
                f"AMD MI300X MI325X AI server pricing availability Dell Supermicro Oracle Azure {time_anchor}",
            ]
        if company == "Supermicro":
            return [
                f"Supermicro GPU server AI server pricing availability H100 H200 B200 MI300X {time_anchor}",
                f"Supermicro Blackwell AMD Instinct GPU server lead time delivery availability {time_anchor}",
            ]
        return [
            f"cloud GPU pricing availability H100 H200 B200 MI300X {time_anchor}",
            f"AI server lead time GPU availability distributor pricing {time_anchor}",
        ]
    ir_fallback = f'{company} investor relations press release {signal_phrase} {time_anchor}'
    news_fallback = f'{company} {signal_phrase} AI hardware semiconductor Reuters Bloomberg {time_anchor}'
    if query.source_type == "job_pages":
        ir_fallback = f'{company} careers AI hardware {signal_phrase} {time_anchor}'
    if query.source_type == "pricing_pages":
        ir_fallback = f'{company} AI server GPU pricing availability distributor {time_anchor}'
    return [ir_fallback, news_fallback]


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    clean_url, _fragment = urldefrag(url.strip())
    parsed = urlparse(clean_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return clean_url


def _extract_time_anchor(query_text: str) -> str | None:
    match = re.search(r"(\b(?:2025|2026)\b|\blast\s+7\s+days\b|\bQ[12]\s+202[56]\b)", query_text, re.IGNORECASE)
    return match.group(1) if match else None


def _metadata_only_document(candidate: dict[str, Any], query: SearchQuery, url: str) -> RawDocument | None:
    domain = extract_domain(url)
    allowed_metadata_domain = any(domain == d or domain.endswith("." + d) for d in TIER2_METADATA_DOMAINS)
    allowed_linkedin_job = query.source_type == "job_pages" and domain == "linkedin.com" and "/jobs/" in urlparse(url).path
    title = str(candidate.get("title") or "").strip()
    snippet = str(candidate.get("snippet") or candidate.get("description") or "").strip()
    haystack = f"{url} {title} {snippet}".lower()
    allowed_pricing_metadata = (
        (query.signal_type.value == "pricing_pressure" or query.source_type == "pricing_pages")
        and any(term in haystack for term in PRICING_HARDWARE_TERMS)
        and any(term in haystack for term in PRICING_SIGNAL_TERMS)
    )
    if not allowed_metadata_domain and not allowed_linkedin_job and not allowed_pricing_metadata:
        return None
    content = "\n".join(part for part in [title, snippet] if part).strip()
    if len(content) < 30:
        return None
    return RawDocument(
        doc_id=f"doc_{generate_uuid()[:12]}",
        url=url,
        domain=domain,
        title=title[:300],
        content=content[:MAX_CONTENT_CHARS],
        published_date=_first_non_empty(candidate.get("published_date"), candidate.get("date")),
        fetched_at=now_iso(),
        source_tier=assign_tier(url),
        content_quality="metadata_only",
        extraction_allowed=False,
        collection_query=query.query_text,
        signal_type_hint=query.signal_type,
    )


def _prefer_metadata_only(url: str, query: SearchQuery) -> bool:
    domain = extract_domain(url)
    path = urlparse(url).path.lower()
    return query.source_type == "job_pages" and domain == "linkedin.com" and "/jobs/" in path


def _new_query_audit(query: SearchQuery) -> dict[str, Any]:
    return {
        "query_id": query.query_id,
        "query_text": query.query_text,
        "target_entity": query.target_entity,
        "signal_type": query.signal_type.value,
        "source_type": query.source_type,
        "attempted_urls": [],
        "accepted_urls": [],
        "rejected_urls": [],
        "fetch_errors": [],
        "accepted_doc_count": 0,
        "fallback_used": False,
        "fallback_policy": None,
        "fallback_produced_documents": False,
    }


def _record_query_audit(query_audit: dict[str, Any]) -> None:
    _LAST_COLLECTION_AUDIT.setdefault("queries", []).append(query_audit)


def _new_fetch_summary() -> dict[str, Any]:
    return {
        "total_fetch_attempts": 0,
        "successful_fetches": 0,
        "failed_fetches": 0,
        "permanent_failures": 0,
        "failure_count_by_domain": defaultdict(int),
        "failure_count_by_reason": defaultdict(int),
    }


def _record_fetch_error(
    summary: dict[str, Any],
    url: str,
    status_code: int | None,
    exc_class: str,
    message: str,
) -> None:
    summary["failed_fetches"] += 1
    if status_code in (400, 401, 403, 404, 410):
        summary["permanent_failures"] += 1
    domain = extract_domain(url) or "unknown"
    reason = f"http_{status_code}" if status_code else exc_class
    if message and "timeout" in message.lower():
        reason = "timeout"
    summary["failure_count_by_domain"][domain] += 1
    summary["failure_count_by_reason"][reason] += 1


def _finalize_fetch_summary(summary: dict[str, Any]) -> dict[str, Any]:
    result = dict(summary)
    result["failure_count_by_domain"] = dict(Counter(summary.get("failure_count_by_domain", {})).most_common())
    result["failure_count_by_reason"] = dict(Counter(summary.get("failure_count_by_reason", {})).most_common())
    return result


def _dedupe_documents(documents: list[RawDocument]) -> list[RawDocument]:
    seen: set[str] = set()
    unique: list[RawDocument] = []
    for doc in documents:
        url = _normalize_url(doc.url)
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(doc)
    return unique


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        if value is not None and str(value).strip():
            return str(value)
    return None
