"""End-to-end orchestration: run a full case to CLOSED with HITL auto-approve."""
from __future__ import annotations

from ecom_orchestrator.domain.models import Stage
from ecom_orchestrator.orchestration.replan import replan_policy, route_after_replan


def test_full_case_runs_to_closed(service):
    summary = service.start_case("global", {"source": "test"}, auto_approve=True)
    assert summary["status"] == "CLOSED", summary
    assert summary["visual_results"], "expected non-empty visual_results"

    trace = service.trace_repo.get_trace(summary["case_id"])
    assert trace, "expected trace records"
    stages_seen = {t["stage"] for t in trace}
    for stg in Stage.main_path():
        assert stg.value in stages_seen, f"missing trace stage: {stg.value}"

    # At least one trace entry per agent/action kind.
    kinds = {t["kind"] for t in trace}
    assert "agent" in kinds
    assert "approval" in kinds


def test_replan_policy_increments_and_routes():
    state = {"critic_flags": [{"kind": "feasibility", "severity": "critical"}], "replan_attempts": 0}
    up = replan_policy(state, 2)
    assert up["replan_attempts"] == 1
    assert up["replan_target"] == "info_structuring"

    # Exceeding MAX_REPLAN escalates to HUMAN_ESCALATION.
    state2 = {"critic_flags": [], "replan_attempts": 2}
    up2 = replan_policy(state2, 2)
    assert up2["replan_attempts"] == 3
    assert route_after_replan(up2, 2) == "human_escalation"

    # Within budget, re-enter the target stage.
    assert route_after_replan(up, 2) == "info_structuring"


def test_visual_replan_target_on_visual_flag():
    state = {"critic_flags": [{"kind": "visual", "severity": "critical"}], "replan_attempts": 0}
    up = replan_policy(state, 2)
    assert up["replan_target"] == "visual_production"
