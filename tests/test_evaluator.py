"""T2: InfoEvaluator LLM-as-judge scoring (deterministic offline path)."""

from __future__ import annotations

from ecom_orchestrator.agents.evaluator import InfoEvaluator

HEALTHY_INFO = {
    "title": "Eco Product | Verified Listing",
    "category": "general",
    "specs": {"material": "eco_alloy"},
    # Two traceable selling points => factuality reaches 1.0 (0.5 each).
    "selling_points": ["Eco-friendly materials", "High customer satisfaction"],
    "description": "desc",
}


def test_info_evaluator_scores_healthy_info(service):
    state = {
        "case_id": "c1",
        "info_structured": HEALTHY_INFO,
        "selected_hypothesis": {
            "id": "h1",
            "rationale": "eco-friendly materials drive customer satisfaction",
        },
    }
    r = InfoEvaluator().run(service.container, state)
    scores = r.data["info_eval_scores"]
    assert all(scores[d] >= 0.6 for d in ("factuality", "coverage", "compliance"))
    critical = [f for f in r.data["info_eval_flags"] if f.get("severity") == "critical"]
    assert not critical, r.data["info_eval_flags"]


def test_info_evaluator_flags_missing_fields(service):
    state = {
        "case_id": "c1",
        # Only title + selling_points present => coverage 2/5 = 0.4 < 0.6.
        "info_structured": {
            "title": "Eco Product | Verified Listing",
            "selling_points": ["Eco-friendly materials"],
        },
        "selected_hypothesis": {
            "id": "h1",
            "rationale": "eco-friendly materials drive customer satisfaction",
        },
    }
    r = InfoEvaluator().run(service.container, state)
    scores = r.data["info_eval_scores"]
    assert scores["coverage"] < 0.6
    flags = r.data["info_eval_flags"]
    cov_flags = [f for f in flags if f.get("dimension") == "coverage"]
    assert cov_flags, f"expected a coverage flag: {flags}"
    assert cov_flags[0]["severity"] == "warning"  # coverage is a warning, not critical


def test_info_evaluator_flags_forbidden_title(service):
    state = {
        "case_id": "c1",
        "info_structured": {
            **HEALTHY_INFO,
            "title": "最好用 Product | Verified Listing",  # contains forbidden term 最
        },
        "selected_hypothesis": {
            "id": "h1",
            "rationale": "eco-friendly materials drive customer satisfaction",
        },
    }
    r = InfoEvaluator().run(service.container, state)
    scores = r.data["info_eval_scores"]
    assert scores["compliance"] == 0.0
    flags = r.data["info_eval_flags"]
    critical = [f for f in flags if f.get("severity") == "critical"]
    assert any(f.get("dimension") == "compliance" for f in critical)
    assert r.ok is False
