"""Pipeline quality thresholds and model/runtime knobs.

Defaults are intentionally strict enough to surface weak retrieval as
PARTIAL_PASS instead of allowing the system to pretend coverage is complete.
Environment variables can tune the values for local/dev runs without code edits.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


# Agent 1 query planning.
MIN_QUERIES = _env_int("AGENT1_MIN_QUERIES", 40)
MAX_QUERIES = _env_int("AGENT1_MAX_QUERIES", 50)
MIN_EXPANSION_QUERIES = _env_int("AGENT1_MIN_EXPANSION_QUERIES", 5)
MAX_EXPANSION_QUERIES = _env_int("AGENT1_MAX_EXPANSION_QUERIES", 10)
MIN_SIGNAL_TYPES = _env_int("AGENT1_MIN_SIGNAL_TYPES", 7)
MAX_EXPANSION_ROUNDS = _env_int("MAX_EXPANSION_ROUNDS", 2)
MAX_MALFORMED_QUERY_RATE = _env_float("AGENT1_MAX_MALFORMED_QUERY_RATE", 0.10)


@dataclass(frozen=True)
class QualityGateConfig:
    min_facts: int = _env_int("QUALITY_MIN_FACTS", 50)
    min_signal_types: int = _env_int("QUALITY_MIN_SIGNAL_TYPES", 7)
    min_company_coverage_ratio: float = _env_float("QUALITY_MIN_COMPANY_COVERAGE_RATIO", 0.75)
    max_zero_doc_query_rate: float = _env_float("QUALITY_MAX_ZERO_DOC_QUERY_RATE", 0.35)
    max_fetch_error_rate: float = _env_float("QUALITY_MAX_FETCH_ERROR_RATE", 0.35)
    min_source_count: int = _env_int("QUALITY_MIN_SOURCE_COUNT", 15)


QUALITY_GATE_CONFIG = QualityGateConfig()


# Fact validation and SAFE.
FACT_MIN_CONFIDENCE = _env_float("FACT_MIN_CONFIDENCE", 0.60)
SAFE_MIN_SUPPORT_RATIO = _env_float("SAFE_MIN_SUPPORT_RATIO", 0.50)
SAFE_MAX_CONCURRENT = _env_int("SAFE_MAX_CONCURRENT", 5)


# Agent 4.
FINBERT_MODEL = os.getenv("FINBERT_MODEL", "ProsusAI/finbert")
