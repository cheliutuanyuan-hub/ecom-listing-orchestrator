"""Optional CLI / uvicorn launcher.

Run with:
    PYTHONPATH=src python -m ecom_orchestrator            # serves the API
    PYTHONPATH=src python -m ecom_orchestrator api --port 8000
"""
from __future__ import annotations

import os
import sys

# Ensure the package (under src/) is importable when invoked as a module.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(prog="ecom_orchestrator")
    sub = parser.add_subparsers(dest="cmd")

    api = sub.add_parser("api", help="Serve the FastAPI app with uvicorn")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()
    if args.cmd == "api":
        import uvicorn

        from ecom_orchestrator.api.app import app

        uvicorn.run(app, host=args.host, port=args.port)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
