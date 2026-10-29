"""CriticAgent: cross-validates the work of other agents.

Checks (flag order: rule flags -> info_eval flags -> alignment flags):
  1. Insight conclusion vs Feasibility constraints
     (selected hypothesis must have an acceptable feasibility score).
  2. Visual assets vs Info selling points
     (key selling points must be carried by at least one visual asset).
  3. LLM-as-judge evaluation of info_structured (InfoEvaluator), appended
     after the deterministic rule flags.
  4. Visual content alignment: each visual result's ``alignment_score``
     (computed by Project B) must pass; a missing score is a warning.

Returns a list of flags. A flag with severity "critical" triggers REPLAN.
"""
from __future__ import annotations

from ..domain.models import AgentResult, Stage
from .base import BaseAgent
from .evaluator import InfoEvaluator

FEASIBILITY_PASS = 0.5
ALIGNMENT_PASS = 0.6


class CriticAgent(BaseAgent):
    name = "critic_agent"
    stage = Stage.COMPLIANCE_CHECK  # critic runs right after compliance

    def run(self, container, state: dict) -> dict:
        case_id = state["case_id"]
        flags = []

        # (1) Insight vs Feasibility
        selected = state.get("selected_hypothesis") or {}
        feas = selected.get("feasibility", {})
        score = float(feas.get("score", 1.0))
        if score < FEASIBILITY_PASS:
            flags.append({
                "kind": "feasibility",
                "severity": "critical",
                "message": f"Selected hypothesis {selected.get('id')} feasibility {score} < {FEASIBILITY_PASS}",
            })

        # (2) Visual assets vs Info selling points
        info = state.get("info_structured") or {}
        selling_points = info.get("selling_points", [])
        visuals = state.get("visual_results", [])
        if not visuals:
            flags.append({
                "kind": "visual",
                "severity": "critical",
                "message": "No visual assets were produced",
            })
        else:
            carried = [v.get("carries_selling_point") for v in visuals if v.get("carries_selling_point")]
            for sp in selling_points:
                if not any(sp == c for c in carried):
                    flags.append({
                        "kind": "visual",
                        "severity": "warning",
                        "message": f"Selling point not represented in any visual: {sp}",
                    })

        # (3) LLM-as-judge evaluation (rule flags take precedence; these append).
        eval_res = InfoEvaluator().run(container, state)
        flags.extend(eval_res.data["info_eval_flags"])

        # (4) Visual alignment (from Project B's AlignmentChecker).
        for v in visuals:
            align = v.get("alignment_score")
            if align is None:
                flags.append({
                    "kind": "visual_alignment",
                    "severity": "warning",
                    "message": f"visual alignment missing for {v.get('image_type')}",
                })
            elif float(align) < ALIGNMENT_PASS:
                flags.append({
                    "kind": "visual_alignment",
                    "severity": "critical",
                    "message": f"visual alignment {align} < {ALIGNMENT_PASS} for {v.get('image_type')}",
                })

        critical = [f for f in flags if f.get("severity") == "critical"]
        self.trace_call(container, case_id, "agent", {
            "flags": len(flags),
            "critical": len(critical),
        })
        return AgentResult(
            agent=self.name,
            stage=self.stage.value,
            ok=not critical,
            data={"critic_flags": flags},
            message=f"{len(critical)} critical flags; {len(flags)} total",
        )
