"""FastAPI application factory.

The service is built once at import time using the default (offline, mock-backed)
wiring. Set LISTING_VISUAL_SERVICE_URL in the environment to route visual
generation to the real Project B service.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..logging_config import log
from ..service.case_service import CaseService, build_default_service
from .routers import cases, health

_STATIC_DIR = Path(__file__).resolve().parent / "static"

_app = FastAPI(title="ecom-listing-orchestrator", version="1.0.0")
_service_instance: CaseService | None = None


def get_service() -> CaseService:
    global _service_instance
    if _service_instance is None:
        _service_instance = build_default_service()
        log.info("CaseService initialized (default offline wiring)")
    return _service_instance


_app.include_router(health.router)
_app.include_router(cases.router)

if _STATIC_DIR.exists():
    _app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@_app.get("/", include_in_schema=False)
def root():
    """Serve the listing workbench UI; fall back to JSON if it is absent."""
    index = _STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"service": "ecom-listing-orchestrator", "docs": "/docs"}


def create_app() -> FastAPI:
    return _app


app = _app
