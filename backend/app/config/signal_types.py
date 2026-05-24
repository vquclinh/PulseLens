# Signal type weights, descriptions, and query templates used across pipeline modules
from app.schemas.models import SignalType

SIGNAL_WEIGHTS: dict[str, float] = {
    SignalType.investor_signal.value:      0.25,   # highest — direct financial impact
    SignalType.news_sentiment.value:       0.20,
    SignalType.pricing_pressure.value:     0.18,   # direct margin impact
    SignalType.strategic_messaging.value:  0.15,
    SignalType.hiring_momentum.value:      0.12,
    SignalType.product_launch.value:       0.07,
    SignalType.supplier_risk.value:        0.03,   # low weight but triggers status override
}

SIGNAL_DESCRIPTIONS: dict[str, str] = {
    SignalType.investor_signal.value:      "SEC 8-K/10-K/13F filings, earnings guidance, analyst upgrades",
    SignalType.news_sentiment.value:       "Reuters/Bloomberg/WSJ coverage, analyst reports",
    SignalType.pricing_pressure.value:     "GPU/server pricing, distributor listings, deal announcements",
    SignalType.strategic_messaging.value:  "CEO comments, earnings calls, investor day presentations",
    SignalType.hiring_momentum.value:      "workforce signals on job boards, LinkedIn",
    SignalType.product_launch.value:       "press releases, product pages, IR announcements",
    SignalType.supplier_risk.value:        "supply chain news, component shortages, concentration mentions",
}

QUERY_TEMPLATES: dict[str, list[str]] = {
    SignalType.hiring_momentum.value: [
        "{company} AI infrastructure job openings {year}",
        "{company} hiring data center engineering roles",
        "{company} workforce expansion {quarter}",
    ],
    SignalType.product_launch.value: [
        "{company} new AI hardware product announcement {year}",
        "{company} product launch press release",
    ],
    SignalType.pricing_pressure.value: [
        "AI server pricing discount {year}",
        "{company} GPU price reduction competitor",
        "cloud GPU on-demand pricing {company}",
    ],
    SignalType.strategic_messaging.value: [
        "{company} AI strategy investor day {year}",
        "{company} CEO earnings call AI infrastructure",
    ],
    SignalType.investor_signal.value: [
        "{company} SEC 8-K filing {quarter} {year}",
        "{company} earnings guidance revision",
    ],
    SignalType.news_sentiment.value: [
        "{company} AI hardware news last 7 days",
        "{company} semiconductor market position {year}",
    ],
    SignalType.supplier_risk.value: [
        "{company} supply chain disruption {year}",
        "{company} supplier concentration risk",
    ],
}
