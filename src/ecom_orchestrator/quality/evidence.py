"""Three-dimension evidence scoring for a case.

completeness: every main-path stage has a trace + snapshot recorded.
safety:      compliance approved + no critical flags in latest critic run.
robustness:  replan_attempts / tool failures / alignment coverage.
"""
from __future__ import annotations


def compute_evidence_scores(state: dict) -> dict[str, float]:
    # completeness: presence of key state artifacts
    keys = ["info_structured", "visual_results", "compliance_status", "listing_result"]
    completeness = sum(1 for k in keys if state.get(k)) / len(keys)

    # safety: compliance approved and no unresolved critical flags
    comp = 1.0 if state.get("compliance_approved") else 0.0
    criticals = [f for f in (state.get("critic_flags") or []) if f.get("severity") == "critical"]
    safety = round(comp * (0.0 if criticals else 1.0), 3)

    # robustness: replan attempts penalty + alignment coverage
    attempts = int(state.get("replan_attempts") or 0)
    visuals = state.get("visual_results") or []
    align_scores = [v.get("alignment_score") for v in visuals if v.get("alignment_score") is not None]
    align_avg = (sum(align_scores) / len(align_scores)) if align_scores else 0.0
    robustness = round(max(0.0, align_avg - 0.1 * attempts), 3)

    return {"completeness": round(completeness, 3), "safety": safety, "robustness": robustness}
