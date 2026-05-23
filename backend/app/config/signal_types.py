# Signal type weights and query templates used across pipeline modules
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

QUERY_TEMPLATES: dict[str, list[str]] = {
    "hiring_momentum": [
        "{company} AI infrastructure job openings {year}",
        "{company} hiring data center engineering roles",
        "{company} workforce expansion {quarter}",
    ],
    "product_launch": [
        "{company} new AI hardware product announcement {year}",
        "{company} product launch press release",
    ],
    "pricing_pressure": [
        "AI server pricing discount {year}",
        "{company} GPU price reduction competitor",
        "cloud GPU on-demand pricing {company}",
    ],
    "strategic_messaging": [
        "{company} AI strategy investor day {year}",
        "{company} CEO earnings call AI infrastructure",
    ],
    "investor_signal": [
        "{company} SEC 8-K filing {quarter} {year}",
        "{company} earnings guidance revision",
    ],
    "news_sentiment": [
        "{company} AI hardware news last 7 days",
        "{company} semiconductor market position {year}",
    ],
    "supplier_risk": [
        "{company} supply chain disruption {year}",
        "{company} supplier concentration risk",
    ],
}
