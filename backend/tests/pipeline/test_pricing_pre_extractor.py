"""
Sprint 8 — Pricing pre-extractor zero-cost static tests.

Tests for backend/app/pipeline/pricing_pre_extractor.py.
All 14 tests use inline text strings only — zero API calls, zero BrightData calls.

Output: prints PASS/FAIL per test, exits with code 0 (all pass) or 1 (any fail).
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.pipeline.pricing_pre_extractor import (
    PricingCandidate,
    build_pricing_fact,
    count_pricing_patterns,
    extract_pricing_context_windows,
    extract_pricing_facts_from_document,
    infer_gpu_model,
    infer_provider_from_url,
    normalize_price_text,
)
from app.schemas.models import FactObject, RawDocument, SignalType

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

P = "✅ PASS"
F = "❌ FAIL"
_failures: list[str] = []


def _check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  {P}  {label}")
    else:
        msg = label + (f": {detail}" if detail else "")
        print(f"  {F}  {msg}")
        _failures.append(msg)


def _make_doc(content: str, url: str = "https://coreweave.com/pricing",
              signal_hint: SignalType = SignalType.pricing_pressure) -> RawDocument:
    return RawDocument(
        doc_id="doc_test_0001",
        url=url,
        domain="coreweave.com",
        title="GPU Pricing",
        content=content,
        published_date=None,
        fetched_at="2026-05-27T00:00:00Z",
        source_tier=2,
        content_quality="full_text",
        extraction_allowed=True,
        collection_query="coreweave gpu pricing h100",
        signal_type_hint=signal_hint,
    )


# ── T1: H100 $2.49/hr → extract fact, entity=Nvidia ────────────────────────

print("\n── T1: H100 $2.49/hr → fact with entity=Nvidia ────────────────────")
_h100_text = (
    "NVIDIA H100 SXM5 GPU cloud instance available at $2.49/hr on-demand pricing. "
    "Reserved instances from $1.80/hr. The H100 delivers exceptional AI performance. " * 40
)
facts_t1 = extract_pricing_facts_from_document(_make_doc(_h100_text))
_check("T1: at least 1 fact extracted", len(facts_t1) >= 1, f"got {len(facts_t1)}")
if facts_t1:
    _check("T1: entity=Nvidia", facts_t1[0].entity == "Nvidia", f"got {facts_t1[0].entity!r}")
    _check("T1: signal_type=pricing_pressure", facts_t1[0].signal_type == SignalType.pricing_pressure)
    _check("T1: confidence >= 0.75", facts_t1[0].confidence >= 0.75, f"got {facts_t1[0].confidence}")


# ── T2: MI300X $2.20/hr → entity=AMD ───────────────────────────────────────

print("\n── T2: MI300X $2.20/hr → entity=AMD ───────────────────────────────")
_mi300x_text = (
    "AMD MI300X GPU available at $2.20/hr. MI300X instances with 192GB HBM3 memory. "
    "On-demand pricing $2.20 per GPU hour. Reserve for $1.65/hr annually. " * 40
)
facts_t2 = extract_pricing_facts_from_document(
    _make_doc(_mi300x_text, url="https://runpod.io/pricing")
)
_check("T2: at least 1 fact extracted", len(facts_t2) >= 1, f"got {len(facts_t2)}")
if facts_t2:
    _check("T2: entity=AMD", facts_t2[0].entity == "AMD", f"got {facts_t2[0].entity!r}")


# ── T3: L40S $0.76/hr → entity=Nvidia ──────────────────────────────────────

print("\n── T3: L40S $0.76/hr → entity=Nvidia ──────────────────────────────")
_l40s_text = (
    "NVIDIA L40S GPU on-demand at $0.76/hr. L40S 48GB GDDR6 ideal for inference. "
    "L40S spot pricing from $0.55/hr subject to availability. " * 40
)
facts_t3 = extract_pricing_facts_from_document(_make_doc(_l40s_text))
_check("T3: at least 1 fact extracted", len(facts_t3) >= 1, f"got {len(facts_t3)}")
if facts_t3:
    _check("T3: entity=Nvidia", facts_t3[0].entity == "Nvidia", f"got {facts_t3[0].entity!r}")


# ── T4: MI325X explicit price → entity=AMD ──────────────────────────────────

print("\n── T4: MI325X explicit price → entity=AMD ──────────────────────────")
_mi325x_text = (
    "AMD MI325X GPU instances starting at $2.80/hr on-demand. MI325X with 288GB HBM3e. "
    "MI325X reserved pricing available at $2.10/hr for annual commitment. " * 40
)
facts_t4 = extract_pricing_facts_from_document(
    _make_doc(_mi325x_text, url="https://lambdalabs.com/pricing")
)
_check("T4: at least 1 fact extracted", len(facts_t4) >= 1, f"got {len(facts_t4)}")
if facts_t4:
    _check("T4: entity=AMD", facts_t4[0].entity == "AMD", f"got {facts_t4[0].entity!r}")


# ── T5: Supermicro starting price of $12,415 → fact ────────────────────────

print("\n── T5: Supermicro starting price of $12,415 → fact ────────────────")
_smci_text = (
    "Supermicro 1U SuperServer GPU system. Starting price of $12,415. "
    "The 1U SuperServer 112B-WR Intel Xeon 6 SP 1TB DDR5 ECC RDIMM starting price of $12,415. " * 30
)
facts_t5 = extract_pricing_facts_from_document(
    _make_doc(
        _smci_text,
        url="https://www.thinkmate.com/systems/supermicro/superserver/gpu",
        signal_hint=SignalType.pricing_pressure,
    )
)
_check("T5: at least 1 fact extracted", len(facts_t5) >= 1, f"got {len(facts_t5)}")


# ── T6: "contact us for pricing" → no fact ──────────────────────────────────

print("\n── T6: 'contact us for pricing' → no fact ──────────────────────────")
_contact_text = (
    "H100 GPU instances available. Contact us for pricing. "
    "H100 SXM5 enterprise contact us for pricing per GPU hour. " * 40
)
facts_t6 = extract_pricing_facts_from_document(_make_doc(_contact_text))
_check("T6: zero facts (contact-us rejected)", len(facts_t6) == 0, f"got {len(facts_t6)}")


# ── T7: "starting price" without $ amount → no fact ────────────────────────

print("\n── T7: 'starting price' without $ → no fact ────────────────────────")
# Use a non-pricing domain so domain fallback doesn't rescue it,
# and ensure pattern count is low so guard blocks it entirely
_vague_text = (
    "H100 GPU instances available with a starting price based on configuration. "
    "No explicit dollar amounts. Starting price varies by region and spec. " * 5
)
_no_price_doc = RawDocument(
    doc_id="doc_test_0007",
    url="https://example.com/gpu",
    domain="example.com",
    title="GPU",
    content=_vague_text,
    published_date=None,
    fetched_at="2026-05-27T00:00:00Z",
    source_tier=3,
    content_quality="full_text",
    extraction_allowed=True,
    collection_query="gpu pricing",
    signal_type_hint=SignalType.pricing_pressure,
)
facts_t7 = extract_pricing_facts_from_document(_no_price_doc)
_check("T7: zero facts (vague 'starting price' without amount)", len(facts_t7) == 0, f"got {len(facts_t7)}")


# ── T8: Navigation/breadcrumb text → no fact ───────────────────────────────

print("\n── T8: Navigation breadcrumb → no fact ────────────────────────────")
_nav_text = (
    "Home > Products > GPU > Pricing. Breadcrumb navigation pricing page. " * 5
)
_nav_doc = RawDocument(
    doc_id="doc_test_0008",
    url="https://example.com/pricing",
    domain="example.com",
    title="Pricing",
    content=_nav_text,
    published_date=None,
    fetched_at="2026-05-27T00:00:00Z",
    source_tier=3,
    content_quality="snippet_only",
    extraction_allowed=True,
    collection_query="pricing",
    signal_type_hint=SignalType.pricing_pressure,
)
facts_t8 = extract_pricing_facts_from_document(_nav_doc)
_check("T8: zero facts (nav/breadcrumb with no price)", len(facts_t8) == 0, f"got {len(facts_t8)}")


# ── T9: HBM shortage without explicit GPU product → no fact ────────────────

print("\n── T9: HBM shortage no product context → no fact ──────────────────")
_hbm_text = (
    "Global HBM memory shortage is driving up costs. Memory supply constraints continue. "
    "HBM3e costs per unit have risen 30%. Supply chain pressure increasing. " * 5
)
_hbm_doc = RawDocument(
    doc_id="doc_test_0009",
    url="https://example.com/news",
    domain="example.com",
    title="HBM shortage",
    content=_hbm_text,
    published_date=None,
    fetched_at="2026-05-27T00:00:00Z",
    source_tier=3,
    content_quality="full_text",
    extraction_allowed=True,
    collection_query="hbm shortage",
    signal_type_hint=SignalType.supplier_risk,
)
facts_t9 = extract_pricing_facts_from_document(_hbm_doc)
_check("T9: zero facts (HBM shortage no product)", len(facts_t9) == 0, f"got {len(facts_t9)}")


# ── T10: Empty content → returns empty list ─────────────────────────────────

print("\n── T10: Empty content doc → empty list ────────────────────────────")
_empty_doc = RawDocument(
    doc_id="doc_test_0010",
    url="https://coreweave.com/pricing",
    domain="coreweave.com",
    title="Pricing",
    content="",
    published_date=None,
    fetched_at="2026-05-27T00:00:00Z",
    source_tier=2,
    content_quality="snippet_only",
    extraction_allowed=True,
    collection_query="pricing",
    signal_type_hint=SignalType.pricing_pressure,
)
facts_t10 = extract_pricing_facts_from_document(_empty_doc)
_check("T10: empty list for empty content", facts_t10 == [], f"got {facts_t10!r}")


# ── T11: Same H100/$2.49/hr pattern twice → deduplicated to 1 fact ──────────

print("\n── T11: Duplicate price pattern → deduplicated ─────────────────────")
_dedup_text = (
    "H100 GPU at $2.49/hr on-demand. H100 $2.49/hr available now. " * 60
)
facts_t11 = extract_pricing_facts_from_document(_make_doc(_dedup_text))
# Should produce ≥1 but deduplication should keep it bounded
_check("T11: facts produced", len(facts_t11) >= 1, f"got {len(facts_t11)}")
# Check dedup keys are unique by verifying no two facts have identical evidence_quote
quotes_t11 = [f.evidence_quote for f in facts_t11]
_check("T11: no duplicate evidence_quotes", len(quotes_t11) == len(set(quotes_t11)),
       f"duplicate found in {len(quotes_t11)} facts")


# ── T12: evidence_quote <= 280 chars ───────────────────────────────────────

print("\n── T12: evidence_quote <= 280 chars ────────────────────────────────")
_long_text = (
    "NVIDIA H100 SXM5 available at $2.49/hr on-demand. This is an extremely long surrounding "
    "sentence with lots of extra context about data centers and cloud computing. " * 50
)
facts_t12 = extract_pricing_facts_from_document(_make_doc(_long_text))
_check("T12: at least 1 fact", len(facts_t12) >= 1, f"got {len(facts_t12)}")
for i, f in enumerate(facts_t12):
    _check(
        f"T12: fact[{i}] evidence_quote <= 280 chars",
        len(f.evidence_quote) <= 280,
        f"got {len(f.evidence_quote)} chars",
    )


# ── T13: No GPU/product context + non-pricing domain → no fact ───────────────

print("\n── T13: Non-pricing domain, no GPU model → no fact ─────────────────")
_generic_text = (
    "Premium service available at $9.99/month subscription plan. "
    "Enterprise pricing at $199/month with annual billing option. " * 20
)
_generic_doc = RawDocument(
    doc_id="doc_test_0013",
    url="https://someservice.com/pricing",
    domain="someservice.com",
    title="Pricing",
    content=_generic_text,
    published_date=None,
    fetched_at="2026-05-27T00:00:00Z",
    source_tier=3,
    content_quality="full_text",
    extraction_allowed=True,
    collection_query="gpu pricing",
    signal_type_hint=SignalType.news_sentiment,  # NOT pricing_pressure
)
facts_t13 = extract_pricing_facts_from_document(_generic_doc)
_check("T13: zero facts (no GPU context, non-pricing domain)", len(facts_t13) == 0,
       f"got {len(facts_t13)}")


# ── T14: Returns list of FactObject instances ────────────────────────────────

print("\n── T14: Returns list[FactObject] schema-compatible instances ────────")
_schema_text = (
    "H100 SXM5 GPU available at $2.49 per GPU hour on CoreWeave cloud. "
    "H200 instances at $3.20/hr. L40S at $0.76/hr for inference workloads. " * 40
)
facts_t14 = extract_pricing_facts_from_document(_make_doc(_schema_text))
_check("T14: returns list", isinstance(facts_t14, list), f"got {type(facts_t14)}")
for i, f in enumerate(facts_t14):
    _check(f"T14: fact[{i}] is FactObject", isinstance(f, FactObject), f"got {type(f)}")
    _check(f"T14: fact[{i}].signal_type=pricing_pressure",
           f.signal_type == SignalType.pricing_pressure)
    _check(f"T14: fact[{i}].source_url set", bool(f.source_url))
    _check(f"T14: fact[{i}].claim <= 150 chars", len(f.claim) <= 150, f"got {len(f.claim)}")
    _check(f"T14: fact[{i}].confidence in [0,1]", 0.0 <= f.confidence <= 1.0)


# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'─' * 60}")
if _failures:
    print(f"❌ {len(_failures)} test(s) FAILED:")
    for msg in _failures:
        print(f"   • {msg}")
    sys.exit(1)
else:
    print("✅ All 14 pricing pre-extractor tests passed")
    sys.exit(0)
