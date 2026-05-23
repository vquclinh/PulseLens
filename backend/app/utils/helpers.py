# Shared utilities — UUID generation, ISO date helpers, URL domain extraction, text cleaning
import uuid
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def new_id() -> str:
    pass


def now_iso() -> str:
    pass


def days_since(date_str: str) -> int:
    pass


def extract_domain(url: str) -> str:
    pass


def clean_text(html: str) -> str:
    pass
