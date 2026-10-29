"""Centralised logging configuration (stdlib only, no external deps)."""
from __future__ import annotations

import logging
import sys


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s :: %(message)s")
    )
    root = logging.getLogger("ecom_orchestrator")
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(handler)
    root.propagate = False
    return root


log = configure_logging()
