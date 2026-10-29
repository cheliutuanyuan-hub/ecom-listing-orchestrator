"""Rule-based compliance adapter (offline). Forbidden-term + platform rules.

Safety level is monotonic: it may RAISE but never LOWER a previously set level.
"""
from __future__ import annotations

from ..domain.models import SafetyLevel
from ..ports.compliance import ComplianceRulePort


class RuleCompliance(ComplianceRulePort):
    def __init__(self, forbidden_terms: list[str] | None = None, max_title_len: int = 80):
        # Business DATA (terms come from cross-project contract with Project B).
        self.forbidden_terms = forbidden_terms or ["最", "第一", "国家级", "顶级", "第一品牌"]
        self.max_title_len = max_title_len

    def check_text(self, text: str, platform: str) -> dict:
        text = text or ""
        violations = []
        for term in self.forbidden_terms:
            start = 0
            while True:
                idx = text.find(term, start)
                if idx == -1:
                    break
                violations.append({"term": term, "position": idx})
                start = idx + len(term)
        return {"violations": violations, "hit": bool(violations)}

    def evaluate(self, payload: dict, platform: str) -> dict:
        texts = [
            payload.get("title", ""),
            " ".join(payload.get("selling_points", []) or []),
            payload.get("description", ""),
        ]
        all_violations = []
        for t in texts:
            res = self.check_text(t, platform)
            all_violations.extend(res["violations"])

        title = payload.get("title", "") or ""
        title_too_long = len(title) > self.max_title_len

        safety = SafetyLevel.LOW
        if all_violations:
            safety = SafetyLevel.HIGH
        elif title_too_long:
            safety = SafetyLevel.MEDIUM

        # "Only raises safety level, never lowers" semantics is applied by the
        # caller (ComplianceAgent) using SafetyLevel.max; here we report raw.
        return {
            "violations": all_violations,
            "title_too_long": title_too_long,
            "safety_level": safety.value,
            "requires_escalation": safety == SafetyLevel.HIGH,
        }
