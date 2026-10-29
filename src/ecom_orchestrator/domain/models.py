"""Pure domain models for the listing-production state machine.

No I/O, no framework imports. These types are the contract shared between the
orchestration graph, the agents, and the persistence layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Stage(str, Enum):
    """Production-line stages (nodes of the state machine)."""

    SIGNAL_ANALYSIS = "SIGNAL_ANALYSIS"
    SELECTION_REVIEW = "SELECTION_REVIEW"
    INFO_STRUCTURING = "INFO_STRUCTURING"
    VISUAL_PRODUCTION = "VISUAL_PRODUCTION"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    LISTING = "LISTING"
    FEEDBACK = "FEEDBACK"
    REPLAN = "REPLAN"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    CLOSED = "CLOSED"

    @classmethod
    def main_path(cls):
        """Stages expected on a healthy auto-approved run."""
        return [
            cls.SIGNAL_ANALYSIS,
            cls.SELECTION_REVIEW,
            cls.INFO_STRUCTURING,
            cls.VISUAL_PRODUCTION,
            cls.COMPLIANCE_CHECK,
            cls.LISTING,
            cls.FEEDBACK,
        ]


class CaseStatus(str, Enum):
    RUNNING = "RUNNING"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    CLOSED = "CLOSED"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"


class SafetyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def max(cls, a: "SafetyLevel", b: "SafetyLevel") -> "SafetyLevel":
        order = [cls.LOW, cls.MEDIUM, cls.HIGH]
        return a if order.index(a) >= order.index(b) else b


class Decision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class Gate(str, Enum):
    SELECTION_REVIEW = "SELECTION_REVIEW"
    INFO_STRUCTURING = "INFO_STRUCTURING"
    VISUAL = "VISUAL"
    COMPLIANCE = "COMPLIANCE"


@dataclass
class AgentResult:
    """Structured result returned by an agent run."""

    agent: str
    stage: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "stage": self.stage,
            "ok": self.ok,
            "data": self.data,
            "message": self.message,
        }


@dataclass
class Case:
    """Top-level case aggregate (thin wrapper around identifiers)."""

    case_id: str
    platform: str
    status: str = CaseStatus.RUNNING.value
    meta: dict[str, Any] = field(default_factory=dict)


def new_case_id() -> str:
    import uuid

    return "case-" + uuid.uuid4().hex[:12]
