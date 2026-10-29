"""Golden-set alignment gate for InfoEvaluator.

Usage: PYTHONPATH=src python scripts/validate_evaluator.py
Exits 0 (PASS) if alignment >= threshold, else 1 (FAIL).
"""
import json
import sys
from pathlib import Path

from ecom_orchestrator.agents.evaluator import InfoEvaluator
from ecom_orchestrator.config import AppConfig


def main() -> int:
    cases = json.loads(Path("eval_sets/golden/golden_info_cases.json").read_text(encoding="utf-8"))
    agent = InfoEvaluator()
    threshold = AppConfig().golden_threshold
    aligned = 0
    for c in cases:
        scores = agent._score(c["info"], c["selected"])
        exp = c["expect"]
        ok = all(abs(scores[k] - exp[k]) < 1e-6 for k in ("factuality", "coverage", "compliance"))
        ok = ok and ((scores["factuality"] < 0.6 or scores["coverage"] < 0.6 or scores["compliance"] < 0.6) == exp["critical"])
        aligned += 1 if ok else 0
    rate = aligned / len(cases)
    print(f"golden alignment: {aligned}/{len(cases)} = {rate:.1%}")
    return 0 if rate >= threshold else 1


if __name__ == "__main__":
    sys.exit(main())
