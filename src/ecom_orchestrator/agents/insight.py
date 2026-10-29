"""InsightAgent: aggregates mock market signals -> opportunity hypotheses
with explicit source references.
"""
from __future__ import annotations

from ..domain.models import AgentResult, Stage
from .base import BaseAgent


class InsightAgent(BaseAgent):
    name = "insight_agent"
    stage = Stage.SIGNAL_ANALYSIS

    def run(self, container, state: dict) -> dict:
        case_id = state["case_id"]
        platform = state.get("platform", "global")
        signals = container.market.fetch_signals(platform)

        hypotheses = []
        idx = 0
        for sig in signals:
            if sig.get("type") != "trend":
                # competitor comments inform confidence but are not standalone trends
                continue
            idx += 1
            hid = f"hyp-{idx}"
            hypothesis = {
                "id": hid,
                "title": self._title_from(sig["content"]),
                "rationale": sig["content"],
                "source_refs": [
                    {"signal_id": sig["id"], "source": sig["source"], "weight": sig["weight"]}
                ],
                "opportunity_score": round(float(sig.get("weight", 0.5)), 3),
                "metrics": self._mock_metrics(idx),
            }
            hypotheses.append(hypothesis)

        # competitor comments attached as cross-evidence to the top hypothesis
        comp_comments = [s for s in signals if s.get("type") == "competitor_comment"]
        if hypotheses and comp_comments:
            hypotheses[0]["source_refs"].extend(
                [{"signal_id": c["id"], "source": c["source"], "weight": c["weight"]}
                 for c in comp_comments]
            )

        self.trace_call(container, case_id, "agent", {
            "signals_count": len(signals),
            "hypotheses_count": len(hypotheses),
        })
        return AgentResult(
            agent=self.name,
            stage=self.stage.value,
            ok=bool(hypotheses),
            data={"signals": signals, "hypotheses": hypotheses},
            message=f"aggregated {len(hypotheses)} hypotheses from {len(signals)} signals",
        )

    @staticmethod
    def _title_from(content: str) -> str:
        # Deterministic, ASCII-safe title from the signal content.
        words = [w for w in content.replace(",", " ").split() if w][:8]
        return "Opportunity: " + " ".join(words).capitalize()

    @staticmethod
    def _mock_metrics(idx: int) -> dict:
        # Stable pseudo-metrics so feasibility is deterministic & passes checks.
        return {
            "cost": 600 + idx * 40,
            "inventory": max(60, 90 - idx * 10),
            "compliance_risk": max(0.05, 0.25 - idx * 0.03),
        }
