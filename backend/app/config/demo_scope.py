"""Demo-scope configuration for the Bright Data Track 2 hackathon slice.

Full 8-company support remains in companies.py. This module only controls the
default runnable scope for cheaper, repeatable demos.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from app.config.companies import COMPANIES, Company
from app.schemas.models import SignalType


DEMO_COMPANY_NAMES = ["Nvidia", "AMD", "Supermicro"]
DEMO_CORE_SIGNAL_TYPES = [
    SignalType.investor_signal.value,
    SignalType.product_launch.value,
    SignalType.pricing_pressure.value,
    SignalType.supplier_risk.value,
]
DEMO_OPTIONAL_SIGNAL_TYPES = [
    SignalType.hiring_momentum.value,
    SignalType.news_sentiment.value,
    SignalType.strategic_messaging.value,
]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class ScopeConfig:
    demo_scope_enabled: bool
    market: str
    companies: list[str]
    core_signal_types: list[str]
    optional_signal_types: list[str]
    min_queries: int
    max_queries: int


def is_demo_scope_enabled() -> bool:
    return _env_bool("PULSELENS_DEMO_SCOPE", True)


def get_demo_companies() -> list[Company]:
    by_name = {company.name: company for company in COMPANIES}
    return [by_name[name] for name in DEMO_COMPANY_NAMES if name in by_name]


def get_scope_config(*, force_full: bool = False) -> ScopeConfig:
    demo_enabled = is_demo_scope_enabled() and not force_full
    if demo_enabled:
        return ScopeConfig(
            demo_scope_enabled=True,
            market="US AI Hardware / Semiconductor",
            companies=list(DEMO_COMPANY_NAMES),
            core_signal_types=list(DEMO_CORE_SIGNAL_TYPES),
            optional_signal_types=list(DEMO_OPTIONAL_SIGNAL_TYPES),
            min_queries=_env_int("DEMO_MIN_QUERIES", 22),
            max_queries=_env_int("DEMO_MAX_QUERIES", 32),
        )
    return ScopeConfig(
        demo_scope_enabled=False,
        market="US AI Hardware / Semiconductor",
        companies=[company.name for company in COMPANIES],
        core_signal_types=[signal.value for signal in SignalType],
        optional_signal_types=[],
        min_queries=_env_int("AGENT1_MIN_QUERIES", 40),
        max_queries=_env_int("AGENT1_MAX_QUERIES", 50),
    )


def scope_payload(scope: ScopeConfig) -> dict:
    return {
        "demo_scope_enabled": scope.demo_scope_enabled,
        "market": scope.market,
        "companies": scope.companies,
        "core_signal_types": scope.core_signal_types,
        "optional_signal_types": scope.optional_signal_types,
        "target_signal_types": scope.core_signal_types,
        "min_queries": scope.min_queries,
        "max_queries": scope.max_queries,
    }
