#!/usr/bin/env python
"""Cheap pricing_pressure-only retrieval audit for the Track 2 demo scope."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

load_dotenv(BACKEND / ".env")

from app.config.demo_scope import get_scope_config, scope_payload  # noqa: E402
from app.pipeline.agent2_web_workers import (  # noqa: E402
    collect_documents,
    get_last_collection_audit,
    get_last_fetch_error_summary,
)
from app.pipeline.pricing_pressure_playbook import (  # noqa: E402
    build_pricing_playbook_specs,
    pricing_playbook_audit_payload,
    specs_to_search_queries,
)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")


def _failure_analysis(web_audit: dict[str, Any]) -> dict[str, Any]:
    queries = web_audit.get("queries") or []
    rows: list[dict[str, Any]] = []
    for query in queries:
        rejected = query.get("rejected_urls") or []
        accepted = query.get("accepted_urls") or []
        rows.append({
            "query_id": query.get("query_id"),
            "query_text": query.get("query_text"),
            "target_entity": query.get("target_entity"),
            "source_type": query.get("source_type"),
            "accepted_doc_count": query.get("accepted_doc_count", 0),
            "accepted_urls": accepted,
            "rejected_urls": rejected,
            "fetch_errors": query.get("fetch_errors") or [],
            "fallback_used": query.get("fallback_used", False),
            "fallback_policy": query.get("fallback_policy"),
            "fallback_produced_documents": query.get("fallback_produced_documents", False),
            "likely_failure": _likely_failure(query),
        })
    return {
        "pricing_query_count": len(queries),
        "zero_doc_query_count": sum(1 for query in queries if int(query.get("accepted_doc_count") or 0) == 0),
        "pricing_queries": rows,
    }


def _likely_failure(query: dict[str, Any]) -> str:
    if int(query.get("accepted_doc_count") or 0) > 0:
        return "accepted_documents_found"
    reasons = Counter(item.get("reason", "unknown") for item in query.get("rejected_urls") or [])
    if reasons:
        return f"top_rejection={reasons.most_common(1)[0][0]}"
    if query.get("fetch_errors"):
        return "fetch_error"
    return "no_serp_candidates_or_all_filtered"


async def main() -> int:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = ROOT / "pipeline_audit_artifacts" / f"pricing_pressure_{timestamp}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(artifact_dir / "pricing_pressure_run.log", encoding="utf-8"),
        ],
    )

    scope = get_scope_config()
    specs = build_pricing_playbook_specs(scope.companies, "last 7 days", include_market=True)
    queries = specs_to_search_queries(specs)
    playbook_payload = pricing_playbook_audit_payload(specs, queries)

    docs = await collect_documents(queries)
    web_audit = get_last_collection_audit()
    fetch_summary = get_last_fetch_error_summary()
    failure_analysis = _failure_analysis(web_audit)

    rejected_urls = [
        {**item, "query_id": query.get("query_id")}
        for query in web_audit.get("queries", [])
        for item in query.get("rejected_urls", [])
    ]
    accepted_domains = Counter(doc.domain for doc in docs)
    rejection_reasons = Counter(item.get("reason", "unknown") for item in rejected_urls)
    metadata_only_count = sum(1 for doc in docs if doc.content_quality == "metadata_only")
    full_text_count = sum(1 for doc in docs if doc.content_quality == "full_text")
    fallback_serp_estimate = sum(2 for query in web_audit.get("queries", []) if query.get("fallback_used"))
    estimated_brightdata_calls = len(queries) + fallback_serp_estimate + int(fetch_summary.get("total_fetch_attempts") or 0)

    failure_summary = {
        "pricing_query_count": len(queries),
        "accepted_pricing_documents": len(docs),
        "zero_doc_pricing_queries": web_audit.get("zero_doc_query_count", 0),
        "zero_doc_pricing_query_rate": round((web_audit.get("zero_doc_query_count", 0) or 0) / max(len(queries), 1), 4),
        "metadata_only_count": metadata_only_count,
        "full_text_count": full_text_count,
        "top_accepted_domains": accepted_domains.most_common(10),
        "top_rejection_reasons": rejection_reasons.most_common(10),
        "fetch_error_summary": fetch_summary,
        "estimated_brightdata_calls": estimated_brightdata_calls,
    }

    _write(artifact_dir / "pricing_scope_config.json", scope_payload(scope))
    _write(artifact_dir / "pricing_queries.json", playbook_payload)
    _write(artifact_dir / "pricing_web_collection_audit.json", web_audit)
    _write(artifact_dir / "pricing_accepted_documents.json", docs)
    _write(artifact_dir / "pricing_rejected_urls.json", rejected_urls)
    _write(artifact_dir / "pricing_failure_summary.json", failure_summary)
    _write(artifact_dir / "pricing_pressure_failure_analysis.json", failure_analysis)

    print("\nPricing pressure retrieval audit")
    print(f"  artifacts: {artifact_dir}")
    print(f"  scope mode: {'demo' if scope.demo_scope_enabled else 'full'}")
    print(f"  companies: {scope.companies}")
    print(f"  pricing query count: {len(queries)}")
    print(f"  accepted pricing documents: {len(docs)}")
    print(f"  zero-doc pricing queries: {failure_summary['zero_doc_pricing_queries']}")
    print(f"  zero-doc pricing query rate: {failure_summary['zero_doc_pricing_query_rate']}")
    print(f"  top accepted domains: {accepted_domains.most_common(10)}")
    print(f"  top rejection reasons: {rejection_reasons.most_common(10)}")
    print(f"  metadata_only count: {metadata_only_count}")
    print(f"  full_text count: {full_text_count}")
    print(f"  estimated Bright Data calls used: {estimated_brightdata_calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
