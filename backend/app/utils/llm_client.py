# OpenRouter LLM client — OpenAI-compatible API, sync JSON/text calls with retry and structured logging
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import openai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_BACKEND_ENV)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_DEFAULT_MODEL = "google/gemini-2.5-flash"

# Per-agent model assignments — override via env vars (e.g. AGENT1_MODEL=anthropic/claude-sonnet-4-5)
AGENT_MODELS: dict[str, str] = {
    "agent1": os.getenv("AGENT1_MODEL", _DEFAULT_MODEL),   # Query Planner
    "agent3": os.getenv("AGENT3_MODEL", _DEFAULT_MODEL),   # Fact Extractor
    "agent5": os.getenv("AGENT5_MODEL", _DEFAULT_MODEL),   # Contradiction Writer
    "agent6": os.getenv("AGENT6_MODEL", _DEFAULT_MODEL),   # Narrative Synthesizer
    "agent7": os.getenv("AGENT7_MODEL", _DEFAULT_MODEL),   # Watch List Builder
    "agent8": os.getenv("AGENT8_MODEL", _DEFAULT_MODEL),   # Analyst Chat
}

_RETRY_DELAYS = [1, 2, 4]   # seconds between retry attempts


def _extract_json(text: str) -> str:
    """Strip markdown code fences if the model wrapped its JSON output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.rstrip())
    return text.strip()


class LLMClient:
    def __init__(self, api_key: str | None = None, agent_name: str = "agent1") -> None:
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY is required — set it in .env or pass api_key=")
        self._client = openai.OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=key,
        )
        self._model = AGENT_MODELS.get(agent_name, AGENT_MODELS["agent1"])

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def call_json(
        self,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ) -> Any:
        """
        Call the model and return parsed JSON. Retries on API error or JSON parse failure.
        Raises RuntimeError after all attempts are exhausted.
        """
        resolved_model = model or self._model
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                raw = self._call(system, user, resolved_model, max_tokens)
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
            except openai.APIStatusError as exc:
                last_error = exc
                logger.warning("API error attempt %d/%d: %s %s", attempt + 1, max_retries, exc.status_code, exc.message)
            except openai.APIConnectionError as exc:
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
        model: str | None = None,
        max_tokens: int = 2048,
        max_retries: int = 3,
    ) -> str:
        """Call the model and return the raw text response with retry."""
        resolved_model = model or self._model
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                result = self._call(system, user, resolved_model, max_tokens)
                logger.debug("call_text OK (attempt %d, %d chars)", attempt + 1, len(result))
                return result
            except (openai.APIStatusError, openai.APIConnectionError) as exc:
                last_error = exc
                logger.warning("API error attempt %d/%d: %s", attempt + 1, max_retries, exc)
                if attempt < max_retries - 1:
                    time.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])

        raise RuntimeError(f"LLM call_text failed after {max_retries} attempts: {last_error}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call(self, system: str, user: str, model: str, max_tokens: int) -> str:
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("LLM response did not include text content")
        return content
