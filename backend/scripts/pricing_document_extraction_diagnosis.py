"""
pricing_document_extraction_diagnosis.py — Sprint 4 zero-cost audit script.

Answers: "Why did cloud pricing docs (CoreWeave, RunPod, GCP) yield zero pricing_pressure facts?"

Inputs (zero BrightData cost):
  - web_collection_audit.json from an existing artifact dir
  - facts from SQLite DB for a given report_id

Logic:
  1. Load accepted pricing URLs from web_collection_audit.json
  2. Load pricing_pressure facts from DB — get the source URLs that DID produce facts
  3. For each accepted pricing URL that produced ZERO pricing_pressure facts:
       classify URL type + estimate gap cause
  4. Write 4 JSON output files

Usage:
  python backend/scripts/pricing_document_extraction_diagnosis.py
  python backend/scripts/pricing_document_extraction_diagnosis.py \
      --report-id report_05aacb872fda \
      --artifact-dir pipeline_audit_artifacts/demo_track2_20260526T165950Z
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pricing_diagnosis")

# ── Paths ──────────────────────────────────────────────────────────────────────

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent
_DB_PATH = _REPO_ROOT / "backend" / "data" / "pulselens.db"
_ARTIFACT_ROOT = _REPO_ROOT / "pipeline_audit_artifacts"

_DEFAULT_REPORT_ID = "report_05aacb872fda"
_DEFAULT_ARTIFACT_DIR = str(_ARTIFACT_ROOT / "demo_track2_20260526T165950Z")

# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def classify_pricing_url(url: str) -> str:
    """
    Classify an accepted pricing URL by content type.
    Returns one of: direct_pricing_page, blog_or_guide, newsletter, unknown.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        domain = _extract_domain(url)
    except Exception:
        return "unknown"

    if any(kw in path for kw in ("/pricing", "/prices", "/price-list", "/rates", "/price")):
        return "direct_pricing_page"
    if any(kw in path for kw in ("/blog/", "/articles/", "/guides/", "/guide/", "/newsletter/")):
        return "blog_or_guide"
    if "newsletter." in domain or "/p/" in path:
        return "newsletter"
    return "unknown"


def estimate_gap_cause(url_type: str, url: str) -> str:
    """
    Estimate why a pricing URL might have yielded zero pricing_pressure facts.
    """
    if url_type == "direct_pricing_page":
        # Cloud provider pages often serve JS-rendered price tables the scraper can't see
        return "likely_no_explicit_price_table_in_scraped_html"
    if url_type == "blog_or_guide":
        return "likely_comparison_guide_not_primary_price_source"
    if url_type == "newsletter":
        return "likely_paywall_partial_content"
    # Heuristics for unknown type
    path = urlparse(url).path.lower()
    if any(kw in path for kw in ("availability", "regions", "specs", "overview")):
        return "likely_availability_page_not_pricing"
    return "unknown"


def has_explicit_price_in_url_or_title(url: str, title: str) -> bool:
    """True if the URL path or title contains an explicit price pattern."""
    text = url + " " + (title or "")
    return bool(re.search(r"\$[\d,]+", text))


# ── DB helpers ──────────────────────────────────────────────────────────────────

def load_pricing_fact_urls(db_path: Path, report_id: str) -> set[str]:
    """Return source_url set for all pricing_pressure facts in this report.
    Facts are stored as JSON in the payload column."""
    if not db_path.exists():
        logger.warning("DB not found: %s", db_path)
        return set()
    try:
        with sqlite3.connect(str(db_path)) as conn:
            rows = conn.execute(
                "SELECT json_extract(payload, '$.source_url') FROM facts "
                "WHERE report_id = ? AND json_extract(payload, '$.signal_type') = 'pricing_pressure'",
                (report_id,),
            ).fetchall()
            return {row[0] for row in rows if row[0]}
    except Exception as exc:
        logger.error("DB query failed: %s", exc)
        return set()


# ── Web collection audit loader ────────────────────────────────────────────────

def load_accepted_pricing_urls(artifact_dir: Path) -> list[dict]:
    """
    Load accepted pricing URLs from web_collection_audit.json.
    Returns list of {url, title, signal_type, query_text, domain}.
    """
    audit_path = artifact_dir / "web_collection_audit.json"
    if not audit_path.exists():
        logger.warning("web_collection_audit.json not found: %s", audit_path)
        return []

    try:
        with open(audit_path) as f:
            audit = json.load(f)
    except Exception as exc:
        logger.error("Failed to read web_collection_audit.json: %s", exc)
        return []

    pricing_urls: list[dict] = []
    queries = audit.get("queries") or []
    for q in queries:
        sig = q.get("signal_type", "")
        if sig != "pricing_pressure":
            continue
        # accepted_urls is a list of {url, reason} dicts
        for entry in q.get("accepted_urls") or []:
            if isinstance(entry, dict):
                url = entry.get("url", "")
                acceptance_reason = entry.get("reason", "")
            else:
                url = str(entry)
                acceptance_reason = ""
            if not url:
                continue
            pricing_urls.append({
                "url": url,
                "title": "",
                "signal_type": sig,
                "query_text": q.get("query_text", ""),
                "domain": _extract_domain(url),
                "acceptance_reason": acceptance_reason,
            })

    logger.info("Loaded %d accepted pricing_pressure URLs from audit", len(pricing_urls))
    return pricing_urls


# ── Main ────────────────────────────────────────────────────────────────────────

def run_diagnosis(report_id: str, artifact_dir: str, output_dir: str | None = None) -> Path:
    artifact_path = Path(artifact_dir)
    if not artifact_path.exists():
        logger.error("Artifact dir not found: %s", artifact_path)
        sys.exit(1)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(output_dir) if output_dir else (_ARTIFACT_ROOT / f"pricing_extraction_diagnosis_{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Writing output to: %s", out_dir)

    # Load inputs
    accepted_pricing_urls = load_accepted_pricing_urls(artifact_path)
    pricing_fact_urls = load_pricing_fact_urls(_DB_PATH, report_id)
    logger.info("DB pricing_pressure fact source URLs: %d", len(pricing_fact_urls))

    if not accepted_pricing_urls:
        logger.warning("No accepted pricing_pressure URLs found — check artifact dir contents")

    # Classify each accepted URL
    all_classified: list[dict] = []
    zero_fact_urls: list[dict] = []
    with_price_pattern: list[dict] = []
    without_price_pattern: list[dict] = []

    for entry in accepted_pricing_urls:
        url = entry["url"]
        title = entry["title"]
        url_type = classify_pricing_url(url)
        produced_fact = url in pricing_fact_urls
        gap_cause = "" if produced_fact else estimate_gap_cause(url_type, url)
        has_price_pattern = has_explicit_price_in_url_or_title(url, title)

        classified = {
            **entry,
            "url_type": url_type,
            "produced_pricing_fact": produced_fact,
            "gap_cause": gap_cause,
            "has_explicit_price_in_url_or_title": has_price_pattern,
        }
        all_classified.append(classified)

        if not produced_fact:
            zero_fact_urls.append(classified)
            if has_price_pattern:
                with_price_pattern.append(classified)
            else:
                without_price_pattern.append(classified)

    # Aggregate summary
    gap_by_domain: dict[str, dict] = {}
    gap_by_cause: dict[str, int] = {}
    for entry in zero_fact_urls:
        d = entry["domain"]
        if d not in gap_by_domain:
            gap_by_domain[d] = {"url_count": 0, "url_types": [], "gap_causes": []}
        gap_by_domain[d]["url_count"] += 1
        gap_by_domain[d]["url_types"].append(entry["url_type"])
        if entry["gap_cause"]:
            gap_by_domain[d]["gap_causes"].append(entry["gap_cause"])
            gap_by_cause[entry["gap_cause"]] = gap_by_cause.get(entry["gap_cause"], 0) + 1

    summary = {
        "report_id": report_id,
        "artifact_dir": str(artifact_path),
        "run_at": ts,
        "total_accepted_pricing_urls": len(accepted_pricing_urls),
        "urls_that_produced_pricing_facts": len(pricing_fact_urls),
        "urls_with_zero_pricing_facts": len(zero_fact_urls),
        "zero_fact_urls_with_explicit_price_in_url_or_title": len(with_price_pattern),
        "zero_fact_urls_without_explicit_price": len(without_price_pattern),
        "gap_count_by_domain": {d: v["url_count"] for d, v in sorted(gap_by_domain.items(), key=lambda x: -x[1]["url_count"])},
        "gap_count_by_cause": dict(sorted(gap_by_cause.items(), key=lambda x: -x[1])),
        "domain_detail": gap_by_domain,
    }

    # Write outputs
    _write_json(out_dir / "pricing_document_extraction_diagnosis.json", all_classified)
    _write_json(out_dir / "cloud_pricing_docs_with_price_patterns.json", with_price_pattern)
    _write_json(out_dir / "cloud_pricing_docs_without_price_patterns.json", without_price_pattern)
    _write_json(out_dir / "pricing_extraction_gap_summary.json", summary)

    # Console summary
    print(f"\n── Pricing Extraction Gap Diagnosis ──────────────────────────────")
    print(f"  Report:              {report_id}")
    print(f"  Accepted pricing URLs: {summary['total_accepted_pricing_urls']}")
    print(f"  URLs that produced facts: {summary['urls_that_produced_pricing_facts']}")
    print(f"  Zero-fact URLs:       {summary['urls_with_zero_pricing_facts']}")
    print(f"\n  Zero-fact by domain:")
    for domain, count in summary["gap_count_by_domain"].items():
        detail = gap_by_domain[domain]
        causes = list(set(detail["gap_causes"]))
        print(f"    {domain}: {count} URL(s) — {causes}")
    print(f"\n  Gap causes:")
    for cause, count in summary["gap_count_by_cause"].items():
        print(f"    {cause}: {count}")
    print(f"\n  Output: {out_dir}")

    return out_dir


def _write_json(path: Path, data: object) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("Wrote %s", path.name)


if __name__ == "__main__":
    sys.path.insert(0, str(_REPO_ROOT / "backend"))

    parser = argparse.ArgumentParser(description="Diagnose cloud pricing extraction gap")
    parser.add_argument("--report-id", default=_DEFAULT_REPORT_ID)
    parser.add_argument("--artifact-dir", default=_DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    run_diagnosis(args.report_id, args.artifact_dir, args.output_dir)
