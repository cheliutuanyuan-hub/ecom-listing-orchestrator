"""Node functions that wire agents + ports together.

Each node is a closure over the ``GraphContainer`` (the ports/adapters + repos +
config). Nodes own the HITL gates and the tracing/snapshot side-effects that make
every step traceable, intervenable, and rollbackable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..agents.compliance import ComplianceAgent
from ..agents.critic import CriticAgent
from ..agents.feasibility import FeasibilityAgent
from ..agents.info_structuring import InfoStructuringAgent
from ..agents.insight import InsightAgent
from ..agents.visual import VisualAgent
from ..domain.models import CaseStatus, Gate, Stage
from ..ports.compliance import ComplianceRulePort
from ..ports.llm import LLMProviderPort
from ..ports.market import MarketSignalSourcePort
from ..ports.pim import PIMPort
from ..ports.visual import VisualServicePort
from ..persistence.base import SnapshotRepository, TraceRepository
from ..quality.evidence import compute_evidence_scores
from .gates import request_approval
from .replan import replan_policy

_NODE = Callable[[dict], dict]


@dataclass
class GraphContainer:
    """Composition root wiring ports/adapters for one graph instance."""

    config: Any
    trace_repo: TraceRepository
    snapshot_repo: SnapshotRepository
    market: MarketSignalSourcePort
    llm: LLMProviderPort
    pim: PIMPort
    visual: VisualServicePort
    compliance: ComplianceRulePort


def build_nodes(container: GraphContainer) -> dict[str, _NODE]:
    def _save(state: dict, updates: dict) -> dict:
        merged = {**state, **updates}
        container.snapshot_repo.save(
            merged["case_id"], merged.get("case_status", CaseStatus.RUNNING.value), merged
        )
        return updates

    def _trace_stage(case_id: str, stage: Stage) -> None:
        container.trace_repo.append_trace(
            case_id, stage.value, "orchestrator", "stage_enter", {}
        )

    # ---- SIGNAL_ANALYSIS -------------------------------------------------
    def signal_analysis(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.SIGNAL_ANALYSIS)

        insight = InsightAgent()
        r1 = insight.run(container, state)
        signals = r1.data["signals"]
        hypotheses = r1.data["hypotheses"]

        feas = FeasibilityAgent()
        r2 = feas.run(container, {**state, "hypotheses": hypotheses})
        hypotheses = r2.data["hypotheses"]

        updates = {
            "signals": signals,
            "hypotheses": hypotheses,
            "current_stage": Stage.SIGNAL_ANALYSIS.value,
            "case_status": CaseStatus.RUNNING.value,
        }
        return _save(state, updates)

    # ---- SELECTION_REVIEW (HITL gate) -----------------------------------
    def selection_review(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.SELECTION_REVIEW)
        if not state.get("selection_review_done"):
            hyps = sorted(
                state.get("hypotheses", []),
                key=lambda h: h.get("feasibility", {}).get("score", 0.0),
                reverse=True,
            )
            selected = hyps[0] if hyps else None
            decision = request_approval(
                container, Gate.SELECTION_REVIEW, {"candidate": selected}
            )
            container.trace_repo.append_trace(
                case_id, Stage.SELECTION_REVIEW.value, "gate", "approval",
                {"gate": Gate.SELECTION_REVIEW.value, "decision": decision},
            )
            if decision != "approve":
                return _save(state, {
                    "selected_hypothesis": selected,
                    "selection_approved": False,
                    "selection_review_done": True,
                    "current_stage": Stage.SELECTION_REVIEW.value,
                })
            return _save(state, {
                "selected_hypothesis": selected,
                "selection_approved": True,
                "selection_review_done": True,
                "current_stage": Stage.SELECTION_REVIEW.value,
            })
        return {}

    # ---- INFO_STRUCTURING (HITL gate) -----------------------------------
    def info_structuring(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.INFO_STRUCTURING)
        if not state.get("info_review_done"):
            agent = InfoStructuringAgent()
            res = agent.run(container, state)
            info = res.data["info_structured"]
            pim_id = res.data["pim_id"]
            consistent = res.data["consistency_ok"]
            decision = request_approval(
                container, Gate.INFO_STRUCTURING, {"info": info, "pim_id": pim_id}
            )
            container.trace_repo.append_trace(
                case_id, Stage.INFO_STRUCTURING.value, "gate", "approval",
                {"gate": Gate.INFO_STRUCTURING.value, "decision": decision},
            )
            return _save(state, {
                "info_structured": info,
                "pim_id": pim_id,
                "consistency_ok": consistent,
                "info_approved": decision == "approve",
                "info_review_done": True,
                "current_stage": Stage.INFO_STRUCTURING.value,
            })
        return {}

    # ---- VISUAL_PRODUCTION (HITL gate) ----------------------------------
    def visual_production(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.VISUAL_PRODUCTION)
        if not state.get("visual_review_done"):
            agent = VisualAgent()
            res = agent.run(container, state)
            results = res.data["visual_results"]
            decision = request_approval(
                container, Gate.VISUAL, {"visual_results": results}
            )
            container.trace_repo.append_trace(
                case_id, Stage.VISUAL_PRODUCTION.value, "gate", "approval",
                {"gate": Gate.VISUAL.value, "decision": decision},
            )
            return _save(state, {
                "visual_results": results,
                "visual_approved": decision == "approve",
                "visual_review_done": True,
                "current_stage": Stage.VISUAL_PRODUCTION.value,
            })
        return {}

    # ---- COMPLIANCE_CHECK (HITL gate: approve risk escalation) ----------
    def compliance_check(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.COMPLIANCE_CHECK)
        if not state.get("compliance_review_done"):
            agent = ComplianceAgent()
            res = agent.run(container, state)
            status = res.data["compliance_status"]
            decision = request_approval(
                container, Gate.COMPLIANCE, {"compliance_status": status}
            )
            container.trace_repo.append_trace(
                case_id, Stage.COMPLIANCE_CHECK.value, "gate", "approval",
                {"gate": Gate.COMPLIANCE.value, "decision": decision},
            )
            return _save(state, {
                "compliance_status": status,
                "compliance_approved": decision == "approve",
                "compliance_review_done": True,
                "current_stage": Stage.COMPLIANCE_CHECK.value,
            })
        return {}

    # ---- CRITIC (cross-validation) --------------------------------------
    def critic(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.COMPLIANCE_CHECK)
        agent = CriticAgent()
        res = agent.run(container, state)
        flags = res.data["critic_flags"]
        # Evidence scores over the state as of this critic run (including the
        # flags it just produced).
        evidence = compute_evidence_scores({**state, "critic_flags": flags})
        return _save(state, {
            "critic_flags": flags,
            "evidence_scores": evidence,
            "current_stage": Stage.COMPLIANCE_CHECK.value,
        })

    # ---- REPLAN ---------------------------------------------------------
    def replan(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.REPLAN)
        updates = replan_policy(state, container.config.max_replan)
        container.trace_repo.append_trace(
            case_id, Stage.REPLAN.value, "orchestrator", "replan",
            {"attempts": updates["replan_attempts"], "target": updates["replan_target"]},
        )
        return _save(state, updates)

    # ---- HUMAN_ESCALATION (terminal) ------------------------------------
    def human_escalation(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.HUMAN_ESCALATION)
        return _save(state, {
            "case_status": CaseStatus.HUMAN_ESCALATION.value,
            "current_stage": Stage.HUMAN_ESCALATION.value,
        })

    # ---- LISTING --------------------------------------------------------
    def listing(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.LISTING)
        info = state.get("info_structured") or {}
        listing = {
            "case_id": case_id,
            "platform": state.get("platform"),
            "title": info.get("title"),
            "category": info.get("category"),
            "selling_points": info.get("selling_points", []),
            "images": [
                {"image_type": v.get("image_type"), "image_url": v.get("image_url")}
                for v in state.get("visual_results", [])
            ],
            "compliance": state.get("compliance_status"),
            "pim_id": state.get("pim_id"),
            "evidence": state.get("evidence_scores") or {},
        }
        return _save(state, {
            "listing_result": listing,
            "current_stage": Stage.LISTING.value,
        })

    # ---- FEEDBACK (terminal -> CLOSED) ----------------------------------
    def feedback(state: dict) -> dict:
        case_id = state["case_id"]
        _trace_stage(case_id, Stage.FEEDBACK)
        fb = {
            "case_id": case_id,
            "rating": 4.5,
            "notes": "Auto-generated feedback: listing produced end-to-end.",
            "visual_count": len(state.get("visual_results", [])),
        }
        return _save(state, {
            "feedback": fb,
            "case_status": CaseStatus.CLOSED.value,
            "current_stage": Stage.CLOSED.value,
        })

    return {
        "signal_analysis": signal_analysis,
        "selection_review": selection_review,
        "info_structuring": info_structuring,
        "visual_production": visual_production,
        "compliance_check": compliance_check,
        "critic": critic,
        "replan": replan,
        "human_escalation": human_escalation,
        "listing": listing,
        "feedback": feedback,
    }
