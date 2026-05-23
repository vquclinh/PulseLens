# Source tier classification — domain sets, weights, assign_tier(), and Bright Data tool mapping
from typing import Literal
from urllib.parse import urlparse


TIER_1_DOMAINS: set[str] = {
    "sec.gov",
    "ir.nvidia.com",
    "ir.amd.com",
    "investor.intel.com",
    "investors.broadcom.com",
    "ir.supermicro.com",
    "ir.dell.com",
    "investor.hpe.com",
    "investor.micron.com",
}

TIER_2_DOMAINS: set[str] = {
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "apnews.com",
    "businesswire.com",
    "prnewswire.com",
}

TIER_3_DOMAINS: set[str] = {
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "arstechnica.com",
    "semianalysis.com",
    "tomshardware.com",
    "anandtech.com",
}

TIER_WEIGHTS: dict[int, float] = {
    1: 1.0,
    2: 0.8,
    3: 0.5,
    4: 0.4,
}

TOOL_MAPPING: dict[str, str] = {
    "serp_news":      "SERP API",           # news and general search results
    "job_pages":      "Web Scraper API",    # LinkedIn, Glassdoor, Indeed
    "ir_pages":       "Web Scraper API",    # SEC EDGAR, IR pages
    "pricing_pages":  "Web Scraper API",    # pricing and distributor listings
    "dynamic_pages":  "Scraping Browser",   # JavaScript-rendered pages
    "protected":      "Web Unlocker",       # anti-bot protected sites
}


def assign_tier(url: str) -> Literal[1, 2, 3, 4]:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().lstrip("www.")
    except Exception:
        return 4
    if host in TIER_1_DOMAINS:
        return 1
    if host in TIER_2_DOMAINS:
        return 2
    if host in TIER_3_DOMAINS:
        return 3
    return 4
