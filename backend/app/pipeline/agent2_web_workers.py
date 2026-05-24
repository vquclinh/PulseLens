# Agent 2 — Web Collection Workers
# Fetches raw web content with Bright Data and emits RawDocument objects for Agent 3.
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urlparse

import diskcache

from app.config.source_tiers import assign_tier
from app.schemas.models import RawDocument, SearchQuery
from app.utils.brightdata_client import BrightDataClient, BrightDataError, DEFAULT_NUM_RESULTS
from app.utils.helpers import extract_domain, generate_uuid, now_iso

logger = logging.getLogger(__name__)

_HERE = Path(__file__).resolve()
_BACKEND_DIR = _HERE.parents[2]

MAX_CONCURRENT_BATCHES = int(os.getenv("BRIGHTDATA_MAX_CONCURRENCY", "10"))
QUERIES_PER_BATCH = int(os.getenv("BRIGHTDATA_QUERIES_PER_BATCH", "5"))
NUM_RESULTS_PER_QUERY = int(os.getenv("BRIGHTDATA_NUM_RESULTS", str(DEFAULT_NUM_RESULTS)))
CACHE_TTL_SECONDS = int(float(os.getenv("CACHE_TTL_HOURS", "4")) * 3600)


def _resolve_cache_dir() -> Path:
    configured = os.getenv("BRIGHTDATA_CACHE_DIR")
    if not configured:
        return _BACKEND_DIR / "cache" / "brightdata"
    path = Path(configured)
    return path if path.is_absolute() else _BACKEND_DIR / path


MIN_CONTENT_CHARS = int(os.getenv("BRIGHTDATA_MIN_CONTENT_CHARS", "120"))
MAX_CONTENT_CHARS = int(os.getenv("BRIGHTDATA_MAX_CONTENT_CHARS", "200000"))

_cache: diskcache.Cache | None = None
_url_locks: dict[str, asyncio.Lock] = {}
_collection_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)


async def collect_documents(queries: list[SearchQuery]) -> list[RawDocument]:
    """
    Collect documents for a batch of SearchQuery objects.

    This function is also used by tests and fallback non-Send execution. In the
    LangGraph pipeline, graph.py fans out each query to collect_documents_for_query().
    """
    if not queries:
        return []

    batches = [queries[i : i + QUERIES_PER_BATCH] for i in range(0, len(queries), QUERIES_PER_BATCH)]
    results: list[RawDocument] = []
    for batch in batches:
        batch_results = await asyncio.gather(*(collect_documents_for_query(query) for query in batch))
        for docs in batch_results:
            results.extend(docs)
    return _dedupe_documents(results)


async def collect_documents_for_query(query: SearchQuery) -> list[RawDocument]:
    async with _collection_semaphore:
        try:
            client = BrightDataClient.from_env()
        except ValueError as exc:
            logger.error("Agent 2 Bright Data configuration error: %s", exc)
            return []

        candidates = await _discover_candidate_urls(client, query)
        docs: list[RawDocument] = []

        for candidate in candidates:
            url = _normalize_url(candidate.get("url", ""))
            if not url:
                continue
            try:
                payload = await _fetch_page_with_cache(client, url, query.source_type)
            except Exception as exc:
                logger.warning("Agent 2 skipped %s for query %s: %s", url, query.query_id, exc)
                continue

            content = str(payload.get("content") or "").strip()
            if len(content) < MIN_CONTENT_CHARS:
                content = str(candidate.get("snippet") or content).strip()
            if len(content) < MIN_CONTENT_CHARS:
                logger.debug("Agent 2 skipped low-content URL %s (%d chars)", url, len(content))
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
                    collection_query=query.query_text,
                    signal_type_hint=query.signal_type,
                )
            )

        logger.info("Agent 2 collected %d documents for query %s", len(docs), query.query_id)
        return _dedupe_documents(docs)


async def _discover_candidate_urls(client: BrightDataClient, query: SearchQuery) -> list[dict[str, Any]]:
    direct_url = _extract_direct_url(query.query_text)
    if direct_url:
        return [{"url": direct_url, "title": "", "snippet": "", "published_date": None}]

    try:
        return await client.serp_search(query.query_text, num_results=NUM_RESULTS_PER_QUERY)
    except Exception as exc:
        logger.warning("Agent 2 SERP discovery failed for query %s: %s", query.query_id, exc)
        return []


async def _fetch_page_with_cache(client: BrightDataClient, url: str, source_type: str) -> dict[str, Any]:
    key = _cache_key(url)
    lock = _url_locks.setdefault(key, asyncio.Lock())
    async with lock:
        cache = _get_cache()
        cached = cache.get(key)
        if isinstance(cached, dict):
            return cached

        payload = await _scrape_by_source_type(client, url, source_type)
        cache.set(key, payload, expire=CACHE_TTL_SECONDS)
        return payload


async def _scrape_by_source_type(client: BrightDataClient, url: str, source_type: str) -> dict[str, Any]:
    if source_type == "job_pages":
        return await client.scrape_job_page(url)
    if source_type == "dynamic_pages":
        return await client.scrape_dynamic_page(url)
    if source_type == "protected":
        return await client.scrape_protected_page(url)
    return await client.scrape_page(url)


def _cache_key(url: str) -> str:
    date_key = datetime.now(timezone.utc).date().isoformat()
    return f"{_normalize_url(url)}:{date_key}"


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


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    clean_url, _fragment = urldefrag(url.strip())
    parsed = urlparse(clean_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return clean_url


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
