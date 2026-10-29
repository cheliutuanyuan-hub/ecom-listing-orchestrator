"""HITL gate helpers using langgraph.types.interrupt.

When ``auto_approve`` is enabled (LISTING_AUTO_APPROVE or run-time param) the
gate is skipped and "approve" is returned without suspending the graph.
Otherwise ``interrupt`` suspends the graph and the resume value (a decision
string) is returned to the caller, which resumes via Command(resume=...).
"""
from __future__ import annotations

from langgraph.types import interrupt

from ..domain.models import Decision, Gate


def request_approval(container, gate: Gate | str, payload: dict) -> str:
    """Return a decision string: 'approve' or 'reject'."""
    if container.config.auto_approve:
        return Decision.APPROVE.value
    decision = interrupt({"gate": str(gate), "payload": payload})
    if isinstance(decision, dict):
        decision = decision.get("decision", "approve")
    if str(decision).lower() not in ("approve", "reject"):
        decision = "approve"
    return str(decision).lower()
