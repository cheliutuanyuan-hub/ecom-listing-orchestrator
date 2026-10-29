"""Offline mock market-signal source + constraint pool. Deterministic."""
from __future__ import annotations

from ..ports.market import MarketSignalSourcePort

# Deterministic, reproducible signals so tests are stable.
_SIGNALS = [
    {
        "id": "sig-trend-1",
        "source": "trend_engine",
        "type": "trend",
        "content": "Rising demand for compact eco-friendly kitchen gadgets in EU market",
        "weight": 0.9,
    },
    {
        "id": "sig-trend-2",
        "source": "trend_engine",
        "type": "trend",
        "content": "Smart home sensors gaining traction among renters",
        "weight": 0.7,
    },
    {
        "id": "sig-comp-1",
        "source": "competitor_feed",
        "type": "competitor_comment",
        "content": "Competitor X praised for fast shipping but criticized for weak packaging",
        "weight": 0.6,
    },
    {
        "id": "sig-comp-2",
        "source": "competitor_feed",
        "type": "competitor_comment",
        "content": "Customers want clearer spec sheets and more scene photos",
        "weight": 0.5,
    },
]

# Constraint pool used by FeasibilityAgent. Pure business data.
_CONSTRAINTS = {
    "cost_budget": 1000.0,
    "inventory_min": 50,
    "compliance_risk_threshold": 0.35,
    "platform_rules": {"max_title_len": 80, "required_fields": ["title", "category", "specs"]},
}


class MockMarket(MarketSignalSourcePort):
    def fetch_signals(self, platform: str) -> list[dict]:
        return [dict(s) for s in _SIGNALS]

    def fetch_constraints(self, platform: str) -> dict:
        return dict(_CONSTRAINTS)
