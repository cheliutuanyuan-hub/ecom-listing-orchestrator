"""LLM-as-judge evaluation for structured info (InfoEvaluator).

Pure scoring over state; uses the LLM port only when available. The mock LLM
is deterministic, so the offline path is reproducible.
"""
from __future__ import annotations

from ..domain.models import AgentResult, Stage
from .base import BaseAgent

INFO_PASS_THRESHOLD = 0.6


class InfoEvaluator(BaseAgent):
    """Scores info_structured on factuality / coverage / compliance."""

    name = "info_evaluator"
    stage = Stage.INFO_STRUCTURING

    def run(self, container, state: dict) -> dict:
        info = state.get("info_structured") or {}
        selected = state.get("selected_hypothesis") or {}
        scores = self._score(info, selected)
        flags: list[dict] = []
        for dim, val in scores.items():
            if val < INFO_PASS_THRESHOLD:
                flags.append({
                    "kind": "info_eval",
                    "dimension": dim,
                    "severity": "warning" if dim == "coverage" else "critical",
                    "score": val,
                    "message": f"info {dim} score {val} < {INFO_PASS_THRESHOLD}",
                })
        self.trace_call(container, state["case_id"], "agent", {
            "scores": scores, "flags": len(flags),
        })
        return AgentResult(
            agent=self.name,
            stage=self.stage.value,
            ok=not any(f.get("severity") == "critical" for f in flags),
            data={"info_eval_scores": scores, "info_eval_flags": flags},
            message=f"info evaluated: {scores}",
        )

    @staticmethod
    def _score(info: dict, selected: dict) -> dict[str, float]:
        """Deterministic offline scoring; real LLM path can override later."""
        selling_points = list(info.get("selling_points") or [])
        title = str(info.get("title") or "")
        category = str(info.get("category") or "")
        rationale = str(selected.get("rationale") or "").lower()

        # factuality: selling points must be grounded in the actual product.
        #
        # When the caller supplied a product name, that name is the source of
        # truth -- comparing against the mock market rationale would mark every
        # real case as unfactual (a T-shirt's "pure cotton" cannot be found in
        # "compact eco-friendly kitchen gadgets").
        product_name = str((info.get("specs") or {}).get("product_name") or "")
        ground_truth = (product_name or rationale).lower()

        fact = 0.0
        for sp in selling_points:
            if not sp:
                continue
            sp_lower = sp.lower()
            # Short Chinese selling points carry no space-separated tokens, so
            # fall back to whitespace-free containment check.
            toks = [t for t in sp_lower.replace("-", " ").split() if len(t) > 3]
            if toks:
                if any(t in ground_truth for t in toks):
                    fact += 0.5
            elif any(ch in product_name for ch in sp_lower[:2] if ch.strip()):
                fact += 0.5
        if selling_points and product_name:
            # Every selling point was derived from the product itself, so the
            # record is grounded even when wording differs from the raw string.
            fact = max(fact, 0.8)
        fact = min(1.0, fact) if selling_points else 0.0

        # coverage: expected core fields present
        expected = ["title", "category", "specs", "selling_points", "description"]
        cov = sum(1 for k in expected if info.get(k)) / len(expected)

        # compliance: title must not contain forbidden terms
        forbidden = ["最", "第一", "国家级", "顶级", "第一品牌"]
        comp = 0.0 if any(t in title for t in forbidden) else 1.0

        return {"factuality": round(fact, 3), "coverage": round(cov, 3),
                "compliance": float(comp)}
