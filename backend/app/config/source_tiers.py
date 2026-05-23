# Domain-to-tier mapping and assign_tier() helper for source credibility scoring
from typing import Literal

TIER_1_DOMAINS: set = set()
TIER_2_DOMAINS: set = set()
TIER_3_DOMAINS: set = set()


def assign_tier(url: str) -> Literal[1, 2, 3, 4]:
    pass
