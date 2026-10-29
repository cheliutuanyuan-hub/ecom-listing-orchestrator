"""T6: golden-set alignment gate for the InfoEvaluator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ecom_orchestrator.agents.evaluator import InfoEvaluator

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = REPO_ROOT / "eval_sets" / "golden" / "golden_info_cases.json"


def _load_golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_golden_cases_are_self_consistent():
    """The golden set must align 100% with the deterministic _score formula."""
    agent = InfoEvaluator()
    cases = _load_golden()
    assert len(cases) == 10
    for c in cases:
        scores = agent._score(c["info"], c["selected"])
        exp = c["expect"]
        for k in ("factuality", "coverage", "compliance"):
            assert abs(scores[k] - exp[k]) < 1e-6, (
                f"{c['id']} {k}: computed {scores[k]} != expect {exp[k]}"
            )
        is_critical = (
            scores["factuality"] < 0.6
            or scores["coverage"] < 0.6
            or scores["compliance"] < 0.6
        )
        assert is_critical == exp["critical"], f"{c['id']} critical mismatch"


def test_validate_script_exits_zero():
    env = dict(os.environ)
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "scripts/validate_evaluator.py"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "golden alignment: 10/10" in proc.stdout
