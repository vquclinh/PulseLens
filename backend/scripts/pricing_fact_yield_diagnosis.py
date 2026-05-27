"""
Offline pricing extraction yield diagnosis.

Correlates accepted pricing URLs (from web_collection_audit.json) against DB facts
to identify which documents had price signal but yielded zero extraction facts.

No live API calls. Reads artifact folder + SQLite DB only.

Usage (run from backend/):
    python scripts/pricing_fact_yield_diagnosis.py \\
        --artifact-dir ../pipeline_audit_artifacts/demo_track2_20260527T074938Z \\
        --report-id report_1df9ca6a1014
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Constants matching agent2_web_workers.py
# ---------------------------------------------------------------------------

_PRICE_PATTERNS = re.compile(
    r"\$[\d,]+(?:\.\d+)?(?:/hr|/hour|/mo|/month)?\b"
    r"|\b[\d,]+\s*(?:USD|EUR|cents?)\b"
    r"|\bper.{0,20}hour\b"
    r"|\bper.{0,20}month\b",
    re.IGNORECASE,
)

# Domains where entity mismatch is likely (not in KNOWN_ENTITIES of node_validate_and_split.py)
_ENTITY_MISMATCH_DOMAINS = frozenset({
    "coreweave.com",
    "runpod.io",
    "lambdalabs.com",
    "lambda.ai",
    "cloud.google.com",
    "oracle.com",
    "aws.amazon.com",
    "azure.microsoft.com",
})

# Agent 3 content truncation threshold
_AGENT3_CONTENT_LIMIT = 8000

# High-pattern threshold for "should have yielded facts"
_HIGH_PATTERN_THRESHOLD = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        parts = host.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else host
    except Exception:
        return ""


def count_pricing_patterns(content: str) -> int:
    return len(_PRICE_PATTERNS.findall(content))


def classify_bottleneck(content_length: int, price_pattern_count: int, domain: str) -> str:
    labels: list[str] = []
    if content_length < 1500:
        labels.append("thin_content")
        return "+".join(labels)  # thin content dominates; skip other checks
    if content_length > _AGENT3_CONTENT_LIMIT:
        labels.append("truncation")
    if price_pattern_count >= _HIGH_PATTERN_THRESHOLD:
        labels.append("tabular_format")
    if domain in _ENTITY_MISMATCH_DOMAINS:
        labels.append("entity_mismatch")
    return "+".join(labels) if labels else "unknown"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_pricing_urls_from_audit(artifact_dir: Path) -> dict[str, dict]:
    """Return {url → {url, content_length, price_pattern_count, escalation_reason, final_method}}."""
    audit_path = artifact_dir / "web_collection_audit.json"
    if not audit_path.exists():
        print(f"[WARN] web_collection_audit.json not found at {audit_path}", file=sys.stderr)
        return {}

    data = json.loads(audit_path.read_text())
    url_info: dict[str, dict] = {}

    for query in data.get("queries", []):
        if query.get("source_type") != "pricing_pages":
            continue

        # Collect accepted URLs for this query
        for acc in query.get("accepted_urls", []):
            url = acc["url"]
            if url not in url_info:
                url_info[url] = {
                    "url": url,
                    "domain": extract_domain(url),
                    "content_length": 0,
                    "price_pattern_count": 0,
                    "escalation_reason": "no_telemetry",
                    "final_method": "normal",
                    "escalated_to_browser": False,
                    "browser_failed": False,
                }

        # Overlay escalation telemetry (richer than accepted_urls)
        for esc in query.get("pricing_escalations", []):
            url = esc["url"]
            final_method = esc.get("final_scrape_method", "normal")
            if final_method == "browser" and esc.get("browser_content_length", 0) > 0:
                content_length = esc["browser_content_length"]
                price_count = esc.get("browser_price_pattern_count", 0)
            else:
                content_length = esc.get("normal_scrape_content_length", 0)
                price_count = esc.get("normal_scrape_price_pattern_count", 0)

            browser_failed = (
                esc.get("escalated_to_browser", False)
                and esc.get("browser_error") is not None
            )

            if url not in url_info:
                url_info[url] = {
                    "url": url,
                    "domain": extract_domain(url),
                    "content_length": 0,
                    "price_pattern_count": 0,
                    "escalation_reason": "no_telemetry",
                    "final_method": "normal",
                    "escalated_to_browser": False,
                    "browser_failed": False,
                }
            url_info[url]["content_length"] = content_length
            url_info[url]["price_pattern_count"] = price_count
            url_info[url]["escalation_reason"] = esc.get("pricing_escalation_reason", "")
            url_info[url]["final_method"] = final_method
            url_info[url]["escalated_to_browser"] = esc.get("escalated_to_browser", False)
            url_info[url]["browser_failed"] = browser_failed

    return url_info


def load_pricing_facts_from_db(db_path: Path, report_id: str) -> dict[str, int]:
    """Return {source_url → fact_count} for pricing_pressure facts in this report."""
    if not db_path.exists():
        print(f"[WARN] DB not found at {db_path}", file=sys.stderr)
        return {}

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT payload FROM facts WHERE report_id = ?",
            (report_id,),
        )
        url_to_count: dict[str, int] = defaultdict(int)
        for (payload_json,) in cur.fetchall():
            try:
                payload = json.loads(payload_json)
            except json.JSONDecodeError:
                continue
            if payload.get("signal_type") == "pricing_pressure":
                source = payload.get("source_url") or ""
                if source:
                    url_to_count[source] += 1
        return dict(url_to_count)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def run_diagnosis(
    artifact_dir: Path,
    report_id: str,
    db_path: Path,
) -> None:
    print(f"\nPricing extraction yield diagnosis")
    print(f"  artifact_dir : {artifact_dir}")
    print(f"  report_id    : {report_id}")
    print(f"  db           : {db_path}")
    print()

    url_info = load_pricing_urls_from_audit(artifact_dir)
    fact_counts = load_pricing_facts_from_db(db_path, report_id)

    if not url_info:
        print("No pricing_pages URLs found in web_collection_audit.json. Exiting.")
        return

    # Build per-doc yield records
    doc_records: list[dict] = []
    for url, info in url_info.items():
        fact_count = fact_counts.get(url, 0)
        yield_status = "has_facts" if fact_count > 0 else "zero_yield"
        bottleneck = (
            classify_bottleneck(info["content_length"], info["price_pattern_count"], info["domain"])
            if yield_status == "zero_yield"
            else "n/a"
        )
        doc_records.append({
            "url": url,
            "domain": info["domain"],
            "content_length": info["content_length"],
            "price_pattern_count": info["price_pattern_count"],
            "fact_count": fact_count,
            "yield_status": yield_status,
            "likely_bottleneck": bottleneck,
            "escalation_reason": info["escalation_reason"],
            "final_method": info["final_method"],
            "escalated_to_browser": info["escalated_to_browser"],
            "browser_failed": info["browser_failed"],
        })

    doc_records.sort(key=lambda d: -d["price_pattern_count"])

    # High-pattern zero-fact subset (most actionable)
    high_pattern_zero = [
        d for d in doc_records
        if d["price_pattern_count"] >= _HIGH_PATTERN_THRESHOLD and d["fact_count"] == 0
    ]

    # Bottleneck breakdown (zero-fact docs only)
    zero_fact_docs = [d for d in doc_records if d["fact_count"] == 0]
    bottleneck_counts: dict[str, int] = defaultdict(int)
    for d in zero_fact_docs:
        for label in d["likely_bottleneck"].split("+"):
            bottleneck_counts[label] += 1
    bottleneck_counts = dict(bottleneck_counts)

    # Primary bottleneck
    primary = max(bottleneck_counts, key=bottleneck_counts.get) if bottleneck_counts else "unknown"

    # Estimate recoverable facts: high-pattern pages × ~2 facts each (conservative)
    estimated_recoverable = len(high_pattern_zero) * 2

    total = len(doc_records)
    with_facts = sum(1 for d in doc_records if d["fact_count"] > 0)
    zero = total - with_facts
    zero_fact_rate = round(zero / total, 4) if total > 0 else 0.0

    summary = {
        "report_id": report_id,
        "pricing_docs_accepted": total,
        "pricing_docs_with_facts": with_facts,
        "pricing_docs_zero_facts": zero,
        "zero_fact_rate": zero_fact_rate,
        "high_pattern_zero_fact_count": len(high_pattern_zero),
        "bottleneck_breakdown": bottleneck_counts,
        "primary_bottleneck": primary,
        "recommended_fix": "Option B — deterministic pricing pre-extractor (scan full doc, extract price-context windows)",
        "estimated_facts_recoverable": estimated_recoverable,
    }

    # ── Console output ────────────────────────────────────────────────────────

    header = f"{'URL':<60}  {'len':>7}  {'pat':>4}  {'facts':>5}  {'bottleneck'}"
    print(header)
    print("-" * len(header))
    for d in doc_records[:15]:
        url_short = (d["url"][:58] + "..") if len(d["url"]) > 60 else d["url"]
        print(
            f"{url_short:<60}  {d['content_length']:>7}  {d['price_pattern_count']:>4}"
            f"  {d['fact_count']:>5}  {d['likely_bottleneck']}"
        )

    print()
    print("Bottleneck breakdown (zero-fact docs):")
    for label, count in sorted(bottleneck_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count}")
    print()
    print(f"pricing_docs_accepted     : {total}")
    print(f"pricing_docs_with_facts   : {with_facts}")
    print(f"pricing_docs_zero_facts   : {zero}  (zero_fact_rate={zero_fact_rate:.1%})")
    print(f"high_pattern_zero_fact    : {len(high_pattern_zero)}  (>= {_HIGH_PATTERN_THRESHOLD} patterns, 0 facts)")
    print(f"estimated_recoverable     : ~{estimated_recoverable} facts (Option B)")
    print()
    print(f"PRIMARY BOTTLENECK: {primary}")
    print(f"RECOMMENDED FIX   : {summary['recommended_fix']}")

    # ── Write output files ────────────────────────────────────────────────────

    out_yield = artifact_dir / "pricing_doc_fact_yield.json"
    out_high = artifact_dir / "high_pattern_zero_fact_docs.json"
    out_summary = artifact_dir / "pricing_extraction_bottleneck_summary.json"

    out_yield.write_text(json.dumps(doc_records, indent=2))
    out_high.write_text(json.dumps(high_pattern_zero, indent=2))
    out_summary.write_text(json.dumps(summary, indent=2))

    print()
    print(f"Output files written:")
    print(f"  {out_yield}")
    print(f"  {out_high}")
    print(f"  {out_summary}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Offline pricing extraction yield diagnosis")
    parser.add_argument(
        "--artifact-dir",
        default="../pipeline_audit_artifacts/demo_track2_20260527T074938Z",
        help="Path to pipeline artifact folder",
    )
    parser.add_argument(
        "--report-id",
        default="report_1df9ca6a1014",
        help="Report ID to look up in DB",
    )
    parser.add_argument(
        "--db",
        default="data/pulselens.db",
        help="Path to pulselens.db (relative to backend/)",
    )
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    db_path = Path(args.db)

    if not artifact_dir.exists():
        print(f"Error: artifact_dir does not exist: {artifact_dir}", file=sys.stderr)
        sys.exit(1)

    run_diagnosis(artifact_dir, args.report_id, db_path)


if __name__ == "__main__":
    main()
