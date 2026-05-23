# Anthropic claude-sonnet-4-20250514 wrapper with structured JSON output and retry logic
import anthropic
from typing import Any


class LLMClient:
    def __init__(self, api_key: str) -> None:
        pass

    async def extract_facts(self, document_content: str, entity: str) -> Any:
        pass

    async def synthesize_narrative(self, context: dict) -> Any:
        pass

    async def chat_completion(self, messages: list, system_prompt: str) -> Any:
        pass
