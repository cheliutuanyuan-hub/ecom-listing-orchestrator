"""Pytest configuration: put src on the path and provide temp-backed fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402


@pytest.fixture
def tmp_config(tmp_path):
    from ecom_orchestrator.config import AppConfig

    return AppConfig(
        _env_file=None,
        LISTING_DB_PATH=str(tmp_path / "trace.db"),
        LISTING_VISUAL_SERVICE_URL="",
        LISTING_AUTO_APPROVE=True,
        LISTING_VISUAL_CACHE_DIR=str(tmp_path / "vcache"),
    )


@pytest.fixture
def service(tmp_config):
    from ecom_orchestrator.service.case_service import build_default_service

    svc = build_default_service(tmp_config)
    yield svc
    # best-effort cleanup of sqlite files created under tmp_path
    for suffix in ("", ".pim"):
        try:
            Path(tmp_config.LISTING_DB_PATH + suffix).unlink()
        except OSError:
            pass
