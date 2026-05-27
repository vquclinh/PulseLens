"""
Offline replay / projection for the pricing pre-extractor.

Since full document text was not persisted in the audit artifacts (only content_length
and price_pattern_count were captured in web_collection_audit.json), this script cannot
run the pre-extractor on real document content. Instead, it:

1. Reads the latest pricing fact yield analysis from the artifact folder
2. Projects how many facts the pre-extractor would likely recover per high-pattern URL
3. Writes projection summary to pipeline_audit_artifacts/pricing_pre_extractor_replay_<ts>/

Run from backend/:
    python scripts/replay_pricing_pre_extractor_on_artifact.py \\
        --artifact-dir ../docs/archive_generated_artifacts/cleanup_20260527/pipeline_audit_artifacts/demo_track2_20260527T074938Z
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Facts-per-pattern conservative estimate (1 fact per 20 explicit price patterns, max 4 per URL)
_FACTS_PER_PATTERN_RATIO = 20
_MAX_FACTS_PER_URL = 4


def _estimate_recoverable(price_pattern_count: int) -> int:
    return min(max(price_pattern_count // _FACTS_PER_PATTERN_RATIO, 1), _MAX_FACTS_PER_URL)


def run_replay(artifact_dir: Path) -> None:
    print(f"\nPricing pre-extractor offline replay")
    print(f"  artifact_dir: {artifact_dir}")
    print()

    # Locate required inputs
    yield_path = artifact_dir / "pricing_doc_fact_yield.json"
    high_path = artifact_dir / "high_pattern_zero_fact_docs.json"
    summary_path = artifact_dir / "pricing_extraction_bottleneck_summary.json"

    if not yield_path.exists():
        print(f"[WARN] pricing_doc_fact_yield.json not found at {yield_path}")
        print("       Run backend/scripts/pricing_fact_yield_diagnosis.py first.")
        return

    doc_yields = json.loads(yield_path.read_text())
    high_pattern_docs = json.loads(high_path.read_text()) if high_path.exists() else []
    bottleneck_summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}

    # --- Projection logic ---
    projection_rows = []
    total_projected = 0
    for doc in doc_yields:
        pcount = doc.get("price_pattern_count", 0)
        fact_count = doc.get("fact_count", 0)
        if fact_count > 0:
            projected = 0
            status = "already_has_facts"
        elif pcount >= 10:
            projected = _estimate_recoverable(pcount)
            status = "high_pattern_recoverable"
        elif pcount >= 1:
            projected = 0  # low-pattern docs: pre-extractor would fire but likely 0 new facts
            status = "low_pattern_uncertain"
        else:
            projected = 0
            status = "no_patterns"
        total_projected += projected
        projection_rows.append({
            "url": doc.get("url"),
            "domain": doc.get("domain"),
            "content_length": doc.get("content_length", 0),
            "price_pattern_count": pcount,
            "existing_fact_count": fact_count,
            "projected_new_facts": projected,
            "recovery_status": status,
            "bottleneck": doc.get("likely_bottleneck", ""),
        })

    projection_rows.sort(key=lambda r: -r["projected_new_facts"])

    replay_summary = {
        "replay_type": "projection_only",
        "reason_no_live_replay": (
            "Full document text was not persisted in audit artifacts. "
            "web_collection_audit.json stores content_length and price_pattern_count "
            "but not the actual document content. Live replay requires a new pipeline run."
        ),
        "artifact_dir": str(artifact_dir),
        "report_id": bottleneck_summary.get("report_id", "unknown"),
        "pricing_docs_analyzed": len(doc_yields),
        "high_pattern_zero_fact_docs": len(high_pattern_docs),
        "total_projected_new_facts": total_projected,
        "projection_assumption": f"1 fact per {_FACTS_PER_PATTERN_RATIO} price patterns, max {_MAX_FACTS_PER_URL} per URL",
        "url_projections": projection_rows,
    }

    # --- Console output ---
    print(f"{'URL':<55}  {'patterns':>8}  {'projected':>9}  {'status'}")
    print("-" * 100)
    for row in projection_rows:
        url_short = row["url"][:53] + ".." if len(row["url"]) > 55 else row["url"]
        print(
            f"{url_short:<55}  {row['price_pattern_count']:>8}  {row['projected_new_facts']:>9}"
            f"  {row['recovery_status']}"
        )
    print()
    print(f"Total projected new facts from pre-extractor: {total_projected}")
    print()
    print("NOTE: This is a projection only. Full document text is not available for live replay.")
    print("      The actual fact count depends on sentence structure and entity presence in context windows.")
    print()

    # --- Write output ---
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path("../pipeline_audit_artifacts") / f"pricing_pre_extractor_replay_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    replay_file = out_dir / "pricing_pre_extractor_replay_summary.json"
    replay_file.write_text(json.dumps(replay_summary, indent=2))

    print(f"Output written to: {replay_file}")


def main() -> None:
    # Default search order: live artifact folder, then archive
    default_candidates = [
        "../pipeline_audit_artifacts/demo_track2_20260527T074938Z",
        "../docs/archive_generated_artifacts/cleanup_20260527/pipeline_audit_artifacts/demo_track2_20260527T074938Z",
    ]

    parser = argparse.ArgumentParser(description="Offline pricing pre-extractor projection")
    parser.add_argument(
        "--artifact-dir",
        default=None,
        help="Path to artifact folder containing pricing_doc_fact_yield.json",
    )
    args = parser.parse_args()

    if args.artifact_dir:
        artifact_dir = Path(args.artifact_dir)
    else:
        artifact_dir = None
        for candidate in default_candidates:
            p = Path(candidate)
            if (p / "pricing_doc_fact_yield.json").exists():
                artifact_dir = p
                break
        if artifact_dir is None:
            print("Could not find pricing_doc_fact_yield.json in default locations.")
            print("Run with --artifact-dir pointing to the correct artifact folder.")
            sys.exit(1)

    if not artifact_dir.exists():
        print(f"Error: artifact_dir does not exist: {artifact_dir}", file=sys.stderr)
        sys.exit(1)

    run_replay(artifact_dir)


if __name__ == "__main__":
    main()
