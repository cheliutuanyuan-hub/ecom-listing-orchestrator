"""ComplianceAgent: platform rule + forbidden-terms check.

Monotonic safety: it may RAISE the safety level, never lower it. The caller
(ComplianceAgent node) holds the prior level and applies SafetyLevel.max.
"""
from __future__ import annotations

from ..domain.models import AgentResult, SafetyLevel, Stage
from .base import BaseAgent


class ComplianceAgent(BaseAgent):
    name = "compliance_agent"
    stage = Stage.COMPLIANCE_CHECK

    def run(self, container, state: dict) -> dict:
        case_id = state["case_id"]
        platform = state.get("platform", "global")
        info = state.get("info_structured") or {}
        prior_level = state.get("compliance_status", {}).get("safety_level") if state.get("compliance_status") else None

        payload = {
            "title": info.get("title", ""),
            "selling_points": info.get("selling_points", []),
            "description": info.get("description", ""),
        }
        evaluated = container.compliance.evaluate(payload, platform)

        # Monotonic: never lower a previously raised safety level.
        level = SafetyLevel(evaluated["safety_level"])
        if prior_level:
            level = SafetyLevel.max(level, SafetyLevel(prior_level))
        evaluated["safety_level"] = level.value

        self.trace_call(container, case_id, "agent", {
            "safety_level": level.value,
            "violations": len(evaluated.get("violations", [])),
            "requires_escalation": evaluated.get("requires_escalation", False),
        })
        return AgentResult(
            agent=self.name,
            stage=self.stage.value,
            ok=not evaluated.get("requires_escalation", False),
            data={"compliance_status": evaluated},
            message=f"safety_level={level.value}; escalation={evaluated.get('requires_escalation')}",
        )
