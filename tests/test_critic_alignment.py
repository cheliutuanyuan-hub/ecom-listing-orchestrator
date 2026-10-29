"""T3: Critic consumes visual alignment scores + info evaluation flags."""

from __future__ import annotations

from ecom_orchestrator.agents.critic import CriticAgent

HEALTHY_INFO = {
    "title": "Eco Product | Verified Listing",
    "category": "general",
    "specs": {"material": "eco_alloy"},
    "selling_points": ["Eco-friendly materials", "High customer satisfaction"],
    "description": "desc",
}

HEALTHY_RATIONALE = "eco-friendly materials drive customer satisfaction"


def test_critic_flags_low_alignment(service):
    state = {
        "case_id": "c1",
        "info_structured": HEALTHY_INFO,
        "selected_hypothesis": {"id": "h1", "rationale": HEALTHY_RATIONALE},
        "visual_results": [
            {
                "image_type": "main",
                "carries_selling_point": "Eco-friendly materials",
                "alignment_score": 0.4,
            }
        ],
    }
    r = CriticAgent().run(service.container, state)
    flags = r.data["critic_flags"]
    crit = [f for f in flags if f["kind"] == "visual_alignment" and f["severity"] == "critical"]
    assert crit, f"expected critical visual_alignment flag: {flags}"
    assert "main" in crit[0]["message"]
    assert "0.4" in crit[0]["message"]


def test_critic_ok_on_high_alignment(service):
    state = {
        "case_id": "c1",
        "info_structured": HEALTHY_INFO,
        "selected_hypothesis": {"id": "h1", "rationale": HEALTHY_RATIONALE},
        "visual_results": [
            {
                "image_type": "main",
                "carries_selling_point": "Eco-friendly materials",
                "alignment_score": 0.95,
            }
        ],
    }
    r = CriticAgent().run(service.container, state)
    flags = r.data["critic_flags"]
    assert not [f for f in flags if f["kind"] == "visual_alignment"], flags


def test_critic_missing_alignment_warns(service):
    state = {
        "case_id": "c1",
        "info_structured": HEALTHY_INFO,
        "selected_hypothesis": {"id": "h1", "rationale": HEALTHY_RATIONALE},
        "visual_results": [
            {"image_type": "detail", "carries_selling_point": "Eco-friendly materials"}
        ],
    }
    r = CriticAgent().run(service.container, state)
    flags = r.data["critic_flags"]
    warns = [f for f in flags if f["kind"] == "visual_alignment" and f["severity"] == "warning"]
    assert warns, f"expected alignment-missing warning: {flags}"


def test_critic_includes_info_eval_flags(service):
    state = {
        "case_id": "c1",
        # Missing fields + rationale that does not support the selling point.
        "info_structured": {"title": "Untraceable Product | Verified Listing"},
        "selected_hypothesis": {"id": "h1", "rationale": "something unrelated"},
        "visual_results": [],
    }
    r = CriticAgent().run(service.container, state)
    flags = r.data["critic_flags"]
    info_eval = [f for f in flags if f.get("kind") == "info_eval"]
    assert info_eval, f"expected info_eval flags: {flags}"
    dims = {f.get("dimension") for f in info_eval}
    assert "coverage" in dims
