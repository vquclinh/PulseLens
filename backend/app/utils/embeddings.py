# Sentence-transformer embeddings for stored facts.
from __future__ import annotations

import hashlib
import logging
import math
import os
from functools import lru_cache
from typing import Iterable

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)


@lru_cache(maxsize=1)
def _load_model():
    if os.getenv("PULSELENS_DISABLE_EMBEDDINGS", "").lower() in {"1", "true", "yes"}:
        raise RuntimeError("Embeddings disabled by PULSELENS_DISABLE_EMBEDDINGS")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is not installed; install backend requirements"
        ) from exc

    logger.info("Loading embedding model %s", DEFAULT_EMBEDDING_MODEL)
    return SentenceTransformer(DEFAULT_EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return normalized embeddings using sentence-transformers."""
    if not texts:
        return []
    model = _load_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [[float(x) for x in vector] for vector in vectors]


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    va = list(a)
    vb = list(b)
    if not va or not vb or len(va) != len(vb):
        return 0.0
    dot = sum(x * y for x, y in zip(va, vb))
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(y * y for y in vb))
    return dot / (na * nb) if na and nb else 0.0


def lexical_score(query: str, text: str) -> float:
    """Small fallback scorer when embeddings are unavailable."""
    q_terms = _terms(query)
    if not q_terms:
        return 0.0
    t_terms = _terms(text)
    overlap = len(q_terms & t_terms)
    return overlap / max(len(q_terms), 1)


def _terms(text: str) -> set[str]:
    words = []
    for raw in text.lower().replace("/", " ").replace("-", " ").split():
        word = "".join(ch for ch in raw if ch.isalnum())
        if len(word) >= 3:
            words.append(word)
    return set(words)


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
