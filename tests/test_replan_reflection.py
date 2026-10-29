"""T4: REPLAN reflects critical failures into the next generation round."""

from __future__ import annotations

from ecom_orchestrator.agents.visual import VisualAgent
from ecom_orchestrator.orchestration.replan import replan_policy


def test_replan_generates_reflection_from_critical_flags():
    state = {
        "critic_flags": [
            {
                "kind": "visual_alignment",
                "severity": "critical",
                "message": "visual alignment 0.4 < 0.6 for main",
            }
        ],
        "replan_attempts": 0,
    }
    up = replan_policy(state, 2)
    assert up["reflections"], "expected a reflection"
    assert "visual_alignment" in up["reflections"][-1]
    assert "0.4" in up["reflections"][-1]


def test_replan_accumulates_reflections_across_attempts():
    state = {
        "critic_flags": [
            {"kind": "feasibility", "severity": "critical", "message": "score low"}
        ],
        "replan_attempts": 1,
        "reflections": ["[visual] first failure"],
    }
    up = replan_policy(state, 2)
    assert len(up["reflections"]) == 2
    assert up["reflections"][0] == "[visual] first failure"
    assert "[feasibility]" in up["reflections"][1]


def test_visual_plan_injects_latest_reflection():
    agent = VisualAgent()
    plan = agent.build_plan(["便携"], ["最"], reflections=["[visual] low alignment"])
    assert len(plan) == 3
    for item in plan:
        # The reflection text is injected (deduped) as a required element.
        injected = [el for el in item["required_elements"] if "low alignment" in el]
        assert injected, item["required_elements"]
        # Original selling-point element is preserved.
        assert "便携" in item["required_elements"]
        # Deduplication holds: no duplicate elements.
        assert len(item["required_elements"]) == len(set(item["required_elements"]))


def test_visual_plan_without_reflections_unchanged():
    agent = VisualAgent()
    plan = agent.build_plan(["便携"], ["最"])
    for item in plan:
        assert item["required_elements"] == [item["selling_point"]]
