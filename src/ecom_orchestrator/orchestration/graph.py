"""Builds and compiles the LangGraph StateGraph.

Pipeline: SIGNAL_ANALYSIS -> SELECTION_REVIEW -> INFO_STRUCTURING ->
VISUAL_PRODUCTION -> COMPLIANCE_CHECK -> CRITIC -> LISTING -> FEEDBACK -> CLOSED.

Conditional edges implement the HITL gates (reject -> HUMAN_ESCALATION), the
Critic REPLAN routing, and the REPLAN re-entry / escalation policy.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..domain.models import Stage
from ..domain.state import GraphState, initial_state as _initial_state
from .nodes import GraphContainer, build_nodes
from .replan import route_after_replan


def build_graph(container: GraphContainer):
    nodes = build_nodes(container)

    builder = StateGraph(GraphState)

    for name, fn in nodes.items():
        builder.add_node(name, fn)

    # Linear entry.
    builder.add_edge(START, "signal_analysis")
    builder.add_edge("signal_analysis", "selection_review")

    # HITL gate routing (reject -> human escalation). Node names are lowercase.
    builder.add_conditional_edges(
        "selection_review",
        lambda s: "info_structuring" if s.get("selection_approved") else "human_escalation",
    )
    builder.add_conditional_edges(
        "info_structuring",
        lambda s: "visual_production" if s.get("info_approved") else "human_escalation",
    )
    builder.add_conditional_edges(
        "visual_production",
        lambda s: "compliance_check" if s.get("visual_approved") else "human_escalation",
    )
    builder.add_conditional_edges(
        "compliance_check",
        lambda s: "critic" if s.get("compliance_approved") else "human_escalation",
    )

    # Critic -> REPLAN or LISTING.
    builder.add_conditional_edges(
        "critic",
        lambda s: "replan"
        if any(f.get("severity") == "critical" for f in (s.get("critic_flags") or []))
        else "listing",
    )

    # REPLAN -> re-enter target stage or escalate.
    max_replan = container.config.max_replan

    def _route_replan(s):
        return route_after_replan(s, max_replan)

    builder.add_conditional_edges("replan", _route_replan)

    # Terminal edges.
    builder.add_edge("listing", "feedback")
    builder.add_edge("feedback", END)
    builder.add_edge("human_escalation", END)

    return builder.compile(checkpointer=MemorySaver())


def make_initial_state(case_id: str, platform: str, meta: dict | None = None):
    return _initial_state(case_id, platform, meta)
