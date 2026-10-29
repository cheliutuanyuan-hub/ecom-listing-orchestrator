"""FeasibilityAgent: scores each hypothesis against a multi-constraint pool
(cost, inventory, compliance risk) and attaches a feasibility score.
"""
from __future__ import annotations

from ..domain.models import AgentResult, Stage
from .base import BaseAgent


class FeasibilityAgent(BaseAgent):
    name = "feasibility_agent"
    stage = Stage.SIGNAL_ANALYSIS

    def run(self, container, state: dict) -> dict:
        case_id = state["case_id"]
        platform = state.get("platform", "global")
        constraints = container.market.fetch_constraints(platform)
        hypotheses = state.get("hypotheses", [])

        scored = [self._score(h, constraints) for h in hypotheses]

        self.trace_call(container, case_id, "agent", {
            "scored": [h["id"] for h in scored],
            "constraints": constraints,
        })
        return AgentResult(
            agent=self.name,
            stage=self.stage.value,
            ok=bool(scored),
            data={"hypotheses": scored},
            message=f"scored {len(scored)} hypotheses",
        )

    def _score(self, h: dict, constraints: dict) -> dict:
        m = h.get("metrics", {})
        budget = float(constraints.get("cost_budget", 1000))
        inv_min = int(constraints.get("inventory_min", 50))
        risk_thr = float(constraints.get("compliance_risk_threshold", 0.35))

        cost = float(m.get("cost", budget))
        inv = int(m.get("inventory", inv_min))
        risk = float(m.get("compliance_risk", 1.0))

        score = 1.0
        if cost > budget:
            score -= 0.4
        if inv < inv_min:
            score -= 0.3
        if risk > risk_thr:
            score -= 0.4
        score = round(max(0.0, min(1.0, score)), 3)

        out = dict(h)
        out["feasibility"] = {
            "score": score,
            "cost_within_budget": cost <= budget,
            "inventory_ok": inv >= inv_min,
            "compliance_risk_ok": risk <= risk_thr,
        }
        return out
