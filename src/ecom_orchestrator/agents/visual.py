"""VisualAgent: computes the image plan and calls the visual-generation service
(mock by default, HTTP to Project B when LISTING_VISUAL_SERVICE_URL is set).
"""
from __future__ import annotations

import time as _time

from ..domain.models import AgentResult, Stage
from .base import BaseAgent


class VisualAgent(BaseAgent):
    name = "visual_agent"
    stage = Stage.VISUAL_PRODUCTION

    CANVAS = {"main": "800x800", "scene": "1200x800", "detail": "800x800"}

    def run(self, container, state: dict) -> dict:
        case_id = state["case_id"]
        platform = state.get("platform", "global")
        info = state.get("info_structured") or {}
        selling_points = info.get("selling_points", [])
        forbidden = container.config.LISTING_FORBIDDEN_TERMS

        category_spec = {
            "category": info.get("category", "general"),
            # Identify the product, not just its attributes: Project B's real
            # image provider needs the subject or it renders something else.
            "product_name": str((info.get("specs") or {}).get("product_name") or ""),
            "canvas_presets": {
                "main": self.CANVAS["main"],
                "scene": self.CANVAS["scene"],
                "detail": self.CANVAS["detail"],
            },
            "forbidden_terms": list(forbidden),
        }

        plan = self.build_plan(selling_points, forbidden, state.get("reflections"))

        # Evidence chain: record the raw tool call (endpoint, duration,
        # outcome, and a compact response sample) around the port call.
        _t0 = _time.time()
        try:
            results = container.visual.submit_batch(
                case_id, platform, category_spec, selling_points, plan
            )
            container.trace_repo.append_trace(
                case_id, Stage.VISUAL_PRODUCTION.value, "visual_service", "tool_call",
                {
                    "endpoint": container.config.visual_url or "mock",
                    "task_ids": len(results),
                    "duration_ms": round((_time.time() - _t0) * 1000, 1),
                    "status": "ok",
                    "response": [
                        {"image_type": r.get("image_type"),
                         "alignment_score": r.get("alignment_score")}
                        for r in results[:5]
                    ],
                },
            )
        except Exception as exc:
            container.trace_repo.append_trace(
                case_id, Stage.VISUAL_PRODUCTION.value, "visual_service", "tool_call",
                {
                    "endpoint": container.config.visual_url or "mock",
                    "status": "failed",
                    "error": str(exc)[:200],
                },
            )
            raise

        self.trace_call(container, case_id, "agent", {
            "plan_items": len(plan),
            "results": len(results),
            "provider": results[0]["provider"] if results else None,
        })
        return AgentResult(
            agent=self.name,
            stage=self.stage.value,
            ok=bool(results),
            data={"visual_results": results},
            message=f"produced {len(results)} visual assets via {results[0]['provider'] if results else 'none'}",
        )

    def build_plan(
        self,
        selling_points: list[str],
        forbidden: list[str],
        reflections: list[str] | None = None,
    ) -> list[dict]:
        """Compute the image plan sent to the visual service.

        main   -> carries the PRIMARY selling point
        scene  -> carries a SECONDARY selling point (or primary)
        detail -> carries a FEATURE selling point (or primary)

        When reflections from a prior REPLAN exist, the most recent one is
        injected as a required element of every image, so the failure reason
        becomes a generation constraint in the retry round.
        """
        sp = selling_points or ["quality"]
        plan = []
        roles = ["main", "scene", "detail"]
        for i, role in enumerate(roles):
            sp_i = sp[i] if i < len(sp) else sp[0]
            plan.append(
                {
                    "image_type": role,
                    "canvas": self.CANVAS[role],
                    "selling_point": sp_i,
                    "required_elements": [sp_i],
                    "forbidden_elements": list(forbidden),
                    "style_preset": "default",
                }
            )
        reflections = reflections or []
        latest = reflections[-1] if reflections else ""
        if latest:
            for item in plan:
                item["required_elements"] = list(
                    dict.fromkeys(item["required_elements"] + [latest])
                )
        return plan
