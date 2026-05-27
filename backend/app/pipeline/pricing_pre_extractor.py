"""
Deterministic pricing pre-extractor.

Scans full RawDocument.content for explicit price/rate patterns and builds
FactObject instances that bypass the Agent 3 content truncation bottleneck
(doc.content[:8000] misses price tables in 50-100KB cloud pricing pages).

Key design decisions:
- evidence_quote is always a verbatim substring of doc.content (passes validate_fact verbatim check)
- entity is inferred from GPU model name, not from cloud provider (passes KNOWN_ENTITIES check)
- rejects vague patterns ("contact us", "starting price" without amount) to avoid false positives
- deduplication by (url, gpu_model, normalized_price) prevents redundant facts
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from app.config.companies import KNOWN_ENTITIES
from app.schemas.models import FactObject, RawDocument, SignalType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_PRICE_PATTERNS_TO_RUN = 5   # skip thin docs

_GPU_ENTITY_MAP: dict[str, str] = {
    "H100": "Nvidia",
    "H200": "Nvidia",
    "B200": "Nvidia",
    "B300": "Nvidia",
    "L40S": "Nvidia",
    "A100": "Nvidia",
    "MI300X": "AMD",
    "MI325X": "AMD",
    "MI350": "AMD",
    "RTX PRO 6000": "Nvidia",
}

_GPU_MODEL_RE = re.compile(
    r"\b(H100|H200|B200|B300|L40S|A100|MI300X|MI325X|MI350|RTX\s*PRO\s*6000)\b",
    re.IGNORECASE,
)

_PRICE_AMOUNT_RE = re.compile(
    r"\$\s*[\d,]+(?:\.\d+)?(?:\s*/\s*(?:GPU\s+)?(?:hr|hour|mo|month))?"
    r"|\b[\d,]+(?:\.\d+)?\s*(?:USD|dollars?)(?:\s*/\s*(?:hr|hour|mo|month))?"
    r"|\bper\s+(?:GPU\s+)?(?:hour|month)\b"
    r"|\blead\s+time\b.{0,60}(?:\d+\s+(?:week|month|day))",
    re.IGNORECASE,
)

# Reject windows containing these patterns (no verifiable price or vague language)
_PRICING_REJECT_RE = re.compile(
    r"contact\s+us\s+for\s+pricing"
    r"|price\s+on\s+request"
    r"|get\s+a\s+quote"
    r"|starting\s+price(?!\s+of\s+\$)"
    r"|\bprice\s+index\b"
    r"|\bprice\s+tracker\b"
    r"|\bprice\s+benchmark\b",
    re.IGNORECASE,
)

# Domains where entity context can be inferred even without an explicit GPU model match
_PRICING_DOMAINS: frozenset[str] = frozenset({
    "coreweave.com", "runpod.io", "lambdalabs.com", "lambda.ai",
    "aws.amazon.com", "azure.microsoft.com", "cloud.google.com",
    "oracle.com", "supermicro.com", "thinkmate.com",
})

# Provider display names keyed by domain
_DOMAIN_PROVIDER_MAP: dict[str, str] = {
    "coreweave.com": "CoreWeave",
    "runpod.io": "RunPod",
    "lambdalabs.com": "Lambda Labs",
    "lambda.ai": "Lambda",
    "aws.amazon.com": "AWS",
    "azure.microsoft.com": "Azure",
    "cloud.google.com": "Google Cloud",
    "oracle.com": "Oracle Cloud",
    "supermicro.com": "Supermicro",
    "thinkmate.com": "ThinkMate",
}

_WINDOW_CHARS = 400       # chars each side of price match for context
_MAX_EVIDENCE_CHARS = 280 # evidence_quote hard cap (verbatim substring)
_MAX_CLAIM_CHARS = 140    # under the 150-char validation limit
_MAX_FACTS_PER_DOC = 8    # per-document cap

# ---------------------------------------------------------------------------
# Module-level audit accumulator
# ---------------------------------------------------------------------------

_PRE_EXTRACTOR_AUDIT: dict = {
    "pricing_pre_extractor_docs_seen": 0,
    "pricing_pre_extractor_candidates_found": 0,
    "pricing_pre_extractor_facts_created": 0,
    "pricing_pre_extractor_facts_rejected": 0,
    "pricing_pre_extractor_duplicate_count": 0,
    "pricing_pre_extractor_top_domains": Counter(),
    "pricing_pre_extractor_sample_facts": [],
}


def get_pre_extractor_audit() -> dict:
    out = dict(_PRE_EXTRACTOR_AUDIT)
    out["pricing_pre_extractor_top_domains"] = dict(out["pricing_pre_extractor_top_domains"])
    return out


def reset_pre_extractor_audit() -> None:
    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_docs_seen"] = 0
    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_candidates_found"] = 0
    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_facts_created"] = 0
    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_facts_rejected"] = 0
    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_duplicate_count"] = 0
    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_top_domains"] = Counter()
    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_sample_facts"] = []


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PricingCandidate:
    window_text: str      # ±400 char context window (verbatim from doc.content)
    evidence_quote: str   # ≤280-char sentence-trimmed window (verbatim substring)
    price_text: str       # matched price string
    gpu_model: Optional[str]
    entity: str           # KNOWN_ENTITIES member
    provider: str         # display name e.g. "CoreWeave"
    dedup_key: str        # url|gpu_model|price_normalized


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def count_pricing_patterns(content: str) -> int:
    return len(_PRICE_AMOUNT_RE.findall(content))


def normalize_price_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def infer_gpu_model(context: str) -> Optional[str]:
    m = _GPU_MODEL_RE.search(context)
    if not m:
        return None
    raw = m.group(0)
    # Normalize whitespace in multi-word models (e.g. "RTX PRO 6000")
    return re.sub(r"\s+", " ", raw.upper())


def infer_provider_from_url(url: str) -> str:
    domain = _extract_domain(url)
    return _DOMAIN_PROVIDER_MAP.get(domain, domain)


def _extract_domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        parts = host.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else host
    except Exception:
        return ""


def _sentence_trim(text: str, max_chars: int) -> str:
    """
    Return the central portion of text, trimmed to sentence boundaries where
    possible. If the text is already within max_chars, return it unchanged.
    """
    if len(text) <= max_chars:
        return text
    # Try to start at a sentence boundary
    mid = len(text) // 2
    half = max_chars // 2
    start = max(0, mid - half)
    end = min(len(text), mid + half)

    # Walk start forward to a sentence start
    for i in range(start, min(start + 60, end)):
        if text[i - 1:i] in (".", "\n") and i < end:
            start = i
            break

    # Walk end backward to a sentence end
    for i in range(end, max(end - 60, start), -1):
        if text[i - 1:i] in (".", "\n"):
            end = i
            break

    trimmed = text[start:end].strip()
    return trimmed[:max_chars]


def _guard_check(doc: RawDocument) -> bool:
    """True if pre-extractor should run on this document."""
    if not doc.extraction_allowed:
        return False
    if not doc.content:
        return False
    if count_pricing_patterns(doc.content) < _MIN_PRICE_PATTERNS_TO_RUN:
        return False
    if doc.signal_type_hint == SignalType.pricing_pressure:
        return True
    domain = _extract_domain(doc.url)
    return any(domain == d or domain.endswith("." + d) for d in _PRICING_DOMAINS)


# Public alias used by agent3_fact_extractors.py
def _should_run_pre_extractor(doc: RawDocument) -> bool:
    return _guard_check(doc)


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract_pricing_context_windows(
    content: str,
    source_url: str,
    entity_hint: Optional[str] = None,
    provider_hint: Optional[str] = None,
) -> list[PricingCandidate]:
    """
    Scan full content for price patterns and return a deduplicated list of
    PricingCandidate objects, each with a verbatim evidence_quote substring.
    """
    domain = _extract_domain(source_url)
    provider = provider_hint or _DOMAIN_PROVIDER_MAP.get(domain, domain)
    norm_url = source_url.rstrip("/")

    candidates: list[PricingCandidate] = []
    seen_dedup_keys: set[str] = set()

    for match in _PRICE_AMOUNT_RE.finditer(content):
        pos = match.start()
        w_start = max(0, pos - _WINDOW_CHARS)
        w_end = min(len(content), pos + _WINDOW_CHARS)
        window = content[w_start:w_end]

        # Skip windows with reject patterns
        if _PRICING_REJECT_RE.search(window):
            continue

        gpu_model = infer_gpu_model(window)

        # Require GPU/product context unless we're on a known pricing domain
        if gpu_model is None and domain not in _PRICING_DOMAINS:
            continue

        # Derive entity
        if entity_hint and entity_hint in KNOWN_ENTITIES:
            entity = entity_hint
        elif gpu_model:
            normalized_model = re.sub(r"\s+", " ", gpu_model.upper())
            # Try exact map key, then just first word (e.g. "MI300X")
            entity = _GPU_ENTITY_MAP.get(normalized_model) or _GPU_ENTITY_MAP.get(gpu_model.split()[0].upper(), "market")
        else:
            entity = "market"

        if entity not in KNOWN_ENTITIES:
            entity = "market"

        # Build evidence_quote from a tighter window
        eq_start = max(0, pos - 200)
        eq_end = min(len(content), pos + 200)
        raw_eq = content[eq_start:eq_end]
        evidence_quote = _sentence_trim(raw_eq, _MAX_EVIDENCE_CHARS).strip()

        # Must be non-empty and actually present as substring
        if not evidence_quote or evidence_quote not in content:
            continue

        # Deduplication key
        price_text = match.group(0).strip()
        norm_price = normalize_price_text(price_text)
        dedup_key = f"{norm_url}|{(gpu_model or '').lower()}|{norm_price}"

        if dedup_key in seen_dedup_keys:
            continue
        seen_dedup_keys.add(dedup_key)

        candidates.append(PricingCandidate(
            window_text=window,
            evidence_quote=evidence_quote,
            price_text=price_text,
            gpu_model=gpu_model,
            entity=entity,
            provider=provider,
            dedup_key=dedup_key,
        ))

    # Return richer evidence first
    candidates.sort(key=lambda c: -len(c.evidence_quote))
    return candidates


def build_pricing_fact(candidate: PricingCandidate, doc: RawDocument) -> Optional[FactObject]:
    """Convert a PricingCandidate to a FactObject; returns None if safety checks fail."""
    # Verbatim check — must be present in full document content
    if candidate.evidence_quote not in doc.content:
        _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_facts_rejected"] += 1
        logger.debug("Pre-extractor: evidence_quote not verbatim in doc %s", doc.doc_id)
        return None

    if candidate.entity not in KNOWN_ENTITIES:
        _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_facts_rejected"] += 1
        logger.debug("Pre-extractor: entity %r not in KNOWN_ENTITIES", candidate.entity)
        return None

    # Confidence: 0.85 for explicit $ price, 0.75 for lead-time / per-hour language only
    has_dollar = bool(re.search(r"\$[\d,]+", candidate.price_text))
    confidence = 0.85 if has_dollar else 0.75

    # Build claim
    if candidate.gpu_model:
        model_display = re.sub(r"\s+", " ", candidate.gpu_model)
        raw_claim = f"{model_display} GPU instances priced at {candidate.price_text} via {candidate.provider}"
    else:
        raw_claim = f"GPU cloud pricing at {candidate.price_text} via {candidate.provider}"
    claim = raw_claim[:_MAX_CLAIM_CHARS]

    fact = FactObject(
        fact_id=f"fact_{uuid4().hex[:12]}",
        doc_id=doc.doc_id,
        entity=candidate.entity,
        signal_type=SignalType.pricing_pressure,
        claim=claim,
        evidence_quote=candidate.evidence_quote,
        source_url=doc.url,
        source_tier=doc.source_tier,
        published_date=doc.published_date,
        sentiment="neutral",
        sentiment_score=0.0,
        confidence=confidence,
        atomic_claims=None,
        safe_verified=False,
    )
    return fact


def extract_pricing_facts_from_document(doc: RawDocument) -> list[FactObject]:
    """
    Main entry point. Scans full doc.content and returns pricing_pressure FactObjects.
    Never raises; returns empty list on any failure.
    """
    if not _guard_check(doc):
        return []

    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_docs_seen"] += 1
    domain = _extract_domain(doc.url)
    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_top_domains"][domain] += 1

    try:
        candidates = extract_pricing_context_windows(doc.content, doc.url)
    except Exception as exc:
        logger.warning("Pre-extractor window extraction failed for %s: %s", doc.url, exc)
        return []

    _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_candidates_found"] += len(candidates)

    facts: list[FactObject] = []
    for candidate in candidates[:_MAX_FACTS_PER_DOC]:
        fact = build_pricing_fact(candidate, doc)
        if fact is not None:
            facts.append(fact)
            _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_facts_created"] += 1
            if len(_PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_sample_facts"]) < 5:
                _PRE_EXTRACTOR_AUDIT["pricing_pre_extractor_sample_facts"].append({
                    "url": doc.url,
                    "entity": fact.entity,
                    "claim": fact.claim,
                    "evidence_quote": fact.evidence_quote[:80],
                })

    logger.info(
        "Pre-extractor: doc=%s domain=%s patterns=%d candidates=%d facts=%d",
        doc.doc_id, domain,
        count_pricing_patterns(doc.content),
        len(candidates),
        len(facts),
    )
    return facts
