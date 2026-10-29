"""Base class for all agents (JUDGMENT-TYPE oriented, not job-title oriented)."""
from __future__ import annotations

from ..domain.models import AgentResult


class BaseAgent:
    name = "base"
    stage = None

    def trace_call(self, container, case_id: str, kind: str, payload: dict) -> None:
        """Record an agent action in the trace repository."""
        container.trace_repo.append_trace(
            case_id, self.stage or "", self.name, kind, payload
        )

    def trace_result(self, container, case_id: str, result: AgentResult) -> AgentResult:
        self.trace_call(container, case_id, "agent_result", result.to_dict())
        return result

    def run(self, container, state: dict) -> dict:
        raise NotImplementedError
