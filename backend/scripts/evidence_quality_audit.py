"""
Evidence Quality & Signal Semantics Audit — Sprint 3
-----------------------------------------------------
Reads from the SQLite DB and existing artifact JSON files.
Does NOT re-run the pipeline or make any BrightData calls.

Usage:
    python backend/scripts/evidence_quality_audit.py
    python backend/scripts/evidence_quality_audit.py --report-id report_dfd5e69a3a42
    python backend/scripts/evidence_quality_audit.py \
        --report-id report_dfd5e69a3a42 \
        --artifact-dir pipeline_audit_artifacts/demo_track2_20260526T040110Z

Outputs under pipeline_audit_artifacts/evidence_quality_<YYYYMMDDTHHMMSSZ>/:
    evidence_quality_summary.json
    signal_semantics_audit.json
    pricing_pressure_semantics_audit.json
    suspicious_claims.json
    source_tier_quality_audit.json
    evidence_quality_run.log
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# ── Path setup ─────────────────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "backend"))

from dotenv import load_dotenv
load_dotenv(_REPO / "backend" / ".env")

from app.schemas.models import FactObject, VerifiedClaim, MarketPulseReport

# ── Config ─────────────────────────────────────────────────────────────────────

DB_PATH = _REPO / "backend" / "data" / "pulselens.db"
DEFAULT_REPORT_ID = "report_dfd5e69a3a42"
DEFAULT_ARTIFACT_DIR = _REPO / "pipeline_audit_artifacts" / "demo_track2_20260526T040110Z"

# ── Pricing pressure semantic classification ───────────────────────────────────

# Patterns that indicate a STRONG pricing signal
_STRONG_PRICE_PATTERNS = [
    r"\$[\d,]+\.?\d*\s*(?:per\s+hour|/\s*hr|/\s*hour|/\s*month|/\s*year)?",  # $X.XX/hr
    r"[\d,]+\s*(?:dollars?|usd)",
    r"\d+\.?\d*\s*%\s*(?:increase|decrease|drop|decline|rise|higher|lower|more|less)",  # %change
    r"(?:discount|discounted|promo|promotional)",
    r"(?:on.demand|spot\s+price|reserved\s+price|rental\s+rate|hourly\s+rate)",
    r"(?:cost\s+per\s+hour|cost\s+per\s+month|cost\s+per\s+year)",
    r"(?:lead\s+time).{0,60}(?:availability|weeks?|months?|days?)",
    r"(?:oversupply|undersupply|supply\s+glut|supply\s+tightness).{0,60}(?:price|cost|rate)",
    r"(?:margin\s+pressure|margin\s+compression|gross\s+margin).{0,60}(?:price|pricing)",
    r"(?:price\s+comparison|pricing\s+comparison|vs\.?\s+competitor)",
    r"starting\s+price\s+of\s+\$",  # "starting price of $X"
    r"price\s+of\s+\$",
    r"priced\s+at\s+\$",
    r"available\s+for\s+\$",
    r"costs?\s+\$",
]

# Patterns that indicate the signal is WEAK (no actual price data)
_WEAK_PRICE_PATTERNS = [
    r"(?:index|tracker|benchmark)\s+(?:launched|announced|introduced|released)",
    r"(?:launched|announced).{0,40}(?:index|tracker|benchmark)",
    r"available\s+with\s+a\s+starting\s+price(?!\s+of\s+\$)",  # "available with a starting price" but no $
    r"prices?\s+(?:may|could|might|will|are\s+expected\s+to)",   # speculative
    r"pricing\s+(?:information|details|info)\s+(?:available|provided|listed)",
]

# Patterns that indicate a fact is MISCLASSIFIED (should be a different signal type)
_MISCLASSIFIED_AS_PRICING = [
    (r"hbm.{0,60}(?:price|cost|shortage)", "should be supplier_risk: HBM shortage/cost"),
    (r"memory.{0,60}(?:price|cost|shortage).{0,60}(?:ai|gpu|accelerator)", "should be supplier_risk: memory shortage causing price pressure"),
    (r"(?:shrinking|reducing|squeezing).{0,60}supply.{0,60}(?:pc|phone|consumer)", "should be supplier_risk: supply diversion"),
    (r"export\s+(?:control|restriction|ban).{0,60}(?:price|cost|revenue)", "should be investor_signal: export restriction revenue impact"),
]


def classify_pricing_fact(fact: dict) -> dict:
    """
    Classify a pricing_pressure fact as strong / weak / misclassified / insufficient_evidence.
    Returns dict with label, reason, matched_patterns.
    """
    text = (fact.get("claim", "") + " " + fact.get("evidence_quote", "")).lower()

    # Check misclassification first
    for pattern, reason in _MISCLASSIFIED_AS_PRICING:
        if re.search(pattern, text, re.IGNORECASE):
            return {
                "label": "misclassified_pricing_signal",
                "reason": reason,
                "matched_pattern": pattern,
            }

    # Check strong signals
    matched_strong = []
    for pat in _STRONG_PRICE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            matched_strong.append(pat)
    if matched_strong:
        return {
            "label": "strong_pricing_signal",
            "reason": "Contains explicit price/rate/change data",
            "matched_patterns": matched_strong[:3],  # top 3
        }

    # Check weak signals
    matched_weak = []
    for pat in _WEAK_PRICE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            matched_weak.append(pat)
    if matched_weak:
        return {
            "label": "weak_pricing_signal",
            "reason": "Pricing-adjacent but no explicit price/rate data",
            "matched_patterns": matched_weak,
        }

    return {
        "label": "insufficient_evidence",
        "reason": "Cannot determine pricing relevance from claim or evidence quote",
        "matched_patterns": [],
    }


# ── Signal sanity-check vocabularies ──────────────────────────────────────────

SIGNAL_SANITY_TERMS: dict[str, list[str]] = {
    "investor_signal": [
        "earnings", "revenue", "margin", "guidance", "filing", "sec", "13f",
        "institutional", "analyst", "upgrade", "downgrade", "eps", "operating income",
        "net income", "stockholder", "investor", "quarterly", "annual", "fiscal",
    ],
    "product_launch": [
        "launch", "announced", "available", "release", "new", "product",
        "accelerator", "instance", "platform", "hardware", "sku", "deployment",
        "general availability", "ga", "mi300", "h100", "b200", "blackwell",
    ],
    "supplier_risk": [
        "shortage", "supply", "dependency", "hbm", "cowos", "foundry", "tsmc",
        "samsung", "memory", "logistics", "export", "constraint", "bottleneck",
        "risk", "disruption",
    ],
    "pricing_pressure": [
        "price", "pricing", "cost", "rental", "discount", "rate", "$/",
        "per hour", "per month", "lead time", "availability", "margin",
    ],
    "strategic_messaging": [
        "strategy", "investment", "partnership", "roadmap", "ceo", "cfo",
        "executive", "guidance", "outlook", "capex", "ecosystem", "vision",
    ],
    "news_sentiment": [
        "news", "report", "coverage", "analyst", "market", "sentiment",
        "reaction", "media",
    ],
    "hiring_momentum": [
        "hiring", "jobs", "headcount", "talent", "recruit", "workforce",
        "layoff", "career", "engineer", "position",
    ],
}

# ── Source domain classification ───────────────────────────────────────────────

_AUTHORITATIVE_DOMAINS = {
    "sec.gov", "ir.amd.com", "ir.supermicro.com", "investor.nvidia.com",
    "ir.nvidia.com", "investors.amd.com",
}
_ACCEPTABLE_DOMAINS = {
    "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
    "tomshardware.com", "servethehome.com", "theregister.com", "anandtech.com",
    "amd.com", "nvidia.com", "supermicro.com", "intel.com",
    "cloud.google.com", "aws.amazon.com", "azure.microsoft.com",
    "coreweave.com", "oracle.com", "runpod.io", "lambdalabs.com",
    "dell.com", "hpe.com",
}
_WEAK_BUT_USABLE_DOMAINS = {
    "semianalysis.com", "newsletter.semianalysis.com",
    "thinkmate.com", "insight.com", "cdw.com",
    "techcrunch.com", "cnbc.com", "fortune.com",
    "enkiai.com",
}
_SUSPICIOUS_DOMAINS = {
    "instagram.com", "facebook.com", "twitter.com", "x.com",
    "linkedin.com", "reddit.com", "youtube.com",
}
_REJECT_NEXT_TIME_CANDIDATES = {
    "ceva-ip.com",  # CEVA Semiconductor — not in demo scope, accepted via fallback
}


def classify_domain(domain: str) -> str:
    d = domain.lower().lstrip("www.")
    if d in _AUTHORITATIVE_DOMAINS or any(d.endswith("." + a) for a in _AUTHORITATIVE_DOMAINS):
        return "authoritative"
    if d in _ACCEPTABLE_DOMAINS or any(d.endswith("." + a) for a in _ACCEPTABLE_DOMAINS):
        return "acceptable"
    if d in _WEAK_BUT_USABLE_DOMAINS or any(d.endswith("." + a) for a in _WEAK_BUT_USABLE_DOMAINS):
        return "weak_but_usable"
    if d in _SUSPICIOUS_DOMAINS or any(d.endswith("." + a) for a in _SUSPICIOUS_DOMAINS):
        return "suspicious_or_low_signal"
    if d in _REJECT_NEXT_TIME_CANDIDATES:
        return "reject_next_time_candidate"
    return "unknown"


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return url


# ── Suspicious claim patterns ──────────────────────────────────────────────────

_SUSPICIOUS_CLAIM_PATTERNS = [
    (r"provides?\s+investor\s+relations\s+information", "IR page metadata extracted as fact"),
    (r"(?:available|accessible)\s+(?:on|at|from)\s+(?:the\s+)?(?:website|page|portal)", "website navigation extracted as fact"),
    (r"news\s+from\s+", "claim starts with 'News from' (banned by Agent 3 rules)"),
    (r"^according\s+to", "claim starts with 'According to' (banned by Agent 3 rules)"),
    (r"information\s+(?:is\s+)?(?:available|provided|listed|displayed)", "generic page description extracted as fact"),
    (r"(?:financial\s+results|sec\s+filings|earnings\s+webcasts)\s+(?:are|can\s+be)\s+found", "IR portal navigation as fact"),
]


def is_suspicious_claim(claim: str) -> tuple[bool, str]:
    for pattern, reason in _SUSPICIOUS_CLAIM_PATTERNS:
        if re.search(pattern, claim, re.IGNORECASE):
            return True, reason
    return False, ""


# ── DB helpers ─────────────────────────────────────────────────────────────────

def load_facts_from_db(report_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT payload FROM facts WHERE report_id = ?", (report_id,)
        ).fetchall()
    return [json.loads(r["payload"]) for r in rows]


def load_claims_from_db(report_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT payload FROM claims WHERE report_id = ?", (report_id,)
        ).fetchall()
    return [json.loads(r["payload"]) for r in rows]


def load_report_from_db(report_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT payload FROM reports WHERE report_id = ?", (report_id,)
        ).fetchone()
    return json.loads(row["payload"]) if row else None


# ── Audit functions ────────────────────────────────────────────────────────────

def audit_pricing_pressure(facts: list[dict]) -> dict:
    pp_facts = [f for f in facts if f.get("signal_type") == "pricing_pressure"]
    classified = []
    for f in pp_facts:
        cls = classify_pricing_fact(f)
        classified.append({
            "fact_id": f.get("fact_id"),
            "entity": f.get("entity"),
            "claim": f.get("claim"),
            "evidence_quote": f.get("evidence_quote", "")[:120],
            "source_url": f.get("source_url"),
            "source_tier": f.get("source_tier"),
            "confidence": f.get("confidence"),
            "sentiment": f.get("sentiment"),
            **cls,
        })

    label_counts = defaultdict(int)
    for c in classified:
        label_counts[c["label"]] += 1

    return {
        "total_pricing_facts": len(pp_facts),
        "strong_pricing_signal_count": label_counts["strong_pricing_signal"],
        "weak_pricing_signal_count": label_counts["weak_pricing_signal"],
        "misclassified_pricing_signal_count": label_counts["misclassified_pricing_signal"],
        "insufficient_evidence_count": label_counts["insufficient_evidence"],
        "strong_fraction": label_counts["strong_pricing_signal"] / max(len(pp_facts), 1),
        "verdict": (
            "WEAK — fewer than 50% of pricing facts are strong signals"
            if label_counts["strong_pricing_signal"] < len(pp_facts) / 2
            else "ACCEPTABLE — majority of pricing facts are strong signals"
        ),
        "facts": classified,
    }


def audit_signal_semantics(facts: list[dict], claims: list[dict]) -> dict:
    signals = [s.value for s in __import__("app.schemas.models", fromlist=["SignalType"]).SignalType]
    result = {}

    claims_by_signal: dict[str, list[dict]] = defaultdict(list)
    for c in claims:
        claims_by_signal[c.get("signal_type", "")].append(c)

    for sig in signals:
        sig_facts = [f for f in facts if f.get("signal_type") == sig]
        sig_claims = claims_by_signal.get(sig, [])
        domains = [extract_domain(f.get("source_url", "")) for f in sig_facts]
        domain_counts: dict[str, int] = defaultdict(int)
        for d in domains:
            domain_counts[d] += 1
        top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        avg_conf = (
            sum(f.get("confidence", 0.0) for f in sig_facts) / len(sig_facts)
            if sig_facts else 0.0
        )

        # Sanity-check vocabulary
        vocab = SIGNAL_SANITY_TERMS.get(sig, [])
        suspicious = []
        for f in sig_facts:
            text = (f.get("claim", "") + " " + f.get("evidence_quote", "")).lower()
            vocab_hits = sum(1 for v in vocab if v in text)
            flagged, flag_reason = is_suspicious_claim(f.get("claim", ""))
            if flagged or vocab_hits == 0:
                suspicious.append({
                    "fact_id": f.get("fact_id"),
                    "entity": f.get("entity"),
                    "claim": f.get("claim"),
                    "source_url": f.get("source_url"),
                    "reason": flag_reason if flagged else f"zero vocab matches from {vocab[:4]}",
                })

        result[sig] = {
            "fact_count": len(sig_facts),
            "verified_claim_count": len(sig_claims),
            "average_confidence": round(avg_conf, 3),
            "source_count": len(set(domains)),
            "top_domains": [{"domain": d, "fact_count": n} for d, n in top_domains],
            "suspicious_claim_count": len(suspicious),
            "suspicious_claims": suspicious,
        }

    return result


def audit_source_quality(facts: list[dict]) -> dict:
    domain_info: dict[str, dict] = {}
    for f in facts:
        domain = extract_domain(f.get("source_url", ""))
        if domain not in domain_info:
            domain_info[domain] = {
                "domain": domain,
                "quality_rating": classify_domain(domain),
                "fact_count": 0,
                "signal_types": set(),
                "tiers": set(),
                "entities": set(),
                "sample_urls": set(),
            }
        domain_info[domain]["fact_count"] += 1
        domain_info[domain]["signal_types"].add(f.get("signal_type", ""))
        domain_info[domain]["tiers"].add(f.get("source_tier"))
        domain_info[domain]["entities"].add(f.get("entity", ""))
        domain_info[domain]["sample_urls"].add(f.get("source_url", ""))

    # Convert sets to lists for JSON serialization
    for d in domain_info.values():
        d["signal_types"] = sorted(d["signal_types"])
        d["tiers"] = sorted(d["tiers"])
        d["entities"] = sorted(d["entities"])
        d["sample_urls"] = sorted(d["sample_urls"])[:2]

    rating_counts: dict[str, int] = defaultdict(int)
    for d in domain_info.values():
        rating_counts[d["quality_rating"]] += 1

    return {
        "total_domains": len(domain_info),
        "rating_summary": dict(rating_counts),
        "suspicious_or_low_signal_count": rating_counts.get("suspicious_or_low_signal", 0),
        "reject_next_time_candidate_count": rating_counts.get("reject_next_time_candidate", 0),
        "domains": sorted(domain_info.values(), key=lambda x: x["fact_count"], reverse=True),
    }


def audit_suspicious_claims(facts: list[dict]) -> list[dict]:
    flagged = []
    for f in facts:
        claim = f.get("claim", "")
        found, reason = is_suspicious_claim(claim)
        if found:
            flagged.append({
                "fact_id": f.get("fact_id"),
                "entity": f.get("entity"),
                "signal_type": f.get("signal_type"),
                "claim": claim,
                "source_url": f.get("source_url"),
                "source_tier": f.get("source_tier"),
                "confidence": f.get("confidence"),
                "suspicious_reason": reason,
            })
    return flagged


def build_summary(
    facts: list[dict],
    claims: list[dict],
    pricing_audit: dict,
    signal_audit: dict,
    source_audit: dict,
    suspicious: list[dict],
    report: dict | None,
    report_id: str,
) -> dict:
    total_facts = len(facts)
    total_claims = len(claims)
    avg_conf = sum(f.get("confidence", 0.0) for f in facts) / max(total_facts, 1)

    quality_status = report.get("quality_status", "UNKNOWN") if report else "UNKNOWN"
    pulse_score = report.get("pulse_score") if report else None

    return {
        "report_id": report_id,
        "quality_status": quality_status,
        "pulse_score": pulse_score,
        "total_facts": total_facts,
        "total_verified_claims": total_claims,
        "average_confidence": round(avg_conf, 3),
        "total_source_domains": source_audit["total_domains"],
        "suspicious_claim_count": len(suspicious),
        "weak_source_count": source_audit["rating_summary"].get("weak_but_usable", 0),
        "suspicious_or_low_signal_source_count": source_audit["rating_summary"].get("suspicious_or_low_signal", 0),
        "reject_next_time_candidate_count": source_audit["rating_summary"].get("reject_next_time_candidate", 0),
        "strong_pricing_signal_count": pricing_audit["strong_pricing_signal_count"],
        "weak_pricing_signal_count": pricing_audit["weak_pricing_signal_count"],
        "misclassified_signal_count": pricing_audit["misclassified_pricing_signal_count"],
        "pricing_verdict": pricing_audit["verdict"],
        "signal_coverage": {
            sig: data["fact_count"] for sig, data in signal_audit.items()
        },
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence Quality Audit — Sprint 3")
    parser.add_argument("--report-id", default=DEFAULT_REPORT_ID)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = _REPO / "pipeline_audit_artifacts" / f"evidence_quality_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = out_dir / "evidence_quality_run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path),
        ],
    )
    log = logging.getLogger("evidence_quality_audit")

    log.info("=== Evidence Quality Audit — Sprint 3 ===")
    log.info("report_id: %s", args.report_id)
    log.info("artifact_dir: %s", args.artifact_dir)
    log.info("output_dir: %s", out_dir)

    # ── Load data ──────────────────────────────────────────────────────────────
    log.info("Loading facts from DB...")
    facts = load_facts_from_db(args.report_id)
    log.info("Loaded %d facts", len(facts))

    log.info("Loading verified claims from DB...")
    claims = load_claims_from_db(args.report_id)
    log.info("Loaded %d claims", len(claims))

    log.info("Loading report from DB...")
    report = load_report_from_db(args.report_id)
    if report is None:
        log.error("Report %s not found in DB — check report_id", args.report_id)
        sys.exit(1)
    log.info("Report loaded: quality_status=%s pulse_score=%s",
             report.get("quality_status"), report.get("pulse_score"))

    # ── Pricing pressure audit ─────────────────────────────────────────────────
    log.info("--- Pricing pressure semantic audit ---")
    pricing_audit = audit_pricing_pressure(facts)
    log.info(
        "pricing_pressure: %d facts | strong=%d weak=%d misclassified=%d insufficient=%d",
        pricing_audit["total_pricing_facts"],
        pricing_audit["strong_pricing_signal_count"],
        pricing_audit["weak_pricing_signal_count"],
        pricing_audit["misclassified_pricing_signal_count"],
        pricing_audit["insufficient_evidence_count"],
    )
    log.info("Pricing verdict: %s", pricing_audit["verdict"])
    for pf in pricing_audit["facts"]:
        log.info(
            "  [%s] conf=%.2f label=%s claim=%s",
            pf["entity"], pf.get("confidence", 0), pf["label"], pf["claim"][:80]
        )

    (out_dir / "pricing_pressure_semantics_audit.json").write_text(
        json.dumps(pricing_audit, indent=2, ensure_ascii=False)
    )

    # ── Per-signal semantics audit ─────────────────────────────────────────────
    log.info("--- Per-signal semantics audit ---")
    signal_audit = audit_signal_semantics(facts, claims)
    for sig, data in signal_audit.items():
        log.info(
            "  %-22s facts=%2d claims=%2d avg_conf=%.2f sources=%2d suspicious=%d",
            sig, data["fact_count"], data["verified_claim_count"],
            data["average_confidence"], data["source_count"], data["suspicious_claim_count"],
        )

    (out_dir / "signal_semantics_audit.json").write_text(
        json.dumps(signal_audit, indent=2, ensure_ascii=False)
    )

    # ── Source quality audit ───────────────────────────────────────────────────
    log.info("--- Source quality audit ---")
    source_audit = audit_source_quality(facts)
    log.info(
        "Domains: %d total | %s",
        source_audit["total_domains"],
        " | ".join(f"{k}={v}" for k, v in sorted(source_audit["rating_summary"].items())),
    )
    for d in source_audit["domains"]:
        log.info(
            "  %-40s [%-30s] facts=%d tiers=%s",
            d["domain"], d["quality_rating"], d["fact_count"], d["tiers"],
        )

    (out_dir / "source_tier_quality_audit.json").write_text(
        json.dumps(source_audit, indent=2, ensure_ascii=False)
    )

    # ── Suspicious claims ──────────────────────────────────────────────────────
    log.info("--- Suspicious claim patterns ---")
    suspicious = audit_suspicious_claims(facts)
    log.info("Suspicious claims found: %d", len(suspicious))
    for sc in suspicious:
        log.info(
            "  [%s|%s] reason=%s claim=%s",
            sc["entity"], sc["signal_type"], sc["suspicious_reason"], sc["claim"][:80],
        )

    (out_dir / "suspicious_claims.json").write_text(
        json.dumps(suspicious, indent=2, ensure_ascii=False)
    )

    # ── Summary ────────────────────────────────────────────────────────────────
    summary = build_summary(
        facts, claims, pricing_audit, signal_audit, source_audit, suspicious, report, args.report_id
    )
    (out_dir / "evidence_quality_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )

    log.info("=== SUMMARY ===")
    log.info("total_facts: %d", summary["total_facts"])
    log.info("total_verified_claims: %d", summary["total_verified_claims"])
    log.info("average_confidence: %.3f", summary["average_confidence"])
    log.info("suspicious_claims: %d", summary["suspicious_claim_count"])
    log.info("strong_pricing: %d  weak_pricing: %d  misclassified: %d",
             summary["strong_pricing_signal_count"],
             summary["weak_pricing_signal_count"],
             summary["misclassified_signal_count"])
    log.info("Output: %s", out_dir)
    print(f"\nAudit complete. Results: {out_dir}")


if __name__ == "__main__":
    main()
