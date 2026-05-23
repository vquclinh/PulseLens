# Shared utilities — UUID generation, ISO date helpers, URL domain extraction, HTML cleaning
import uuid
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def generate_uuid() -> str:
    return str(uuid.uuid4()).replace("-", "")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def days_since(date_str: str) -> int:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return max(0, delta.days)
    except Exception:
        return 0


def extract_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host.lstrip("www.")
    except Exception:
        return ""


def clean_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# Aliases used in existing pipeline stubs
new_id = generate_uuid
clean_text = clean_html
