"""REPLAN policy and routing.

When the Critic flags a critical issue the graph routes to REPLAN, which
increments ``replan_attempts`` and adjusts state (drops/lowers the failing
item) then re-enters the relevant stage. If attempts exceed MAX_REPLAN the case
is routed to HUMAN_ESCALATION (terminal).
"""
from __future__ import annotations

from ..domain.models import Stage


def replan_policy(state: dict, max_replan: int) -> dict:
    """Compute the state updates for a replan step.

    Returns a dict of state fields to merge: incremented ``replan_attempts``,
    ``replan_target`` (stage to re-enter), and adjustments to clear the failing
    work so the re-entered stage re-runs cleanly.
    """
    attempts = int(state.get("replan_attempts", 0)) + 1
    flags = state.get("critic_flags", []) or []

    # Choose the re-entry stage based on the dominant flag kind (lowercase
    # node names, matching the graph's node registry).
    target = "info_structuring"
    for f in flags:
        if f.get("kind") == "visual":
            target = "visual_production"
            break
        if f.get("kind") == "feasibility":
            target = "info_structuring"
            break

    # Drop/lower the failing hypothesis and reset downstream work.
    selected = state.get("selected_hypothesis")
    adjusted_selected = None
    if isinstance(selected, dict):
        adjusted_selected = dict(selected)
        adjusted_selected["priority"] = "low"
        adjusted_selected.setdefault("feasibility", {})
        adjusted_selected["feasibility"]["score"] = min(
            0.5, float(adjusted_selected["feasibility"].get("score", 0.5))
        )

    # Reflection: structure critical failure reasons into reflection texts
    # injected into the next generation round (replaces blind re-weighting).
    reflections = list(state.get("reflections") or [])
    for f in flags:
        if f.get("severity") == "critical":
            kind = f.get("kind")
            msg = f.get("message", "")
            dim = f.get("dimension", "")
            reflections.append(
                f"[{kind}{':' + dim if dim else ''}] {msg}"
            )

    return {
        "replan_attempts": attempts,
        "replan_target": target,
        "reflections": reflections,
        "selected_hypothesis": adjusted_selected,
        "visual_results": [],
        "visual_approved": False,
        "visual_review_done": False,
        "info_approved": False,
        "info_review_done": False,
        "critic_flags": [],
        "current_stage": Stage.REPLAN.value,
    }


def route_after_replan(state: dict, max_replan: int) -> str:
    """Routing function: escalate if too many replans, else re-enter target."""
    if int(state.get("replan_attempts", 0)) > max_replan:
        return "human_escalation"
    return state.get("replan_target") or "info_structuring"
