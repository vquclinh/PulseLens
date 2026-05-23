# Company universe — 8 tracked AI hardware companies with metadata
from dataclasses import dataclass
from typing import Optional


@dataclass
class Company:
    name: str
    ticker: str
    domain: str
    ir_url: str
    careers_url: str
    description: str


COMPANIES: list = []
