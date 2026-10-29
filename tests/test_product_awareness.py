"""Product-aware structuring.

Regression guard for a real bug: ``meta["product_name"]`` was accepted by
``CaseService.start_case`` but never reached the graph state, so every case was
driven purely by the hard-coded mock market signals. With a real image provider
that surfaced as pictures of a completely different product (a T-shirt rendered
as a storage box), because the selling points came from mock market text.
"""

from __future__ import annotations

from ecom_orchestrator.agents.info_structuring import InfoStructuringAgent
from ecom_orchestrator.agents.evaluator import InfoEvaluator
from ecom_orchestrator.domain.state import initial_state

PRODUCT = "夏季纯棉短袖T恤，男女同款，透气速干"


def test_initial_state_keeps_meta():
    state = initial_state("case-1", "tmall", {"product_name": PRODUCT})
    assert state["meta"]["product_name"] == PRODUCT


def test_selling_points_come_from_product_not_market_signal():
    selected = {"id": "hyp-1", "rationale": "compact eco-friendly kitchen gadgets"}
    points = InfoStructuringAgent._make_selling_points(selected, PRODUCT)

    assert points[0] == PRODUCT
    assert any("纯棉" in p for p in points)
    assert any("速干" in p for p in points)
    # The market-signal keywords must not leak into a real product's卖点.
    assert not any("Eco-friendly" in p or "compact" in p.lower() for p in points)


def test_selling_points_fall_back_to_signal_without_product():
    selected = {"id": "hyp-1", "rationale": "compact eco-friendly kitchen gadgets"}
    points = InfoStructuringAgent._make_selling_points(selected, "")
    assert "Eco-friendly materials" in points


def test_title_and_category_use_product_name():
    selected = {"id": "hyp-1", "title": "Kitchen Gadget", "rationale": "kitchen gadgets"}
    assert PRODUCT in InfoStructuringAgent._make_title(selected, PRODUCT)
    assert InfoStructuringAgent._make_category(selected, PRODUCT) == "apparel"


def test_evaluator_does_not_penalise_product_grounded_info():
    """A real product record must not be flagged as unfactual.

    Before the fix, factuality compared selling points against the mock market
    rationale, scoring 0.0 and pushing the case into REPLAN -> HUMAN_ESCALATION.
    """
    info = {
        "title": f"{PRODUCT} | Verified Listing",
        "category": "apparel",
        "specs": {"product_name": PRODUCT},
        "selling_points": [PRODUCT, "100% 纯棉，亲肤透气"],
        "description": "desc",
    }
    selected = {"rationale": "compact eco-friendly kitchen gadgets"}
    scores = InfoEvaluator._score(info, selected)
    assert scores["factuality"] >= 0.6


def test_configured_visual_url_never_silently_falls_back_to_mock(tmp_path, monkeypatch):
    """A broken adapter import must surface, not degrade to mock.

    A syntax error in ``http_visual.py`` was swallowed by ``except Exception``,
    so a deployment with LISTING_VISUAL_SERVICE_URL set produced mock SVG
    artifacts while reporting success.
    """
    import pytest

    from ecom_orchestrator.service import case_service as cs

    monkeypatch.setattr(cs, "HttpVisualClient", None)
    monkeypatch.setattr(cs, "_HTTP_VISUAL_IMPORT_ERROR", SyntaxError("boom"))
    monkeypatch.setenv("LISTING_VISUAL_SERVICE_URL", "http://visual-studio:8011")
    monkeypatch.setenv("LISTING_DB_PATH", str(tmp_path / "l.db"))

    with pytest.raises(RuntimeError, match="failed to import"):
        cs.build_default_service()
