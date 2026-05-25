# Agent 3 — RASG-inspired schema extraction (arXiv:2405.20245)
# Uses prompt-enforced JSON schema to constrain extraction output.
# Not true function/tool calling; applies RASG's schema-constraint insight via prompting.
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from app.config.companies import COMPANIES
from app.schemas.models import FactObject, RawDocument, SignalType
from app.utils.helpers import generate_uuid
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

MAX_FACTS_PER_DOCUMENT = int(os.getenv("MAX_FACTS_PER_DOCUMENT", "10"))
_MAX_CONCURRENT = 10  # asyncio.to_thread slots for LLM calls

ENTITY_ALIASES: dict[str, str] = {"market": "market"}
for _company in COMPANIES:
    ENTITY_ALIASES[_company.name.lower()] = _company.name
    ENTITY_ALIASES[_company.ticker.lower()] = _company.name
    for _alias in _company.known_aliases:
        ENTITY_ALIASES[_alias.lower()] = _company.name


def normalize_entity(raw: str) -> str:
    return ENTITY_ALIASES.get(raw.lower().strip(), raw.strip())

# ── Prompts ────────────────────────────────────────────────────────────────────

_SYSTEM = """\
You are a financial market intelligence extraction system.

Method: RASG-inspired schema extraction (arXiv:2405.20245)
Fill the schema fields exactly — return only valid JSON matching the schema below.
Extract ONLY facts EXPLICITLY STATED in the provided text.
Do NOT infer, interpret, or add information not present in the text.
Return ONLY a valid JSON array. If no relevant facts exist, return [].

TIME WINDOW: Only extract facts that are current or recent.
Discard any fact referencing data, events, or figures from before January 2024.
If a document only contains historical data older than 2024, return [].

Schema for each fact object:
{
  "entity":         "Company name (Nvidia|AMD|Intel|Broadcom|Supermicro|Dell|HPE|Micron) or 'market'",
  "signal_type":    "one of: hiring_momentum | product_launch | pricing_pressure | strategic_messaging | investor_signal | news_sentiment | supplier_risk",
  "claim":          "1 complete declarative sentence, max 150 chars, no interpretation",
  "evidence_quote": "EXACT verbatim substring copied from the Text below — must appear word-for-word",
  "published_date": "ISO 8601 date string (YYYY-MM-DD) or null",
  "confidence":     0.0 to 1.0 (float between 0 and 1)
}

Rules:
- evidence_quote MUST be an exact substring of the Text — no paraphrasing
- claim must not exceed 150 characters
- claim must be a complete declarative sentence with subject, verb, and object.
  Do NOT copy headlines verbatim. Do NOT start with "News from..." or "According to...".
  Restate the fact in plain financial analyst style.
- TIME WINDOW: Discard any fact referencing data or events from before January 2024.
- confidence calibration — how explicitly and precisely is this fact stated?
  1.0 = exact numbers/dates/names quoted verbatim from an official source
  0.9 = clearly stated fact with specific detail (named metric, named date)
  0.8 = fact stated but without specific numbers or dates
  0.7 = fact implied strongly but not stated with full precision
  Below 0.7 = do not include this fact
  Examples: "Revenue was $44.1B in Q1 2025" from earnings release → 1.0
            "Revenue increased significantly this quarter" → 0.8
            "Revenue growth may continue next year" → do not include\
"""

_USER = """\
Context:
  query:           {query}
  expected_signal: {expected_signal}

Text:
{content}\
"""

# ── Core extractor ─────────────────────────────────────────────────────────────


class FactExtractor:
    def __init__(self) -> None:
        self._llm = LLMClient(agent_name="agent3")

    def extract(self, doc: RawDocument) -> list[FactObject]:
        """Synchronous extraction for one document — called via asyncio.to_thread."""
        user = _USER.format(
            query=doc.collection_query,
            expected_signal=doc.signal_type_hint.value if doc.signal_type_hint else "any",
            content=doc.content[:8000],
        )
        try:
            raw = self._llm.call_json(_SYSTEM, user, max_tokens=2048)
        except Exception as exc:
            logger.warning("Agent 3 LLM failed for doc %s: %s", doc.doc_id, exc)
            return []

        if not isinstance(raw, list):
            logger.debug("Agent 3 got non-list response for doc %s: %s", doc.doc_id, type(raw))
            return []

        facts: list[FactObject] = []
        for item in raw[:MAX_FACTS_PER_DOCUMENT]:
            if not isinstance(item, dict):
                continue
            fact = _build_fact(item, doc)
            if fact is not None:
                facts.append(fact)

        logger.debug(
            "Agent 3 extracted %d raw facts from doc %s (%s)",
            len(facts), doc.doc_id, doc.domain,
        )
        return facts


# ── Helpers ────────────────────────────────────────────────────────────────────


def _build_fact(item: dict, doc: RawDocument) -> Optional[FactObject]:
    """Parse one LLM-returned dict into a FactObject; return None on any schema error."""
    try:
        signal_type = SignalType(str(item.get("signal_type", "")).strip())
    except ValueError:
        return None

    entity = normalize_entity(str(item.get("entity", "")))
    claim = str(item.get("claim", "")).strip()
    evidence_quote = str(item.get("evidence_quote", "")).strip()

    if not entity or not claim or not evidence_quote:
        return None

    # Reject overlong fields — truncating hides bad LLM output, rejecting surfaces it
    if len(claim) > 150:
        return None
    if len(evidence_quote) > 200:
        return None

    try:
        confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0

    pub_date_raw = item.get("published_date")
    published_date: Optional[str] = str(pub_date_raw) if pub_date_raw else doc.published_date

    return FactObject(
        fact_id=f"fact_{generate_uuid()[:12]}",
        doc_id=doc.doc_id,
        entity=entity,
        signal_type=signal_type,
        claim=claim,
        evidence_quote=evidence_quote,
        source_url=doc.url,
        source_tier=doc.source_tier,
        published_date=published_date,
        sentiment="neutral",     # set by Agent 4 (FinBERT)
        sentiment_score=0.0,     # set by Agent 4 (FinBERT)
        confidence=confidence,
    )


# ── Async batch entry point ────────────────────────────────────────────────────


async def extract_facts_from_documents(documents: list[RawDocument]) -> list[FactObject]:
    """
    Async batch extraction — runs LLM calls in thread pool (LLMClient is sync).
    Bounded to _MAX_CONCURRENT simultaneous LLM calls.
    """
    if not documents:
        return []

    extractor = FactExtractor()
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def _extract_one(doc: RawDocument) -> list[FactObject]:
        async with semaphore:
            return await asyncio.to_thread(extractor.extract, doc)

    results = await asyncio.gather(*(_extract_one(doc) for doc in documents))

    all_facts: list[FactObject] = []
    for facts in results:
        all_facts.extend(facts)

    logger.info(
        "Agent 3 extracted %d raw facts from %d documents", len(all_facts), len(documents)
    )
    return all_facts


# ── Standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    async def main() -> None:
        from app.pipeline.agent2_web_workers import collect_documents_for_query
        from app.schemas.models import SearchQuery, SignalType as ST
        from app.utils.helpers import generate_uuid

        # Fetch a small set of real documents from Agent 2
        test_queries = [
            SearchQuery(
                query_id=generate_uuid()[:12],
                query_text="Nvidia AI GPU hiring jobs 2025",
                target_entity="Nvidia",
                signal_type=ST.hiring_momentum,
                source_type="serp_news",
                priority=1,
                expected_source_tier=3,
            ),
            SearchQuery(
                query_id=generate_uuid()[:12],
                query_text="AMD MI400 product launch announcement 2025",
                target_entity="AMD",
                signal_type=ST.product_launch,
                source_type="serp_news",
                priority=1,
                expected_source_tier=3,
            ),
        ]

        print("\n── Agent 2: fetching documents ──────────────────────────────")
        docs: list = []
        for q in test_queries:
            q_docs = await collect_documents_for_query(q)
            docs.extend(q_docs)
            print(f"  query '{q.query_text[:50]}' → {len(q_docs)} docs")

        if not docs:
            print("No documents returned — check BrightData config")
            return

        print(f"\n── Agent 3: extracting facts from {len(docs)} documents ────")
        from app.pipeline.agent3_fact_extractors import extract_facts_from_documents
        raw_facts = await extract_facts_from_documents(docs)

        if not raw_facts:
            print("No facts extracted")
            return

        # Group by entity → signal_type
        from collections import defaultdict
        groups: dict = defaultdict(list)
        for f in raw_facts:
            groups[(f.entity, f.signal_type.value)].append(f)

        print(f"\nExtracted {len(raw_facts)} raw facts across {len(groups)} (entity, signal_type) groups:\n")
        for (entity, sig), facts in sorted(groups.items()):
            print(f"  [{entity}] {sig}  ({len(facts)} facts)")
            for f in facts:
                print(f"    fact_id:  {f.fact_id}")
                print(f"    claim:    {f.claim}")
                print(f"    quote:    {f.evidence_quote[:120]}")
                print(f"    conf:     {f.confidence:.2f}  tier:{f.source_tier}  date:{f.published_date}")
                print()

    asyncio.run(main())
