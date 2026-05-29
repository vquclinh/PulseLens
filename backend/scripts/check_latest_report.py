"""
check_latest_report.py — quick runtime verification of DB backend + latest report.

Usage (from backend/):
    python scripts/check_latest_report.py

Loads .env automatically so it works the same way the API does.
Never prints DATABASE_URL or any secret.
"""
from __future__ import annotations

import asyncio
import os
import sys

# Load .env exactly as main.py does — must happen before any app.* import
from dotenv import load_dotenv
load_dotenv()

# Now safe to import the adapter
from app.db import db_adapter  # noqa: E402 — must be after load_dotenv


async def main() -> None:
    backend = os.getenv("DATABASE_BACKEND", "sqlite").lower()
    db_url_present = bool(os.getenv("DATABASE_URL"))

    print(f"DATABASE_BACKEND : {backend}")
    print(f"DATABASE_URL set : {str(db_url_present).lower()}")
    print()

    rid = await db_adapter.latest_report_id()
    if rid is None:
        print("No report found in the database.")
        sys.exit(1)

    print(f"Latest report_id : {rid}")

    report = await db_adapter.load_report(rid)
    if report is None:
        print(f"Report {rid} could not be loaded.")
        sys.exit(1)

    facts = await db_adapter.list_report_facts(rid)

    print(f"generated_at     : {report.generated_at}")
    print(f"pulse_score      : {report.pulse_score}")
    print(f"pulse_status     : {report.pulse_status.value if report.pulse_status else 'N/A'}")
    print(f"quality_status   : {report.quality_status.value if report.quality_status else 'N/A'}")
    print(f"evidence_count   : {report.evidence_count}")
    print(f"source_count     : {report.source_count}")
    print(f"fact rows loaded : {len(facts)}")
    print()
    print("OK — latest report loaded successfully.")


if __name__ == "__main__":
    asyncio.run(main())
