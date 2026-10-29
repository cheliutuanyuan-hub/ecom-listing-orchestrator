"""GraphState: the mutable state threaded through the LangGraph StateGraph.

Plain TypedDict (no reducers) so each node fully owns the fields it writes.
Conditional routing reads these fields to decide next node.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class GraphState(TypedDict, total=False):
    # --- identity / control ---
    case_id: str
    platform: str
    # Free-form caller input (e.g. {"product_name": "..."}). Carries the real
    # product through the pipeline; without it every case would be a generic
    # demo driven purely by mock market signals.
    meta: dict[str, Any]
    case_status: str
    current_stage: str
    error: Optional[str]

    # --- signal -> selection ---
    signals: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    selected_hypothesis: Optional[dict[str, Any]]
    selection_approved: bool
    selection_review_done: bool

    # --- info structuring ---
    info_structured: Optional[dict[str, Any]]
    pim_id: Optional[str]
    consistency_ok: bool
    info_approved: bool
    info_review_done: bool

    # --- visual production ---
    visual_results: list[dict[str, Any]]
    visual_approved: bool
    visual_review_done: bool

    # --- compliance ---
    compliance_status: Optional[dict[str, Any]]
    compliance_approved: bool
    compliance_review_done: bool

    # --- critic / replan ---
    critic_flags: list[dict[str, Any]]
    replan_attempts: int
    replan_target: str
    reflections: list[str]  # accumulated reflection texts across replans

    # --- terminal ---
    listing_result: Optional[dict[str, Any]]
    feedback: Optional[dict[str, Any]]
    evidence_scores: Optional[dict[str, float]]


def initial_state(case_id: str, platform: str, meta: Optional[dict[str, Any]] = None) -> GraphState:
    return GraphState(
        case_id=case_id,
        platform=platform,
        meta=dict(meta or {}),
        case_status="RUNNING",
        current_stage="",
        error=None,
        signals=[],
        hypotheses=[],
        selected_hypothesis=None,
        selection_approved=False,
        selection_review_done=False,
        info_structured=None,
        pim_id=None,
        consistency_ok=False,
        info_approved=False,
        info_review_done=False,
        visual_results=[],
        visual_approved=False,
        visual_review_done=False,
        compliance_status=None,
        compliance_approved=False,
        compliance_review_done=False,
        critic_flags=[],
        replan_attempts=0,
        replan_target="",
        reflections=[],
        listing_result=None,
        feedback=None,
        evidence_scores=None,
    )
