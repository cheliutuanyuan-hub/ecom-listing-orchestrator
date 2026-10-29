"""Pydantic (v2) schemas for the HTTP API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StartCaseRequest(BaseModel):
    platform: str = Field(default="global", description="Target marketplace/platform")
    meta: dict[str, Any] = Field(default_factory=dict, description="Arbitrary case metadata")
    auto_approve: bool | None = Field(
        default=None,
        description="If true, skip HITL interrupts and auto-approve all gates.",
    )


class ApproveRequest(BaseModel):
    decision: str = Field(default="approve", description="'approve' or 'reject'")


class CaseSummary(BaseModel):
    case_id: str
    status: str
    current_stage: str | None = None
    selection_approved: bool = False
    info_approved: bool = False
    visual_approved: bool = False
    compliance_approved: bool = False
    visual_results: list[dict] = Field(default_factory=list)
    replan_attempts: int = 0
    pending_gates: list[str] = Field(default_factory=list)
    trace_count: int = 0


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ecom-listing-orchestrator"
