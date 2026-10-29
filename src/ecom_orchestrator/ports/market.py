"""Market-signal source + constraint pool port. Default wiring uses MockMarket."""
from __future__ import annotations

from abc import ABC, abstractmethod


class MarketSignalSourcePort(ABC):
    @abstractmethod
    def fetch_signals(self, platform: str) -> list[dict]:
        """Return raw market signals.

        Each signal: {"id", "source", "type" ("trend"|"competitor_comment"),
        "content", "weight" (float 0..1)}.
        """

    @abstractmethod
    def fetch_constraints(self, platform: str) -> dict:
        """Return the multi-constraint pool used by the FeasibilityAgent.

        Shape: {"cost_budget": float, "inventory_min": int,
        "compliance_risk_threshold": float, "platform_rules": {"max_title_len": int}}.
        """
