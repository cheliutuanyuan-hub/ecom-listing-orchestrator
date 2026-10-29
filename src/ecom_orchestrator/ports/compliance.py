"""Compliance rule port. Default wiring uses RuleCompliance (offline rules)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class ComplianceRulePort(ABC):
    @abstractmethod
    def check_text(self, text: str, platform: str) -> dict:
        """Scan a piece of text for forbidden terms.

        Returns {"violations": [{"term", "position"}], "hit": bool}.
        """

    @abstractmethod
    def evaluate(self, payload: dict, platform: str) -> dict:
        """Evaluate a full listing payload (title, selling_points, description).

        Returns {"violations": [...], "safety_level": "low"|"medium"|"high",
        "requires_escalation": bool}.
        """
