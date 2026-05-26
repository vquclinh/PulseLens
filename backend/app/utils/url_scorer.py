# URL relevance scoring — filters SERP results before Bright Data fetch.
# All domain knowledge from source_tiers.py; all entity knowledge from companies.py.
# Pricing source families are intentionally explicit for the hackathon demo
# playbook; company/IR domain knowledge still comes from config.
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Dict, FrozenSet, List
from urllib.parse import urlparse

from app.config.companies import COMPANIES
from app.config.source_tiers import TIER_1_DOMAINS, TIER_2_DOMAINS, TIER_3_DOMAINS, TIER_WEIGHTS, assign_tier
from app.utils.helpers import extract_domain

if TYPE_CHECKING:
    from app.schemas.models import SearchQuery

# Generic financial terms per signal type — derived from ARCHITECTURE.md signal playbook.
# These are vocabulary terms, not domain names.
SIGNAL_EVIDENCE_TERMS: Dict[str, List[str]] = {
    "investor_signal": [
        "earnings", "guidance", "revenue", "analyst", "upgrade", "downgrade",
        "13f", "sec", "filing", "institutional",
    ],
    "news_sentiment": [
        "ai", "chip", "semiconductor", "data center", "accelerator", "demand",
        "supply", "market",
    ],
    "pricing_pressure": [
        "price", "pricing", "discount", "availability", "lead time", "margin",
        "cost", "gpu", "server",
    ],
    "strategic_messaging": [
        "ceo", "cfo", "strategy", "roadmap", "investor day", "earnings call",
        "guidance", "outlook", "capex",
    ],
    "hiring_momentum": [
        "hiring", "layoff", "jobs", "engineer", "workforce", "career",
        "headcount", "talent", "recruit",
    ],
    "product_launch": [
        "launch", "announce", "release", "available", "new", "product",
        "accelerator", "benchmark",
    ],
    "supplier_risk": [
        "supply", "shortage", "hbm", "cowos", "export", "tsmc", "samsung",
        "foundry", "component",
    ],
}

MARKET_RELEVANCE_TERMS = [
    "ai", "artificial intelligence", "gpu", "accelerator", "semiconductor",
    "chip", "data center", "server", "hbm", "memory", "foundry", "hardware",
]

FORUM_MARKERS = [
    "reddit.", "forum", "community", "stackoverflow", "quora", "hackernews",
    "news.ycombinator", "discord", "telegram",
]

SOCIAL_MARKERS = [
    "facebook.com", "twitter.com", "x.com/", "linkedin.com/pulse", "linkedin.com/posts",
    "instagram.com",  # Sprint 3: was missing, causing Instagram URLs to slip through supplier_risk queries
]

TRACKING_MARKERS = [
    "links.message.", "click.", "email.", "mailchi.mp", "utm_", "mkt_tok",
    "trk=", "tracking", "redirect",
]

UNRELATED_VENDOR_TERMS = [
    "symantec", "antivirus", "endpoint security", "cybersecurity", "cdw.com/product",
]

PRICING_SIGNAL_TERMS = [
    "price", "pricing", "discount", "availability", "available", "lead time",
    "on-demand", "reserved", "spot", "rental", "cost", "quote", "buy",
]

PRICING_HARDWARE_TERMS = [
    "gpu", "accelerator", "h100", "h200", "b200", "l40s", "a100",
    "mi300", "mi300x", "mi325", "mi325x", "mi350", "blackwell",
    "instinct", "ec2", "vm", "instance", "compute", "ai server",
    "gpu server", "rack-scale", "liquid cooling",
]

CLOUD_PRICING_DOMAINS = {
    "aws.amazon.com",
    "azure.microsoft.com",
    "cloud.google.com",
    "oracle.com",
    "coreweave.com",
    "lambdalabs.com",
    "runpod.io",
}

COMPANY_PRODUCT_DOMAINS = {company.domain for company in COMPANIES}

COMPANY_IR_DOMAINS = frozenset(
    urlparse(company.ir_url).netloc.lower().lstrip("www.")
    for company in COMPANIES
)

OEM_DISTRIBUTOR_DOMAINS = {
    "supermicro.com",
    "store.supermicro.com",
    "dell.com",
    "hpe.com",
    "cdw.com",
    "exxactcorp.com",
    "thinkmate.com",
    "connection.com",
    "insight.com",
}

PRICING_CONTEXT_DOMAINS = {
    "reuters.com",
    "bloomberg.com",
    "theregister.com",
    "semianalysis.com",
    "servethehome.com",
    "tomshardware.com",
    "anandtech.com",
}


# ── Source-type affinity: derived from company config, not hardcoded ───────────

def _build_source_type_affinity() -> Dict[str, FrozenSet[str]]:
    """
    Build per-source-type preferred domain sets from existing company config.
    ir_pages: IR domains + sec.gov (same set as TIER_1_DOMAINS).
    job_pages: careers URL domains from each company in COMPANIES.
    """
    career_domains: set[str] = set()
    for c in COMPANIES:
        if c.careers_url:
            netloc = urlparse(c.careers_url).netloc.lower().lstrip("www.")
            if netloc:
                career_domains.add(netloc)
    return {
        "ir_pages":  frozenset(TIER_1_DOMAINS),
        "job_pages": frozenset(career_domains),
    }


_SOURCE_TYPE_AFFINITY: Dict[str, FrozenSet[str]] = _build_source_type_affinity()


# ── Pure functions ─────────────────────────────────────────────────────────────

def get_entity_terms(target_entity: str) -> List[str]:
    """Derive search terms from company config — no hardcoding."""
    company = next(
        (c for c in COMPANIES if c.name.lower() == target_entity.lower()),
        None,
    )
    if not company:
        return [target_entity.lower()]

    terms = [
        company.name.lower(),
        company.ticker.lower(),
        company.domain.split(".")[0],   # "nvidia" from "nvidia.com"
    ]
    terms += [a.lower() for a in company.known_aliases]
    return list(set(terms))


def _term_matches(term: str, text: str) -> bool:
    """
    Always use word-boundary regex to prevent substring false-positives.
    Fixes: 'mu' (Micron ticker) matching 'communications', 'mutual', etc.
           'amd' matching 'command', 'amendment', etc.
    """
    return bool(re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE))


def _is_search_engine_result_url(url: str) -> bool:
    """
    Structural detection of search-engine navigation URLs — no domain names.
    Catches:  /search?q=...  (Google, Bing, Yahoo, Reuters site-search, etc.)
              /html?q=...    (DuckDuckGo HTML)
              /url?url=...   (Google redirect/tracking)
    """
    try:
        parsed = urlparse(url)
        host  = parsed.netloc.lower()
        path  = parsed.path.rstrip("/").lower()
        query = parsed.query.lower()
    except Exception:
        return False

    if "googleusercontent.com" in host and "/search" in path:
        return True

    # Search result pages: path=/search or /html with q= or p= param
    if path in ("/search", "/html") and re.search(r"(?:^|&)(?:q|p)=", query):
        return True

    # Google redirect / tracking URLs: path=/url with url= or q= param
    if path == "/url" and re.search(r"(?:^|&)(?:url|q)=", query):
        return True

    return False


def _extract_site_constraint(query_text: str) -> str | None:
    """Return the domain from a site: operator in query_text, or None."""
    m = re.search(r"\bsite:(\S+)", query_text, re.IGNORECASE)
    return m.group(1).lower() if m else None


def _url_matches_site(url: str, site: str) -> bool:
    """True if the URL's host equals or is a subdomain of `site`."""
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return False
    site = site.lstrip("www.")
    return host == site or host.endswith("." + site)


def _domain_in_family(domain: str, family: set[str]) -> bool:
    return any(domain == item or domain.endswith("." + item) for item in family)


# ── Error memory ───────────────────────────────────────────────────────────────

class DomainErrorMemory:
    """Remembers domains that returned permanent HTTP errors this run. Not persisted."""

    def __init__(self) -> None:
        self._failed: Dict[str, int] = {}   # domain → permanent-failure count

    def record_failure(self, url: str, status_code: int) -> None:
        if status_code in (400, 403, 404, 410):
            domain = extract_domain(url)
            self._failed[domain] = self._failed.get(domain, 0) + 1

    def is_likely_unfetchable(self, url: str) -> bool:
        """True after 2 permanent failures from the same domain."""
        return self._failed.get(extract_domain(url), 0) >= 2

    def penalty(self, url: str) -> float:
        """0 fails → 1.0, 1 fail → 0.5, 2+ fails → effectively 0 via hard rule."""
        fails = self._failed.get(extract_domain(url), 0)
        return max(0.0, 1.0 - fails * 0.5)


# ── Scorer ─────────────────────────────────────────────────────────────────────

class URLScorer:
    def __init__(self) -> None:
        self.error_memory = DomainErrorMemory()

    def _hard_rejection_reason(self, serp_result: dict, query: "SearchQuery") -> str | None:
        url = serp_result.get("url") or serp_result.get("link", "")
        title = serp_result.get("title", "")
        description = serp_result.get("snippet") or serp_result.get("description", "")
        source_type = getattr(query, "source_type", "") or ""
        haystack = f"{url} {title} {description}".lower()
        domain = extract_domain(url)

        if not url:
            return "missing_url"
        if _is_search_engine_result_url(url) or domain in {"google.com", "bing.com", "yahoo.com"}:
            return "search_engine_result_url"
        if any(marker in haystack for marker in TRACKING_MARKERS):
            return "tracking_or_email_redirect_url"

        site = _extract_site_constraint(query.query_text)
        if site and not _url_matches_site(url, site):
            return "site_constraint_mismatch"

        if any(marker in haystack for marker in FORUM_MARKERS) and source_type != "community_pages":
            return "forum_or_community_source_not_allowed"
        if any(marker in haystack for marker in SOCIAL_MARKERS):
            return "social_or_low_signal_page_not_allowed"

        if (
            "/investor-relations" in urlparse(url).path.lower()
            and not _domain_in_family(domain, COMPANY_PRODUCT_DOMAINS)
            and not _domain_in_family(domain, COMPANY_IR_DOMAINS)
            and not _domain_in_family(domain, frozenset({"sec.gov"}))
        ):
            return "fallback_ir_metadata_wrong_entity"

        if source_type == "ir_pages" and assign_tier(url) != 1:
            return "ir_pages_requires_tier1_ir_or_sec_domain"

        if source_type == "job_pages":
            career_domains = _SOURCE_TYPE_AFFINITY.get("job_pages", frozenset())
            host = urlparse(url).netloc.lower().lstrip("www.")
            jobish = any(term in haystack for term in ("job", "jobs", "career", "careers", "linkedin.com/jobs"))
            if host not in career_domains and not jobish:
                return "job_pages_requires_careers_or_jobs_domain"

        sig_key = query.signal_type.value if hasattr(query.signal_type, "value") else str(query.signal_type)

        if source_type == "pricing_pages" or sig_key == "pricing_pressure":
            pricing_reason = self._pricing_rejection_reason(domain, haystack)
            if pricing_reason:
                return pricing_reason

        if source_type == "serp_news" and assign_tier(url) == 4:
            trusted_news = domain in TIER_2_DOMAINS or domain in TIER_3_DOMAINS
            relevance_terms = MARKET_RELEVANCE_TERMS + SIGNAL_EVIDENCE_TERMS.get(sig_key, [])
            if not trusted_news and not any(term in haystack for term in relevance_terms):
                return "serp_news_irrelevant_tier4_domain"

        if self.error_memory.is_likely_unfetchable(url):
            return "domain_repeated_permanent_failures"

        return None

    def _pricing_rejection_reason(self, domain: str, haystack: str) -> str | None:
        if any(term in haystack for term in UNRELATED_VENDOR_TERMS):
            return "pricing_irrelevant_vendor_page"
        if any(marker in haystack for marker in ("login", "signin", "auth", "/support/", "support/download", "cdn.")):
            return "pricing_source_family_mismatch"

        has_pricing_signal = any(term in haystack for term in PRICING_SIGNAL_TERMS)
        has_hardware_signal = any(term in haystack for term in PRICING_HARDWARE_TERMS)
        is_cloud = _domain_in_family(domain, CLOUD_PRICING_DOMAINS)
        is_company = _domain_in_family(domain, COMPANY_PRODUCT_DOMAINS)
        is_oem = _domain_in_family(domain, OEM_DISTRIBUTOR_DOMAINS)
        is_context = _domain_in_family(domain, PRICING_CONTEXT_DOMAINS)

        if is_cloud or is_company:
            if not has_hardware_signal:
                return "pricing_missing_hardware_terms"
            if not has_pricing_signal:
                return "pricing_source_family_mismatch"
            return None

        if is_oem:
            if not has_hardware_signal:
                return "pricing_missing_hardware_terms"
            if not has_pricing_signal and "server" not in haystack:
                return "pricing_source_family_mismatch"
            return None

        if is_context:
            if not has_hardware_signal:
                return "pricing_missing_hardware_terms"
            return None

        return "pricing_source_family_mismatch"

    def score(self, serp_result: dict, query: "SearchQuery") -> float:
        # Accept both "url"/"link" and "snippet"/"description" key conventions.
        url         = serp_result.get("url") or serp_result.get("link", "")
        title       = serp_result.get("title", "")
        description = serp_result.get("snippet") or serp_result.get("description", "")

        if self._hard_rejection_reason(serp_result, query):
            return 0.0

        source_type = getattr(query, "source_type", "") or ""

        # ── Scoring components ─────────────────────────────────────────────────

        tier_score = TIER_WEIGHTS[assign_tier(url)]

        entity_terms   = get_entity_terms(query.target_entity)
        snippet        = (url + " " + title + " " + description).lower()
        matched_entity = any(_term_matches(t, snippet) for t in entity_terms)
        entity_score   = 1.0 if matched_entity else 0.0
        pricing_hardware_match = source_type == "pricing_pages" and any(
            term in snippet for term in PRICING_HARDWARE_TERMS
        )
        if pricing_hardware_match and entity_score == 0.0:
            entity_score = 0.6

        sig_key      = query.signal_type.value if hasattr(query.signal_type, "value") else str(query.signal_type)
        sig_terms    = SIGNAL_EVIDENCE_TERMS.get(sig_key, [])
        matched_sig  = sum(1 for t in sig_terms if t in snippet)
        signal_score = min(matched_sig / max(len(sig_terms) * 0.3, 1), 1.0)

        error_penalty = self.error_memory.penalty(url)

        # job_pages: soft affinity — prefer career domains; others penalised 0.5×
        job_affinity = 1.0
        if source_type == "job_pages":
            career_domains = _SOURCE_TYPE_AFFINITY.get("job_pages", frozenset())
            try:
                host = urlparse(url).netloc.lower().lstrip("www.")
            except Exception:
                host = ""
            if host not in career_domains:
                job_affinity = 0.5

        score = (
            tier_score    * 0.30
            + entity_score  * 0.40
            + signal_score  * 0.20
            + error_penalty * 0.10
        ) * job_affinity

        # ── More hard rules (after scoring) ───────────────────────────────────

        # Off-target entity: never fetch (unless querying for "market")
        if (
            query.target_entity != "market"
            and entity_score == 0.0
            and not (source_type == "ir_pages" and assign_tier(url) == 1)
            and not pricing_hardware_match
        ):
            return 0.0

        return round(score, 3)

    def rejection_reason(
        self,
        serp_result: dict,
        query: "SearchQuery",
        min_score: float = 0.3,
    ) -> str | None:
        hard_reason = self._hard_rejection_reason(serp_result, query)
        if hard_reason:
            return hard_reason
        score = self.score(serp_result, query)
        if score < min_score:
            return f"below_relevance_threshold:{score:.3f}"
        return None

    def acceptance_reason(self, serp_result: dict, query: "SearchQuery") -> str:
        url = serp_result.get("url") or serp_result.get("link", "")
        title = serp_result.get("title", "")
        description = serp_result.get("snippet") or serp_result.get("description", "")
        domain = extract_domain(url)
        haystack = f"{url} {title} {description}".lower()
        source_type = getattr(query, "source_type", "") or ""
        sig_key = query.signal_type.value if hasattr(query.signal_type, "value") else str(query.signal_type)

        if sig_key == "pricing_pressure" or source_type == "pricing_pages":
            if _domain_in_family(domain, CLOUD_PRICING_DOMAINS):
                return "pricing_cloud_provider_accept"
            if _domain_in_family(domain, COMPANY_PRODUCT_DOMAINS):
                return "pricing_playbook_accept"
            if _domain_in_family(domain, OEM_DISTRIBUTOR_DOMAINS):
                return "pricing_oem_distributor_accept"
            if _domain_in_family(domain, PRICING_CONTEXT_DOMAINS):
                return "pricing_playbook_accept"
            if any(term in haystack for term in PRICING_HARDWARE_TERMS):
                return "pricing_playbook_accept"
        return "accepted"

    def should_fetch(
        self,
        serp_result: dict,
        query: "SearchQuery",
        min_score: float = 0.3,
    ) -> bool:
        return self.rejection_reason(serp_result, query, min_score=min_score) is None

    def record_http_result(self, url: str, status_code: int) -> None:
        self.error_memory.record_failure(url, status_code)


# ── Standalone tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from app.schemas.models import SearchQuery, SignalType
    from app.utils.helpers import generate_uuid

    P = "✅ PASS"
    F = "❌ FAIL"

    def _q(entity: str, sig: SignalType, source_type: str = "serp_news", text: str = "") -> SearchQuery:
        return SearchQuery(
            query_id=generate_uuid()[:12],
            query_text=text or f"{entity} {sig.value}",
            target_entity=entity,
            signal_type=sig,
            source_type=source_type,
            priority=1,
            expected_source_tier=3,
        )

    # ── Test 1: search-engine URL rejection ───────────────────────────────────
    print("\n── Test 1: search-engine URL rejection ─────────────────────")
    scorer = URLScorer()
    q = _q("Nvidia", SignalType.investor_signal)

    cases = [
        ("https://www.google.com/search?q=nvidia+earnings",        True,  "Google SERP"),
        ("https://www.bing.com/search?q=nvidia+earnings",          True,  "Bing SERP"),
        ("https://www.google.com/url?sa=t&url=https://ir.nvidia.com", True, "Google redirect"),
        ("https://webcache.googleusercontent.com/search?q=cache:ir.nvidia.com", True, "Google webcache"),
        ("https://ir.nvidia.com/news/q1-2026",                     False, "Nvidia IR (not search engine)"),
        ("https://reuters.com/technology/nvidia-earnings-2025",    False, "Reuters article"),
    ]
    for url, expect_blocked, label in cases:
        blocked = _is_search_engine_result_url(url)
        ok = blocked == expect_blocked
        print(f"  {P if ok else F}  {label}: blocked={blocked}")
        assert ok, f"Expected blocked={expect_blocked} for {url}"

    # ── Test 2: entity matching — short tickers ────────────────────────────────
    print("\n── Test 2: entity matching — short tickers (word boundary) ─")
    q_mu = _q("Micron", SignalType.investor_signal)
    q_amd = _q("AMD", SignalType.investor_signal)

    # MU should NOT match these snippets
    bad_mu  = {"url": "https://reuters.com/x", "title": "communications investment", "snippet": "mutual fund activity"}
    good_mu = {"url": "https://investor.micron.com/x", "title": "Micron (MU) earnings", "snippet": "MU revenue Q1 2026"}
    bad_amd = {"url": "https://reuters.com/x", "title": "amended filing", "snippet": "command decision announced"}

    score_bad_mu  = URLScorer().score(bad_mu, q_mu)
    score_good_mu = URLScorer().score(good_mu, q_mu)
    score_bad_amd = URLScorer().score(bad_amd, q_amd)

    print(f"  'mutual fund activity' vs Micron query: score={score_bad_mu}  ({P if score_bad_mu == 0.0 else F}  should be 0.0)")
    print(f"  'Micron (MU) earnings' vs Micron query: score={score_good_mu}  ({P if score_good_mu > 0 else F}  should be >0)")
    print(f"  'amended filing' vs AMD query: score={score_bad_amd}  ({P if score_bad_amd == 0.0 else F}  should be 0.0)")

    assert score_bad_mu  == 0.0, f"'mu' should NOT match 'mutual fund', got {score_bad_mu}"
    assert score_good_mu  > 0.0, f"'MU' ticker should match Micron query, got {score_good_mu}"
    assert score_bad_amd == 0.0, f"'amd' should NOT match 'amended', got {score_bad_amd}"

    # ── Test 3: site: constraint enforcement ──────────────────────────────────
    print("\n── Test 3: site: constraint enforcement ────────────────────")
    q_site = _q("Nvidia", SignalType.investor_signal, text="Nvidia 10-K annual report site:sec.gov")

    in_site  = {"url": "https://sec.gov/Archives/edgar/data/nvidia.htm",
                "title": "Nvidia 10-K", "snippet": "Nvidia annual report SEC filing"}
    off_site = {"url": "https://reuters.com/nvidia-annual-report",
                "title": "Nvidia 10-K filing summary", "snippet": "Nvidia investor annual report"}

    s_in  = URLScorer().score(in_site,  q_site)
    s_off = URLScorer().score(off_site, q_site)
    print(f"  sec.gov (in site: constraint): score={s_in}  ({P if s_in > 0 else F})")
    print(f"  reuters.com (off site: constraint): score={s_off}  ({P if s_off == 0.0 else F})")
    assert s_in  > 0.0, f"sec.gov should pass site: constraint, got {s_in}"
    assert s_off == 0.0, f"reuters.com should fail site: constraint, got {s_off}"

    # ── Test 4: ir_pages source-type hard rule ────────────────────────────────
    print("\n── Test 4: ir_pages source-type — Tier-1 only ──────────────")
    q_ir = _q("Nvidia", SignalType.investor_signal, source_type="ir_pages")

    ir_tier1   = {"url": "https://investor.nvidia.com/sec-filings/annual-reports",
                  "title": "Nvidia Annual Reports", "snippet": "Nvidia investor relations annual report"}
    ir_tier2   = {"url": "https://reuters.com/nvidia-sec-annual-filing",
                  "title": "Nvidia annual SEC filing", "snippet": "Nvidia investor filing revenue"}
    ir_sec     = {"url": "https://sec.gov/cgi-bin/browse-edgar?CIK=nvda",
                  "title": "Nvidia SEC EDGAR", "snippet": "Nvidia investor filings SEC"}

    s_t1  = URLScorer().score(ir_tier1, q_ir)
    s_t2  = URLScorer().score(ir_tier2, q_ir)
    s_sec = URLScorer().score(ir_sec,   q_ir)
    print(f"  ir.nvidia.com (Tier 1): score={s_t1}  ({P if s_t1 > 0 else F}  should pass)")
    print(f"  reuters.com (Tier 2): score={s_t2}  ({P if s_t2 == 0.0 else F}  should be blocked)")
    print(f"  sec.gov (Tier 1): score={s_sec}  ({P if s_sec > 0 else F}  should pass)")
    assert s_t1  > 0.0, f"ir.nvidia.com should pass ir_pages check, got {s_t1}"
    assert s_t2  == 0.0, f"reuters.com should be blocked for ir_pages, got {s_t2}"
    assert s_sec > 0.0, f"sec.gov should pass ir_pages check, got {s_sec}"

    # ── Test 5: job_pages soft affinity ───────────────────────────────────────
    print("\n── Test 5: job_pages soft affinity ─────────────────────────")
    q_jobs = _q("Intel", SignalType.hiring_momentum, source_type="job_pages")

    jobs_career = {"url": "https://jobs.intel.com/software-engineer-ai",
                   "title": "Intel AI Software Engineer jobs", "snippet": "Intel hiring engineer talent"}
    jobs_news   = {"url": "https://techcrunch.com/intel-layoffs-2025",
                   "title": "Intel layoffs 2025", "snippet": "Intel workforce headcount reduction"}

    s_career = URLScorer().score(jobs_career, q_jobs)
    s_news   = URLScorer().score(jobs_news,   q_jobs)
    print(f"  jobs.intel.com (career domain): score={s_career}")
    print(f"  techcrunch (non-career domain, 0.5×): score={s_news}")
    assert s_career > s_news, f"Career domain should score higher than non-career domain"
    # Career domain should be above threshold; non-career 0.5× may or may not pass
    assert s_career >= 0.3, f"Career domain should be fetchable, got {s_career}"
    print(f"  {P}  career domain scores higher than non-career domain")

    # ── Test 6: HTTP error memory (unchanged, regression) ────────────────────
    print("\n── Test 6: HTTP error memory ────────────────────────────────")
    sc6 = URLScorer()
    q6 = _q("Nvidia", SignalType.investor_signal)
    sc6.record_http_result("https://seekingalpha.com/x", 403)
    sc6.record_http_result("https://seekingalpha.com/y", 403)
    r6 = {"url": "https://seekingalpha.com/nvidia-earnings", "title": "Nvidia earnings", "snippet": "Nvidia investor earnings revenue"}
    fetch6 = sc6.should_fetch(r6, q6)
    print(f"  seekingalpha after 2x 403: should_fetch={fetch6}  ({P if not fetch6 else F})")
    assert not fetch6, "seekingalpha should be blocked after 2 permanent failures"

    # 429 (retryable) should NOT block
    sc7 = URLScorer()
    sc7.record_http_result("https://seekingalpha.com/x", 429)
    sc7.record_http_result("https://seekingalpha.com/y", 429)
    fetch7 = sc7.should_fetch(r6, q6)
    print(f"  seekingalpha after 2x 429 (retryable): should_fetch={fetch7}  ({P if fetch7 else F})")
    assert fetch7, "429 should not block domain"

    print("\n✅ All tests passed")
