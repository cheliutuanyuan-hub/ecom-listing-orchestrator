"""Application service: owns the compiled graph + checkpointer and exposes the
case lifecycle (start / get / approve).

The checkpointer uses ``thread_id = case_id`` so HITL interrupts can be resumed
deterministically by the FastAPI / approve flow.
"""
from __future__ import annotations

from typing import Any, Optional

from langgraph.types import Command

from ..adapters.mock_llm import MockLLM
from ..adapters.mock_market import MockMarket
from ..adapters.mock_visual import MockVisualService
from ..adapters.rule_compliance import RuleCompliance
from ..adapters.sqlite_pim import SQLitePIM
from ..config import AppConfig, load_config
from ..domain.models import CaseStatus, new_case_id
from ..orchestration.graph import build_graph, make_initial_state
from ..orchestration.nodes import GraphContainer
from ..persistence.sqlite import SqliteSnapshotRepository, SqliteTraceRepository
from ..ports.compliance import ComplianceRulePort
from ..ports.llm import LLMProviderPort
from ..ports.market import MarketSignalSourcePort
from ..ports.pim import PIMPort
from ..ports.visual import VisualServicePort

try:  # optional HTTP adapter (only used when a visual service URL is set)
    from ..adapters.http_visual import HttpVisualClient
except Exception as _import_error:  # pragma: no cover - httpx should be present
    HttpVisualClient = None  # type: ignore
    _HTTP_VISUAL_IMPORT_ERROR = _import_error
else:
    _HTTP_VISUAL_IMPORT_ERROR = None


class CaseService:
    def __init__(
        self,
        config: AppConfig,
        trace_repo: SqliteTraceRepository,
        snapshot_repo: SqliteSnapshotRepository,
        container: GraphContainer,
        graph,
    ):
        self.config = config
        self.trace_repo = trace_repo
        self.snapshot_repo = snapshot_repo
        self.container = container
        self.graph = graph

    # ---- lifecycle ------------------------------------------------------
    def start_case(self, platform: str, meta: Optional[dict] = None, auto_approve: Optional[bool] = None) -> dict:
        prev = self._maybe_set_auto_approve(auto_approve)
        try:
            case_id = new_case_id()
            init = make_initial_state(case_id, platform, meta)
            cfg = {"configurable": {"thread_id": case_id}}
            self.graph.invoke(init, cfg)
        finally:
            self._restore_auto_approve(prev)
        return self._summarize(case_id)

    def approve_case(self, case_id: str, decision: str = "approve", auto_approve: Optional[bool] = None) -> dict:
        prev = self._maybe_set_auto_approve(auto_approve)
        try:
            cfg = {"configurable": {"thread_id": case_id}}
            self.graph.invoke(Command(resume=decision), cfg)
        finally:
            self._restore_auto_approve(prev)
        return self._summarize(case_id)

    def get_case(self, case_id: str) -> dict:
        return self._summarize(case_id)

    # ---- helpers --------------------------------------------------------
    def _maybe_set_auto_approve(self, auto_approve: Optional[bool]):
        if auto_approve is None:
            return None
        prev = self.container.config.LISTING_AUTO_APPROVE
        self.container.config.LISTING_AUTO_APPROVE = bool(auto_approve)
        return prev

    def _restore_auto_approve(self, prev):
        if prev is not None:
            self.container.config.LISTING_AUTO_APPROVE = prev

    def _summarize(self, case_id: str) -> dict:
        snap = self.snapshot_repo.get(case_id) or {}
        cfg = {"configurable": {"thread_id": case_id}}
        try:
            gs = self.graph.get_state(cfg)
        except Exception:
            gs = None
        pending = list(gs.next) if gs is not None else []
        values = dict(gs.values) if gs is not None else {}

        if pending:
            status = CaseStatus.AWAITING_HUMAN.value
        else:
            status = snap.get("case_status") or values.get("case_status") or CaseStatus.RUNNING.value

        return {
            "case_id": case_id,
            "status": status,
            "current_stage": snap.get("current_stage") or values.get("current_stage"),
            "selection_approved": bool(snap.get("selection_approved", False) or values.get("selection_approved", False)),
            "info_approved": bool(snap.get("info_approved", False) or values.get("info_approved", False)),
            "visual_approved": bool(snap.get("visual_approved", False) or values.get("visual_approved", False)),
            "compliance_approved": bool(snap.get("compliance_approved", False) or values.get("compliance_approved", False)),
            "visual_results": snap.get("visual_results") or values.get("visual_results") or [],
            "replan_attempts": int(snap.get("replan_attempts", 0) or values.get("replan_attempts", 0)),
            "pending_gates": pending,
            "trace_count": len(self.trace_repo.get_trace(case_id)),
        }


def build_default_service(config: Optional[AppConfig] = None) -> CaseService:
    """Wire the default (fully offline, mock-backed) service."""
    config = config or load_config()
    db_path = config.LISTING_DB_PATH

    trace_repo = SqliteTraceRepository(db_path)
    snapshot_repo = SqliteSnapshotRepository(db_path)

    market: MarketSignalSourcePort = MockMarket()
    llm: LLMProviderPort = MockLLM()
    pim: PIMPort = SQLitePIM(db_path + ".pim")
    compliance: ComplianceRulePort = RuleCompliance(config.LISTING_FORBIDDEN_TERMS)

    if config.use_http_visual:
        # A configured URL means "use the real service". Never fall back to
        # mock silently -- that hid a broken adapter import and made a fully
        # configured deployment quietly produce mock artifacts.
        if HttpVisualClient is None:
            raise RuntimeError(
                f"LISTING_VISUAL_SERVICE_URL={config.visual_url!r} is set but the "
                f"HTTP visual adapter failed to import: {_HTTP_VISUAL_IMPORT_ERROR}"
            ) from _HTTP_VISUAL_IMPORT_ERROR
        visual: VisualServicePort = HttpVisualClient(
            config.visual_url,
            timeout=config.LISTING_VISUAL_TIMEOUT,
            public_base=config.visual_public_url,
        )
    else:
        visual: VisualServicePort = MockVisualService(config.LISTING_VISUAL_CACHE_DIR)

    container = GraphContainer(
        config=config,
        trace_repo=trace_repo,
        snapshot_repo=snapshot_repo,
        market=market,
        llm=llm,
        pim=pim,
        visual=visual,
        compliance=compliance,
    )
    graph = build_graph(container)
    return CaseService(config, trace_repo, snapshot_repo, container, graph)
