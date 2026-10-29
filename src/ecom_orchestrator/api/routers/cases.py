"""Case lifecycle routers: start a case, fetch a case, and approve a pending
HITL gate (resume the interrupted graph).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import ApproveRequest, CaseSummary, StartCaseRequest

router = APIRouter(prefix="/cases", tags=["cases"])


def _service():
    # Lazy import avoids a circular import with app.py at module load time.
    from ..app import get_service

    return get_service()


@router.post("", response_model=CaseSummary)
def start_case(req: StartCaseRequest) -> CaseSummary:
    svc = _service()
    summary = svc.start_case(req.platform, req.meta, auto_approve=req.auto_approve)
    return CaseSummary(**summary)


@router.get("/{case_id}", response_model=CaseSummary)
def get_case(case_id: str) -> CaseSummary:
    svc = _service()
    summary = svc.get_case(case_id)
    if summary.get("status") == "RUNNING" and not summary.get("pending_gates"):
        # Unknown / never-started case.
        if summary.get("trace_count", 0) == 0:
            raise HTTPException(status_code=404, detail="case not found")
    return CaseSummary(**summary)


@router.post("/{case_id}/approve", response_model=CaseSummary)
def approve_case(case_id: str, req: ApproveRequest) -> CaseSummary:
    svc = _service()
    summary = svc.approve_case(case_id, decision=req.decision)
    return CaseSummary(**summary)
