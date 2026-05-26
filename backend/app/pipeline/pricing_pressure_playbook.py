"""Deterministic pricing_pressure query playbook for the demo scope."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.schemas.models import SearchQuery, SignalType
from app.utils.helpers import generate_uuid


@dataclass(frozen=True)
class PricingPlaybookQuery:
    template_id: str
    family: str
    target_entity: str
    query_text: str
    source_type: str
    expected_source_tier: int
    priority: int = 1


DEMO_PRICING_COMPANIES = {"Nvidia", "AMD", "Supermicro"}


def pricing_time_anchor(time_window: str) -> str:
    normalized = (time_window or "").strip().lower()
    if normalized and normalized not in {"last 7 days", "last seven days"}:
        return time_window
    return datetime.now().strftime("%B %Y")


def build_pricing_playbook_specs(
    companies: list[str],
    time_window: str,
    *,
    include_market: bool = True,
) -> list[PricingPlaybookQuery]:
    anchor = pricing_time_anchor(time_window)
    selected = [company for company in companies if company in DEMO_PRICING_COMPANIES]
    specs: list[PricingPlaybookQuery] = []

    if "Nvidia" in selected:
        specs.extend([
            PricingPlaybookQuery(
                template_id="nvda_aws_h100_h200_pricing",
                family="cloud_pricing",
                target_entity="Nvidia",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"site:aws.amazon.com/ec2 Nvidia H100 H200 GPU instance pricing availability {anchor}",
            ),
            PricingPlaybookQuery(
                template_id="nvda_azure_nc_h100_pricing",
                family="cloud_pricing",
                target_entity="Nvidia",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"site:azure.microsoft.com Nvidia H100 H200 GPU VM pricing availability {anchor}",
            ),
            PricingPlaybookQuery(
                template_id="nvda_coreweave_blackwell_availability",
                family="cloud_pricing",
                target_entity="Nvidia",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"CoreWeave Nvidia H100 H200 B200 Blackwell GPU cloud pricing availability {anchor}",
            ),
            PricingPlaybookQuery(
                template_id="nvda_lambda_runpod_gpu_pricing",
                family="cloud_pricing",
                target_entity="Nvidia",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"Lambda Labs RunPod Nvidia H100 H200 L40S GPU pricing availability {anchor}",
            ),
        ])

    if "AMD" in selected:
        specs.extend([
            PricingPlaybookQuery(
                template_id="amd_azure_mi300x_pricing",
                family="cloud_pricing",
                target_entity="AMD",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"site:azure.microsoft.com AMD Instinct MI300X MI325X GPU VM pricing availability {anchor}",
            ),
            PricingPlaybookQuery(
                template_id="amd_oracle_mi300x_availability",
                family="cloud_pricing",
                target_entity="AMD",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"Oracle Cloud AMD Instinct MI300X MI325X GPU instance pricing availability {anchor}",
            ),
            PricingPlaybookQuery(
                template_id="amd_dell_mi300x_server_availability",
                family="oem_distributor",
                target_entity="AMD",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"AMD MI300X MI325X Instinct AI server pricing availability Dell Supermicro {anchor}",
            ),
            PricingPlaybookQuery(
                template_id="amd_mi350_cloud_availability",
                family="pricing_news_context",
                target_entity="AMD",
                source_type="serp_news",
                expected_source_tier=3,
                query_text=f"AMD MI350 MI325X Instinct cloud GPU availability pricing {anchor} Reuters ServeTheHome",
            ),
        ])

    if "Supermicro" in selected:
        specs.extend([
            PricingPlaybookQuery(
                template_id="smci_store_ai_gpu_server",
                family="oem_distributor",
                target_entity="Supermicro",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"site:supermicro.com Supermicro GPU server AI server pricing availability H100 H200 B200 {anchor}",
            ),
            PricingPlaybookQuery(
                template_id="smci_blackwell_server_availability",
                family="oem_distributor",
                target_entity="Supermicro",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"Supermicro Nvidia Blackwell B200 GPU server availability lead time liquid cooling {anchor}",
            ),
            PricingPlaybookQuery(
                template_id="smci_amd_instinct_server_availability",
                family="oem_distributor",
                target_entity="Supermicro",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"Supermicro AMD Instinct MI300 MI325 GPU server availability pricing {anchor}",
            ),
            PricingPlaybookQuery(
                template_id="smci_distributor_gpu_server_pricing",
                family="oem_distributor",
                target_entity="Supermicro",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"Supermicro AI GPU server distributor pricing availability H100 H200 B200 {anchor}",
            ),
        ])

    if include_market:
        specs.extend([
            PricingPlaybookQuery(
                template_id="market_cloud_gpu_price_changes",
                family="pricing_news_context",
                target_entity="market",
                source_type="serp_news",
                expected_source_tier=3,
                query_text=f"cloud GPU rental price changes H100 H200 B200 MI300X {anchor} SemiAnalysis ServeTheHome",
            ),
            PricingPlaybookQuery(
                template_id="market_ai_server_lead_times",
                family="pricing_news_context",
                target_entity="market",
                source_type="serp_news",
                expected_source_tier=3,
                query_text=f"AI server lead times GPU availability supply shortage oversupply {anchor} Reuters Bloomberg",
            ),
            PricingPlaybookQuery(
                template_id="market_gpu_instance_discounts",
                family="cloud_pricing",
                target_entity="market",
                source_type="pricing_pages",
                expected_source_tier=4,
                query_text=f"GPU instance discounts pricing availability H100 H200 L40S MI300X {anchor} AWS Azure Google Cloud",
            ),
        ])

    return specs


def specs_to_search_queries(specs: list[PricingPlaybookQuery]) -> list[SearchQuery]:
    return [
        SearchQuery(
            query_id=f"q_price_{generate_uuid()[:8]}",
            query_text=spec.query_text,
            target_entity=spec.target_entity,
            signal_type=SignalType.pricing_pressure,
            source_type=spec.source_type,
            priority=spec.priority,
            expected_source_tier=spec.expected_source_tier,
        )
        for spec in specs
    ]


def pricing_playbook_audit_payload(
    specs: list[PricingPlaybookQuery],
    queries: list[SearchQuery],
) -> list[dict[str, object]]:
    return [
        {
            "query_id": query.query_id,
            "template_id": spec.template_id,
            "family": spec.family,
            "target_entity": spec.target_entity,
            "source_type": spec.source_type,
            "query_text": spec.query_text,
        }
        for spec, query in zip(specs, queries)
    ]
