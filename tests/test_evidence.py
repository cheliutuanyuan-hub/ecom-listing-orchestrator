"""T5: three-dimension evidence scoring wired into the full case."""

from __future__ import annotations

from ecom_orchestrator.quality.evidence import compute_evidence_scores


def test_compute_evidence_scores_complete_case():
    state = {
        "info_structured": {"title": "x"},
        "visual_results": [{"alignment_score": 1.0}],
        "compliance_status": {"safety_level": "low"},
        "listing_result": {"title": "x"},
        "compliance_approved": True,
        "critic_flags": [],
        "replan_attempts": 0,
    }
    scores = compute_evidence_scores(state)
    assert scores["completeness"] == 1.0
    assert scores["safety"] == 1.0
    assert scores["robustness"] == 1.0
    assert all(v > 0.5 for v in scores.values())


def test_compute_evidence_penalizes_replan_and_low_alignment():
    state = {
        "info_structured": {"title": "x"},
        "visual_results": [{"alignment_score": 0.4}],
        "compliance_status": {"safety_level": "high"},
        "listing_result": None,
        "compliance_approved": False,
        "critic_flags": [{"severity": "critical", "kind": "visual_alignment"}],
        "replan_attempts": 2,
    }
    scores = compute_evidence_scores(state)
    assert scores["robustness"] == 0.2  # 0.4 - 0.1 * 2 replans
    assert scores["safety"] == 0.0  # compliance not approved + critical flags
    assert scores["completeness"] == 0.75  # listing_result missing at critic time


def test_full_case_listing_contains_evidence(service):
    summary = service.start_case("global", {"source": "test"}, auto_approve=True)
    assert summary["status"] == "CLOSED", summary
    snap = service.snapshot_repo.get(summary["case_id"])
    assert snap is not None
    listing = snap["listing_result"]
    assert listing is not None
    evidence = listing["evidence"]
    assert set(evidence.keys()) == {"completeness", "safety", "robustness"}
    assert all(isinstance(v, float) for v in evidence.values())


def test_full_case_records_tool_call_traces(service):
    summary = service.start_case("global", {"source": "test"}, auto_approve=True)
    assert summary["status"] == "CLOSED", summary
    trace = service.trace_repo.get_trace(summary["case_id"])
    tool_calls = [t for t in trace if t["kind"] == "tool_call"]
    actors = {t["actor"] for t in tool_calls}
    assert "visual_service" in actors, "visual service call must be traced"
    assert "pim" in actors, "pim save must be traced"

    visual_call = [t for t in tool_calls if t["actor"] == "visual_service"][0]
    payload = visual_call["payload"]
    assert payload["status"] == "ok"
    assert "duration_ms" in payload
    assert payload["response"], "expected a sampled tool response"
    assert "alignment_score" in payload["response"][0]

    pim_call = [t for t in tool_calls if t["actor"] == "pim"][0]
    assert pim_call["payload"]["status"] == "ok"
    assert pim_call["payload"]["pim_id"]
