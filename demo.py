"""Standalone end-to-end verification (runs OFFLINE with mock adapters).

Run:
    PYTHONPATH=src python demo.py

Prints exactly "VERIFICATION PASSED" and exits 0 on success.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from ecom_orchestrator.config import AppConfig
from ecom_orchestrator.domain.models import Stage
from ecom_orchestrator.service.case_service import build_default_service


def main() -> int:
    cfg = AppConfig(
        _env_file=None,
        LISTING_AUTO_APPROVE=True,
        LISTING_VISUAL_SERVICE_URL="",  # empty => MockVisualService (offline)
        LISTING_DB_PATH="demo_trace.db",
        LISTING_VISUAL_CACHE_DIR="demo_visual_cache",
    )
    svc = build_default_service(cfg)

    summary = svc.start_case("global", {"source": "demo"}, auto_approve=True)

    # 1) Full case reaches terminal CLOSED.
    assert summary["status"] == "CLOSED", summary
    # 2) Visual assets were produced by the (mock) visual service.
    assert summary["visual_results"], "expected non-empty visual_results"
    # 3) Every main-path stage was traced (traceability requirement).
    trace = svc.trace_repo.get_trace(summary["case_id"])
    assert trace, "expected trace records"
    stages_seen = {t["stage"] for t in trace}
    for stg in Stage.main_path():
        assert stg.value in stages_seen, f"missing trace stage: {stg.value}"

    # Cleanup demo artifacts.
    for p in ("demo_trace.db", "demo_trace.db.pim"):
        try:
            os.remove(p)
        except OSError:
            pass

    print("VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
