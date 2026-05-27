"""
Live PulseLens pipeline audit.

Runs the full LangGraph pipeline with telemetry wrappers around:
- OpenRouter calls via LLMClient
- Bright Data calls via BrightDataClient
- LangGraph node updates

Secrets are never written. API keys are only reported as set/missing.

Run from backend/:
  python scripts/full_pipeline_live_audit.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
REPORT_PATH = PROJECT_ROOT / "FULL_PIPELINE_TEST_REPORT.md"
ARTIFACT_ROOT = PROJECT_ROOT / "pipeline_audit_artifacts"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
ARTIFACT_DIR = ARTIFACT_ROOT / RUN_ID

MAX_INLINE_TEXT = 4000
MAX_TABLE_TEXT = 180


def _clip(value: object, limit: int = MAX_INLINE_TEXT) -> str:
    text = str(value) if value is not None else ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n...[truncated {len(text) - limit} chars]"


def _one_line(value: object, limit: int = MAX_TABLE_TEXT) -> str:
    text = str(value) if value is not None else ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _json_safe(obj: object) -> object:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")  # type: ignore[attr-defined]
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if hasattr(obj, "value"):
        return getattr(obj, "value")
    return str(obj)


def _write_json(name: str, payload: object) -> str:
    path = ARTIFACT_DIR / name
    path.write_text(json.dumps(_json_safe(payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path.relative_to(PROJECT_ROOT))


def _summarize_list(items: list[Any], sample_limit: int = 3) -> dict[str, Any]:
    return {
        "count": len(items),
        "sample": [_summarize_value(item, depth=1) for item in items[:sample_limit]],
    }


def _summarize_value(value: object, depth: int = 0) -> object:
    if depth > 3:
        return _one_line(value)
    if hasattr(value, "model_dump"):
        data = value.model_dump(mode="json")  # type: ignore[attr-defined]
        return _summarize_value(data, depth + 1)
    if isinstance(value, list):
        return _summarize_list(value)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"content", "evidence_quote", "narrative_body"} and isinstance(item, str):
                out[str(key)] = {
                    "chars": len(item),
                    "preview": _clip(item, 800),
                }
            elif isinstance(item, list):
                out[str(key)] = _summarize_list(item)
            elif isinstance(item, dict):
                out[str(key)] = _summarize_value(item, depth + 1)
            else:
                out[str(key)] = _json_safe(item)
        return out
    return _json_safe(value)


def _summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    list_keys = [
        "queries",
        "raw_documents",
        "raw_facts",
        "scored_facts",
        "verified_claims",
        "contradictions",
        "company_narratives",
        "errors",
    ]
    for key in list_keys:
        summary[key] = _summarize_list(list(state.get(key) or []))
    for key in [
        "market",
        "companies",
        "time_window",
        "query_expansion_rounds",
        "low_signal_types",
        "quality_passed",
        "signal_scores",
        "market_narrative",
        "report",
    ]:
        summary[key] = _summarize_value(state.get(key))
    return summary


class MemoryLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        )


def _env_status() -> dict[str, str]:
    keys = [
        "OPENROUTER_API_KEY",
        "BRIGHTDATA_API_KEY",
        "BRIGHTDATA_SERP_ZONE",
        "BRIGHTDATA_SCRAPER_ZONE",
        "BRIGHTDATA_BROWSER_ZONE",
        "BRIGHTDATA_UNLOCKER_ZONE",
        "ALPHA_VANTAGE_API_KEY",
        "AGENT1_MODEL",
        "AGENT3_MODEL",
        "AGENT5_MODEL",
        "AGENT6_MODEL",
        "AGENT7_MODEL",
        "AGENT8_MODEL",
        "EMBEDDING_MODEL",
        "PULSELENS_DISABLE_EMBEDDINGS",
    ]
    return {key: ("SET" if os.getenv(key) else "MISSING") for key in keys}


def _hardcoded_scan() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    include_suffixes = {".py", ".ts", ".tsx", ".md"}
    exclude_parts = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "dist",
        "cache",
        "data",
        "pipeline_audit_artifacts",
    }
    generated_reports = {
        "FULL_PIPELINE_TEST_REPORT.md",
        "AUDIT_REPORT.md",
        "RE_AUDIT_REPORT.md",
        "AGENT_QUALITY_REPORT.md",
    }
    patterns: list[tuple[str, str, str]] = [
        (r"https?://[^\"'\s)]+", "URL literal", "Check if this should be env/config."),
        (r"google/gemini-[^\"'\s]+", "LLM model literal", "Should be env-overridable."),
        (r"claude[^\"'\s)]*", "Claude/stale model literal", "Likely stale if code uses OpenRouter/Gemini."),
        (r"ProsusAI/finbert", "FinBERT model literal", "Consider FINBERT_MODEL env var."),
        (r"sentence-transformers/all-MiniLM-L6-v2", "Embedding model literal", "OK if env-overridable."),
        (r"Path\(\"/tmp/[^\"]+\"\)", "/tmp output path", "OK for tests/scripts, not runtime."),
        (r"\b_MIN_[A-Z0-9_]+\s*=\s*[0-9.]+", "Private threshold constant", "Consider config if product behavior."),
        (r"\b_MAX_[A-Z0-9_]+\s*=\s*[0-9.]+", "Private threshold constant", "Consider config if product behavior."),
        (r"\b_BATCH_SIZE\s*=\s*[0-9.]+", "Batch size constant", "Prefer env/config."),
        (r"\bDEFAULT_[A-Z0-9_]+\s*=\s*[\"0-9]", "Default constant", "OK when env-overridable."),
        (r"\"(?:Nvidia|AMD|Intel|Broadcom|Supermicro|Dell|HPE|Micron)\"", "Company literal", "Should usually derive from companies.py."),
    ]

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in include_suffixes:
            continue
        rel = path.relative_to(PROJECT_ROOT)
        if str(rel) in generated_reports:
            continue
        if any(part in exclude_parts for part in rel.parts):
            continue
        if str(rel) in {"backend/.env"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") and "Claude" not in stripped:
                continue
            for regex, category, note in patterns:
                if re.search(regex, line, re.IGNORECASE):
                    candidates.append(
                        {
                            "file": str(rel),
                            "line": lineno,
                            "category": category,
                            "value": stripped,
                            "note": note,
                        }
                    )
                    break
    return candidates


def _classify_hardcoded(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in candidates:
        file = item["file"]
        line = item["line"]
        value = item["value"]
        severity = "Info"
        recommendation = item["note"]

        if file.endswith("frontend/src/modules/about/pages/about-page.tsx") and "Claude" in value:
            severity = "Medium"
            recommendation = "Update stale UI copy to OpenRouter / configured model."
        elif file.endswith("backend/app/pipeline/agent4_finbert_scorer.py") and "ProsusAI/finbert" in value:
            severity = "Medium"
            recommendation = "Move to FINBERT_MODEL env/config; keep ProsusAI/finbert as default."
        elif file.endswith("backend/app/utils/finbert_client.py"):
            severity = "Low"
            recommendation = "Remove stub or replace with real shared FinBERT wrapper."
        elif file.endswith("backend/app/pipeline/node_quality_gate.py") and "_MIN_" in value:
            severity = "Medium"
            recommendation = "Move quality thresholds to app.config.quality_gates."
        elif file.endswith("backend/app/pipeline/node_validate_and_split.py") and ("_MIN_" in value or "_MAX_" in value):
            severity = "Medium"
            recommendation = "Move validation/SAFE thresholds to config."
        elif file.endswith("backend/app/pipeline/node_triangulator.py") and ("_TIER_W" in value or "_RECENCY_WINDOW_DAYS" in value):
            severity = "Medium"
            recommendation = "Import tier weights from source_tiers.py and move recency window to config."
        elif "localhost" in value:
            severity = "Low"
            recommendation = "Acceptable dev default if env/proxy override exists."
        elif file.endswith("backend/app/pipeline/agent1_query_planner.py") and "PRIORITY_COMPANIES" in value:
            severity = "Low"
            recommendation = "Hackathon-specific business rule; consider deriving priority from config."
        elif "package-lock.json" in file:
            continue

        findings.append({**item, "severity": severity, "recommendation": recommendation})
    return findings


def _run_command(label: str, args: list[str], cwd: Path) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=180,
        )
        return {
            "label": label,
            "command": " ".join(args),
            "cwd": str(cwd.relative_to(PROJECT_ROOT)),
            "returncode": proc.returncode,
            "duration_sec": round(time.perf_counter() - started, 2),
            "stdout": proc.stdout[-6000:],
            "stderr": proc.stderr[-6000:],
        }
    except Exception as exc:
        return {
            "label": label,
            "command": " ".join(args),
            "cwd": str(cwd.relative_to(PROJECT_ROOT)),
            "returncode": None,
            "duration_sec": round(time.perf_counter() - started, 2),
            "error": repr(exc),
        }


async def _run_pipeline_with_telemetry() -> dict[str, Any]:
    from langchain_core.runnables import RunnableConfig

    from app.config.companies import COMPANIES
    from app.config.markets import DEFAULT_MARKET, DEFAULT_TIME_WINDOW
    from app.pipeline.graph import pipeline_graph
    from app.pipeline.state import PipelineState
    from app.utils.helpers import generate_uuid

    initial_state: PipelineState = {
        "market": DEFAULT_MARKET,
        "companies": [company.name for company in COMPANIES],
        "time_window": DEFAULT_TIME_WINDOW,
        "queries": [],
        "raw_documents": [],
        "raw_facts": [],
        "scored_facts": [],
        "verified_claims": [],
        "contradictions": [],
        "signal_scores": {},
        "company_narratives": [],
        "market_narrative": None,
        "report": None,
        "query_expansion_rounds": 0,
        "low_signal_types": [],
        "quality_passed": False,
        "errors": [],
    }
    config: RunnableConfig = {
        "configurable": {"thread_id": f"live-audit-{generate_uuid()[:12]}"},
        "recursion_limit": 80,
    }

    started = time.perf_counter()
    node_events: list[dict[str, Any]] = []
    final_state: dict[str, Any] | None = None
    error: str | None = None

    try:
        async for update in pipeline_graph.astream(initial_state, config=config, stream_mode="updates"):
            for node_name, payload in update.items():
                node_events.append(
                    {
                        "time": datetime.now(timezone.utc).isoformat(),
                        "node": node_name,
                        "summary": _summarize_value(payload),
                    }
                )
        snapshot = await pipeline_graph.aget_state(config)
        final_state = dict(snapshot.values)
    except Exception:
        error = traceback.format_exc()
        try:
            snapshot = await pipeline_graph.aget_state(config)
            final_state = dict(snapshot.values)
        except Exception:
            pass

    return {
        "initial_state": initial_state,
        "config": {"configurable": config["configurable"], "recursion_limit": config["recursion_limit"]},
        "duration_sec": round(time.perf_counter() - started, 2),
        "node_events": node_events,
        "final_state": final_state,
        "final_state_summary": _summarize_state(final_state or {}),
        "error": error,
    }


def _install_telemetry(openrouter_calls: list[dict[str, Any]], brightdata_calls: list[dict[str, Any]]) -> None:
    from app.utils.llm_client import LLMClient
    from app.utils.brightdata_client import BrightDataClient

    original_llm_init = LLMClient.__init__
    original_llm_call = LLMClient._call
    original_bd_request = BrightDataClient._request
    counter_lock = threading.Lock()
    counters = {"llm": 0, "bd": 0}

    def audited_llm_init(self: Any, api_key: str | None = None, agent_name: str = "agent1") -> None:
        self._audit_agent_name = agent_name
        original_llm_init(self, api_key=api_key, agent_name=agent_name)

    def audited_llm_call(self: Any, system: str, user: str, model: str, max_tokens: int) -> str:
        with counter_lock:
            counters["llm"] += 1
            call_id = f"llm_{counters['llm']:04d}"
        started = time.perf_counter()
        entry: dict[str, Any] = {
            "call_id": call_id,
            "agent": getattr(self, "_audit_agent_name", "unknown"),
            "model": model,
            "max_tokens": max_tokens,
            "system_chars": len(system),
            "user_chars": len(user),
            "system": system,
            "user": user,
        }
        try:
            result = original_llm_call(self, system, user, model, max_tokens)
            entry.update(
                {
                    "ok": True,
                    "duration_sec": round(time.perf_counter() - started, 2),
                    "response_chars": len(result),
                    "response": result,
                }
            )
            return result
        except Exception as exc:
            entry.update(
                {
                    "ok": False,
                    "duration_sec": round(time.perf_counter() - started, 2),
                    "error": repr(exc),
                }
            )
            raise
        finally:
            openrouter_calls.append(entry)

    async def audited_bd_request(
        self: Any,
        zone: str,
        url: str,
        response_format: str,
        render_js: bool = False,
    ) -> Any:
        with counter_lock:
            counters["bd"] += 1
            call_id = f"bd_{counters['bd']:04d}"
        started = time.perf_counter()
        entry: dict[str, Any] = {
            "call_id": call_id,
            "zone": zone,
            "url": url,
            "response_format": response_format,
            "render_js": render_js,
        }
        try:
            result = await original_bd_request(self, zone, url, response_format, render_js=render_js)
            entry.update(
                {
                    "ok": True,
                    "duration_sec": round(time.perf_counter() - started, 2),
                    "response_summary": _summarize_brightdata_payload(result),
                }
            )
            return result
        except Exception as exc:
            entry.update(
                {
                    "ok": False,
                    "duration_sec": round(time.perf_counter() - started, 2),
                    "error": repr(exc),
                }
            )
            raise
        finally:
            brightdata_calls.append(entry)

    LLMClient.__init__ = audited_llm_init  # type: ignore[method-assign]
    LLMClient._call = audited_llm_call  # type: ignore[method-assign]
    BrightDataClient._request = audited_bd_request  # type: ignore[method-assign]


def _summarize_brightdata_payload(payload: object) -> dict[str, Any]:
    if isinstance(payload, str):
        return {
            "type": "str",
            "chars": len(payload),
            "preview": _clip(payload, 1200),
        }
    if isinstance(payload, list):
        return {
            "type": "list",
            "count": len(payload),
            "sample": [_summarize_value(item) for item in payload[:3]],
        }
    if isinstance(payload, dict):
        keys = sorted(str(k) for k in payload.keys())
        out: dict[str, Any] = {"type": "dict", "keys": keys}
        for key in ("url", "title", "published_date"):
            if key in payload:
                out[key] = payload.get(key)
        content = payload.get("content") or payload.get("text") or payload.get("html") or payload.get("body")
        if content is not None:
            out["content_chars"] = len(str(content))
            out["content_preview"] = _clip(content, 1200)
        return out
    return {"type": type(payload).__name__, "preview": _clip(payload, 1200)}


def _markdown_table(rows: Sequence[Sequence[object]], headers: list[str]) -> str:
    def cell(value: object) -> str:
        return _one_line(value, 120).replace("|", "\\|")

    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(cell(v) for v in row) + " |")
    return "\n".join(output)


def _list_like_count(value: object) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict) and isinstance(value.get("count"), int):
        return int(value["count"])
    return 0


def _render_report(
    env_status: dict[str, str],
    hardcoded_findings: list[dict[str, Any]],
    commands: list[dict[str, Any]],
    pipeline: dict[str, Any],
    openrouter_calls: list[dict[str, Any]],
    brightdata_calls: list[dict[str, Any]],
    logs: list[dict[str, Any]],
    artifact_paths: dict[str, str],
) -> str:
    final_state = pipeline.get("final_state") or {}
    report_obj = final_state.get("report") if isinstance(final_state, dict) else None
    final_summary = pipeline.get("final_state_summary") or {}
    errors = (final_state.get("errors") if isinstance(final_state, dict) else None) or []
    pipeline_error = pipeline.get("error")

    if pipeline_error:
        verdict = "FAIL - pipeline raised an exception"
    elif report_obj is None:
        verdict = "FAIL - pipeline completed without MarketPulseReport"
    elif errors:
        verdict = "PARTIAL - report generated with recorded errors"
    else:
        verdict = "PASS - MarketPulseReport generated"

    hardcoded_rows = [
        [
            item["severity"],
            f"{item['file']}:{item['line']}",
            item["category"],
            item["value"],
            item["recommendation"],
        ]
        for item in hardcoded_findings
        if item["severity"] != "Info"
    ]
    if not hardcoded_rows:
        hardcoded_rows = [["Info", "-", "-", "No non-info hard-code candidates found", "-"]]

    command_rows = [
        [
            cmd["label"],
            cmd.get("returncode"),
            cmd.get("duration_sec"),
            _one_line((cmd.get("stdout") or "") + " " + (cmd.get("stderr") or "") + " " + (cmd.get("error") or ""), 160),
        ]
        for cmd in commands
    ]

    node_rows = [
        [
            idx + 1,
            event["node"],
            json.dumps(event["summary"], ensure_ascii=False, default=str)[:500],
        ]
        for idx, event in enumerate(pipeline.get("node_events") or [])
    ]

    llm_rows = [
        [
            call["call_id"],
            call.get("agent"),
            call.get("model"),
            call.get("ok"),
            call.get("duration_sec"),
            call.get("system_chars"),
            call.get("user_chars"),
            call.get("response_chars", 0),
            call.get("error", ""),
        ]
        for call in openrouter_calls
    ]

    bd_rows = [
        [
            call["call_id"],
            call.get("zone"),
            call.get("response_format"),
            call.get("render_js"),
            call.get("ok"),
            call.get("duration_sec"),
            call.get("url"),
            call.get("error", ""),
        ]
        for call in brightdata_calls
    ]

    env_rows = [[key, value] for key, value in env_status.items()]
    zero_doc_queries: list[str] = []
    brightdata_permanent_errors = 0
    json_parse_failures = 0
    low_quality_filtered: tuple[int, int] | None = None
    checkpoint_warnings = 0
    quality_gate_line = ""
    for record in logs:
        msg = record.get("message", "")
        m = re.search(r"Agent 2 collected 0 documents for query (q_[a-f0-9]+)", msg)
        if m:
            zero_doc_queries.append(m.group(1))
        if "Bright Data permanent error" in msg:
            brightdata_permanent_errors += 1
        if "JSON parse failure" in msg:
            json_parse_failures += 1
        m = re.search(r"Agent 2 filtered (\d+)/(\d+) documents as low-quality", msg)
        if m:
            low_quality_filtered = (int(m.group(1)), int(m.group(2)))
        if "Deserializing unregistered type" in msg:
            checkpoint_warnings += 1
        if "quality_gate: facts=" in msg:
            quality_gate_line = msg

    lines = [
        "# Full PulseLens Pipeline Test Report",
        "",
        f"- Run ID: `{RUN_ID}`",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Verdict: **{verdict}**",
        f"- Pipeline duration: `{pipeline.get('duration_sec')}s`",
        f"- OpenRouter calls captured: `{len(openrouter_calls)}`",
        f"- Bright Data calls captured: `{len(brightdata_calls)}`",
        f"- LangGraph node updates captured: `{len(pipeline.get('node_events') or [])}`",
        "",
        "Secrets are redacted. API keys are reported only as SET/MISSING.",
        "",
        "## 1. Artifact Index",
        "",
        _markdown_table([[k, v] for k, v in artifact_paths.items()], ["Artifact", "Path"]),
        "",
        "## 2. Environment Readiness",
        "",
        _markdown_table(env_rows, ["Variable", "Status"]),
        "",
        "## 3. Hard-Coded Values Audit",
        "",
        "The table below lists non-info hard-code candidates found in used project code/docs. Full raw scan is in the artifacts.",
        "",
        _markdown_table(hardcoded_rows, ["Severity", "Location", "Category", "Value", "Recommendation"]),
        "",
        "## 4. Verification Commands",
        "",
        _markdown_table(command_rows, ["Check", "Exit", "Seconds", "Output tail"]),
        "",
        "## 5. Pipeline Input",
        "",
        "```json",
        json.dumps(_json_safe(pipeline.get("initial_state")), indent=2, ensure_ascii=False),
        "```",
        "",
        "## 6. Stage-by-Stage LangGraph Updates",
        "",
        _markdown_table(node_rows, ["#", "Node", "Output Summary"]),
        "",
        "## 7. Final Pipeline State Summary",
        "",
        "```json",
        json.dumps(_json_safe(final_summary), indent=2, ensure_ascii=False)[:30000],
        "```",
        "",
        "## 8. OpenRouter Calls",
        "",
        _markdown_table(llm_rows, ["Call", "Agent", "Model", "OK", "Seconds", "System chars", "User chars", "Response chars", "Error"]),
        "",
        "### OpenRouter Prompt/Response Samples",
        "",
    ]

    for call in openrouter_calls[:12]:
        lines.extend(
            [
                f"#### {call['call_id']} - {call.get('agent')} - OK={call.get('ok')}",
                "",
                "**System prompt**",
                "",
                "```text",
                _clip(call.get("system", ""), 3000),
                "```",
                "",
                "**User prompt**",
                "",
                "```text",
                _clip(call.get("user", ""), 3000),
                "```",
                "",
                "**Response**",
                "",
                "```text",
                _clip(call.get("response", call.get("error", "")), 3000),
                "```",
                "",
            ]
        )

    if len(openrouter_calls) > 12:
        lines.append(f"Additional OpenRouter call details are in `{artifact_paths['openrouter_calls']}`.")
        lines.append("")

    lines.extend(
        [
            "## 9. Bright Data Calls",
            "",
            _markdown_table(bd_rows, ["Call", "Zone", "Format", "Render JS", "OK", "Seconds", "URL", "Error"]),
            "",
            "### Bright Data Response Samples",
            "",
        ]
    )
    for call in brightdata_calls[:20]:
        lines.extend(
            [
                f"#### {call['call_id']} - OK={call.get('ok')}",
                "",
                f"- URL: `{call.get('url')}`",
                f"- Zone: `{call.get('zone')}`",
                f"- Format: `{call.get('response_format')}`",
                "",
                "```json",
                json.dumps(_json_safe(call.get("response_summary", {"error": call.get("error")})), indent=2, ensure_ascii=False)[:5000],
                "```",
                "",
            ]
        )
    if len(brightdata_calls) > 20:
        lines.append(f"Additional Bright Data call details are in `{artifact_paths['brightdata_calls']}`.")
        lines.append("")

    lines.extend(
        [
            "## 10. Runtime Logs",
            "",
            "Last 120 log lines captured from pipeline modules:",
            "",
            "```text",
            "\n".join(
                f"{r['time']} {r['level']} {r['logger']}: {r['message']}"
                for r in logs[-120:]
            ),
            "```",
            "",
            "## 11. Errors And Weaknesses Observed",
            "",
        ]
    )

    if pipeline_error:
        lines.extend(["### Pipeline exception", "", "```text", pipeline_error, "```", ""])
    if errors:
        lines.extend(["### State errors", "", "```json", json.dumps(_json_safe(errors), indent=2), "```", ""])
    if report_obj is None:
        lines.append("- No `MarketPulseReport` was present in final state.")
    else:
        report_data = _json_safe(report_obj)
        lines.append(f"- MarketPulseReport generated: `{report_data.get('report_id') if isinstance(report_data, dict) else 'unknown'}`")
        if isinstance(report_data, dict):
            lines.append(f"- Pulse score: `{report_data.get('pulse_score')}`")
            lines.append(f"- Pulse status: `{report_data.get('pulse_status')}`")
            lines.append(f"- Evidence count: `{report_data.get('evidence_count')}`")
            lines.append(f"- Source count: `{report_data.get('source_count')}`")
            lines.append(f"- Company narratives: `{_list_like_count(report_data.get('company_narratives'))}`")
            lines.append(f"- Top signals: `{_list_like_count(report_data.get('top_signals'))}`")
            narrative = report_data.get("market_narrative") or {}
            lines.append(
                f"- Watch list items: `{_list_like_count(narrative.get('watch_list')) if isinstance(narrative, dict) else 0}`"
            )
    lines.append("")

    weakness_notes = []
    if any(item["severity"] in {"Medium", "High", "Critical"} for item in hardcoded_findings):
        weakness_notes.append("Hard-coded/stale values remain; see Section 3.")
    if zero_doc_queries:
        weakness_notes.append(
            f"Agent 2 returned 0 documents for {len(zero_doc_queries)} queries: "
            + ", ".join(zero_doc_queries[:12])
            + (" ..." if len(zero_doc_queries) > 12 else "")
        )
    if brightdata_permanent_errors:
        weakness_notes.append(
            f"Bright Data scraper returned {brightdata_permanent_errors} permanent HTTP errors during page fetches."
        )
    if low_quality_filtered:
        weakness_notes.append(
            f"Agent 2 discarded {low_quality_filtered[0]}/{low_quality_filtered[1]} fetched documents as low-quality before extraction."
        )
    if json_parse_failures:
        weakness_notes.append(f"LLM JSON parsing failed {json_parse_failures} time(s) and required retry.")
    if quality_gate_line and "signal_types=5" in quality_gate_line:
        weakness_notes.append(
            "Quality gate passed with only 5 covered fact signal types because the current gate threshold is 4; "
            "this is lower than Agent 1's 7-signal query coverage target."
        )
    if checkpoint_warnings:
        weakness_notes.append(
            f"LangGraph emitted {checkpoint_warnings} checkpoint serialization warnings for unregistered Pydantic/Enum types."
        )
    if pipeline.get("node_events"):
        node_names = [event["node"] for event in pipeline["node_events"]]
        if node_names.count("query_planner") > 1:
            weakness_notes.append("Quality-gate expansion occurred; inspect duplicated query/document behavior carefully.")
    if not brightdata_calls:
        weakness_notes.append("No Bright Data calls were captured; Agent 2 did not reach live collection or config failed early.")
    if not openrouter_calls:
        weakness_notes.append("No OpenRouter calls were captured; Agent 1 did not reach LLM execution or config failed early.")
    if not weakness_notes:
        weakness_notes.append("No additional automated weakness notes beyond the tables above.")
    lines.extend(f"- {note}" for note in weakness_notes)
    lines.append("")

    return "\n".join(lines)


async def main() -> int:
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, str(BACKEND_DIR))
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    load_dotenv(BACKEND_DIR / ".env")

    log_handler = MemoryLogHandler()
    log_handler.setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger().addHandler(log_handler)
    for name in ("app", "langgraph"):
        logging.getLogger(name).setLevel(logging.INFO)

    openrouter_calls: list[dict[str, Any]] = []
    brightdata_calls: list[dict[str, Any]] = []

    env_status = _env_status()
    raw_hardcoded = _hardcoded_scan()
    hardcoded_findings = _classify_hardcoded(raw_hardcoded)

    commands = [
        _run_command("Backend compile", [str(BACKEND_DIR / ".venv/bin/python"), "-m", "compileall", "-q", "app"], BACKEND_DIR),
        _run_command("Frontend build", ["npm", "run", "build"], PROJECT_ROOT / "frontend"),
    ]

    _install_telemetry(openrouter_calls, brightdata_calls)
    pipeline = await _run_pipeline_with_telemetry()

    artifact_paths = {
        "raw_hardcoded_scan": _write_json("raw_hardcoded_scan.json", raw_hardcoded),
        "hardcoded_findings": _write_json("hardcoded_findings.json", hardcoded_findings),
        "verification_commands": _write_json("verification_commands.json", commands),
        "openrouter_calls": _write_json("openrouter_calls.json", openrouter_calls),
        "brightdata_calls": _write_json("brightdata_calls.json", brightdata_calls),
        "langgraph_node_events": _write_json("langgraph_node_events.json", pipeline.get("node_events") or []),
        "final_state_summary": _write_json("final_state_summary.json", pipeline.get("final_state_summary") or {}),
        "runtime_logs": _write_json("runtime_logs.json", log_handler.records),
    }

    report_text = _render_report(
        env_status=env_status,
        hardcoded_findings=hardcoded_findings,
        commands=commands,
        pipeline=pipeline,
        openrouter_calls=openrouter_calls,
        brightdata_calls=brightdata_calls,
        logs=log_handler.records,
        artifact_paths=artifact_paths,
    )
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Artifacts: {ARTIFACT_DIR}")
    if pipeline.get("error"):
        print("Pipeline error captured; see report.")
        return 1
    if not (pipeline.get("final_state") or {}).get("report"):
        print("No report generated; see report.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
