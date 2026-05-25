# Bright Data HTTP wrapper — SERP discovery plus page scraping with retry.
from __future__ import annotations

import asyncio
import html
import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv

from app.utils.helpers import clean_html, extract_domain

logger = logging.getLogger(__name__)

_BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_BACKEND_ENV)

DEFAULT_BRIGHTDATA_API_URL = "https://api.brightdata.com/request"
DEFAULT_NUM_RESULTS = 5
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_RETRY_DELAYS = (1.0, 2.0, 4.0)


_NON_RETRYABLE_CODES: frozenset[int] = frozenset({400, 401, 403, 404, 410})


class BrightDataError(RuntimeError):
    """Raised when Bright Data cannot return a usable response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class BrightDataClient:
    def __init__(
        self,
        api_key: str,
        serp_zone: str,
        scraper_zone: str,
        browser_zone: str | None = None,
        unlocker_zone: str | None = None,
        api_url: str = DEFAULT_BRIGHTDATA_API_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
    ) -> None:
        if not api_key:
            raise ValueError("BRIGHTDATA_API_KEY is required")
        if not serp_zone:
            raise ValueError("BRIGHTDATA_SERP_ZONE is required")
        if not scraper_zone:
            raise ValueError("BRIGHTDATA_SCRAPER_ZONE is required")

        self.api_key = api_key
        self.serp_zone = serp_zone
        self.scraper_zone = scraper_zone
        self.browser_zone = browser_zone or scraper_zone
        self.unlocker_zone = unlocker_zone or scraper_zone
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.retry_delays = retry_delays

    @classmethod
    def from_env(cls) -> "BrightDataClient":
        return cls(
            api_key=os.getenv("BRIGHTDATA_API_KEY", ""),
            serp_zone=os.getenv("BRIGHTDATA_SERP_ZONE", ""),
            scraper_zone=os.getenv("BRIGHTDATA_SCRAPER_ZONE", ""),
            browser_zone=os.getenv("BRIGHTDATA_BROWSER_ZONE") or None,
            unlocker_zone=os.getenv("BRIGHTDATA_UNLOCKER_ZONE") or None,
            api_url=os.getenv("BRIGHTDATA_API_URL", DEFAULT_BRIGHTDATA_API_URL),
            timeout_seconds=float(os.getenv("BRIGHTDATA_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
        )

    async def serp_search(self, query: str, num_results: int = DEFAULT_NUM_RESULTS) -> list[dict[str, Any]]:
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"
        payload = await self._request(self.serp_zone, search_url, response_format="json")
        results = self._normalize_serp_results(payload)
        if results:
            return results[:num_results]

        # Some Bright Data SERP zones return raw HTML even when JSON is requested.
        if isinstance(payload, str):
            return self._extract_results_from_html(payload, limit=num_results)
        return []

    async def scrape_page(self, url: str) -> dict[str, Any]:
        payload = await self._request(self.scraper_zone, url, response_format="raw")
        return self._normalize_page_payload(url, payload)

    async def scrape_job_page(self, url: str) -> dict[str, Any]:
        payload = await self._request(self.scraper_zone, url, response_format="raw")
        return self._normalize_page_payload(url, payload)

    async def scrape_dynamic_page(self, url: str) -> dict[str, Any]:
        payload = await self._request(self.browser_zone, url, response_format="raw", render_js=True)
        return self._normalize_page_payload(url, payload)

    async def scrape_protected_page(self, url: str) -> dict[str, Any]:
        payload = await self._request(self.unlocker_zone, url, response_format="raw")
        return self._normalize_page_payload(url, payload)

    async def _request(
        self,
        zone: str,
        url: str,
        response_format: str,
        render_js: bool = False,
    ) -> Any:
        request_payload: dict[str, Any] = {
            "zone": zone,
            "url": url,
            "format": response_format,
        }
        if render_js:
            request_payload["render"] = True

        headers = {"Authorization": f"Bearer {self.api_key}"}
        last_error: Exception | None = None
        last_status_code: int | None = None
        last_response_snippet: str = ""
        for attempt in range(len(self.retry_delays) + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(self.api_url, json=request_payload, headers=headers)
                    response.raise_for_status()
                    return self._decode_response(response)
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                exc_class = type(exc).__name__
                exc_message = str(exc) or "(empty exception message)"
                if isinstance(exc, httpx.HTTPStatusError):
                    last_status_code = exc.response.status_code
                    last_response_snippet = exc.response.text[:500]
                    if last_status_code in _NON_RETRYABLE_CODES:
                        logger.warning(
                            "Bright Data permanent error url=%s zone=%s attempt=%d/%d class=%s message=%s status=%s response_snippet=%r — not retrying",
                            url,
                            zone,
                            attempt + 1,
                            len(self.retry_delays) + 1,
                            exc_class,
                            exc_message,
                            last_status_code,
                            last_response_snippet,
                        )
                        break
                if attempt >= len(self.retry_delays):
                    break
                delay = self.retry_delays[attempt]
                logger.warning(
                    "Bright Data request failed url=%s zone=%s attempt=%d/%d class=%s message=%s status=%s response_snippet=%r; retrying in %.1fs",
                    url,
                    zone,
                    attempt + 1,
                    len(self.retry_delays) + 1,
                    exc_class,
                    exc_message,
                    last_status_code,
                    last_response_snippet,
                    delay,
                )
                await asyncio.sleep(delay)

        raise BrightDataError(
            (
                f"Bright Data request failed url={url} zone={zone} "
                f"class={type(last_error).__name__ if last_error else 'UnknownError'} "
                f"message={str(last_error) or '(empty exception message)'} "
                f"status={last_status_code} response_snippet={last_response_snippet[:200]!r}"
            ),
            status_code=last_status_code,
        )

    @staticmethod
    def _decode_response(response: httpx.Response) -> Any:
        import json as _json
        content_type = response.headers.get("content-type", "").lower()
        if "json" in content_type:
            data = response.json()
        else:
            try:
                data = response.json()
            except ValueError:
                return response.text

        # Unwrap BrightData envelope: {"status_code": N, "headers": {...}, "body": "..."}
        if isinstance(data, dict) and "body" in data and "status_code" in data:
            body = data["body"]
            if isinstance(body, str):
                try:
                    return _json.loads(body)
                except (ValueError, _json.JSONDecodeError):
                    return body
            return body
        return data

    @staticmethod
    def _normalize_serp_results(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            candidates = payload
        elif isinstance(payload, dict):
            candidates = (
                payload.get("organic")
                or payload.get("organic_results")
                or payload.get("results")
                or payload.get("items")
                or []
            )
        else:
            return []

        if isinstance(candidates, dict):
            candidates = list(candidates.values())
        if not isinstance(candidates, list):
            return []

        results: list[dict[str, Any]] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("link") or item.get("href")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                continue
            title = item.get("title") or item.get("name") or ""
            snippet = item.get("description") or item.get("snippet") or item.get("content") or ""
            published_date = item.get("date") or item.get("published_date")
            results.append(
                {
                    "url": url,
                    "title": str(title),
                    "snippet": str(snippet),
                    "published_date": str(published_date) if published_date else None,
                }
            )
        return results

    @staticmethod
    def _extract_results_from_html(html_text: str, limit: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for match in re.finditer(r'href="(https?://[^"#]+)"', html_text):
            url = html.unescape(match.group(1))
            if "google." in extract_domain(url) or url in seen:
                continue
            seen.add(url)
            results.append({"url": url, "title": "", "snippet": "", "published_date": None})
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _normalize_page_payload(url: str, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            raw_content = (
                payload.get("content")
                or payload.get("text")
                or payload.get("html")
                or payload.get("body")
                or ""
            )
            title = payload.get("title") or BrightDataClient._extract_title(str(raw_content))
            published_date = payload.get("published_date") or payload.get("date")
            final_url = payload.get("url") or url
            return {
                "url": str(final_url),
                "title": str(title or ""),
                "content": clean_html(str(raw_content)),
                "published_date": str(published_date) if published_date else None,
            }

        raw_text = str(payload or "")
        return {
            "url": url,
            "title": BrightDataClient._extract_title(raw_text),
            "content": clean_html(raw_text),
            "published_date": BrightDataClient._extract_published_date(raw_text),
        }

    @staticmethod
    def _extract_title(raw_html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return html.unescape(clean_html(match.group(1)))[:300]

    @staticmethod
    def _extract_published_date(raw_html: str) -> str | None:
        patterns = [
            r'property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)',
            r'name=["\']date["\'][^>]+content=["\']([^"\']+)',
            r'name=["\']pubdate["\'][^>]+content=["\']([^"\']+)',
            r'datetime=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_html, flags=re.IGNORECASE)
            if match:
                return html.unescape(match.group(1))
        return None
