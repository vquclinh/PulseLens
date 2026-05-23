# Anthropic claude-sonnet-4-20250514 wrapper — sync JSON/text calls with retry and structured logging
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
_RETRY_DELAYS = [1, 2, 4]   # exponential backoff seconds between attempts


def _extract_json(text: str) -> str:
    """Strip markdown code fences if the model wrapped its JSON output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.rstrip())
    return text.strip()


class LLMClient:
    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def call_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ) -> Any:
        """
        Call Claude and return parsed JSON. Retries on API error or JSON parse failure.
        Raises RuntimeError after all attempts are exhausted.
        """
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                raw = self._call(system, user, max_tokens)
                text = _extract_json(raw)
                result = json.loads(text)
                logger.debug("call_json OK (attempt %d, %d chars)", attempt + 1, len(text))
                return result
            except json.JSONDecodeError as exc:
                last_error = exc
                logger.warning(
                    "JSON parse failure attempt %d/%d: %s — preview: %.120s",
                    attempt + 1, max_retries, exc, raw[:200] if "raw" in dir() else "",
                )
            except anthropic.APIStatusError as exc:
                last_error = exc
                logger.warning("API error attempt %d/%d: %s %s", attempt + 1, max_retries, exc.status_code, exc.message)
            except anthropic.APIConnectionError as exc:
                last_error = exc
                logger.warning("Connection error attempt %d/%d: %s", attempt + 1, max_retries, exc)

            if attempt < max_retries - 1:
                delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
                logger.info("Retrying in %ds…", delay)
                time.sleep(delay)

        raise RuntimeError(f"LLM call_json failed after {max_retries} attempts: {last_error}")

    def call_text(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        max_retries: int = 3,
    ) -> str:
        """Call Claude and return the raw text response with retry."""
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                result = self._call(system, user, max_tokens)
                logger.debug("call_text OK (attempt %d, %d chars)", attempt + 1, len(result))
                return result
            except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
                last_error = exc
                logger.warning("API error attempt %d/%d: %s", attempt + 1, max_retries, exc)
                if attempt < max_retries - 1:
                    time.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])

        raise RuntimeError(f"LLM call_text failed after {max_retries} attempts: {last_error}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call(self, system: str, user: str, max_tokens: int) -> str:
        msg = self._client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text
