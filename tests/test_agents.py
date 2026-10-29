"""Agents must produce structured, deterministic outputs."""
from __future__ import annotations

from ecom_orchestrator.agents.compliance import ComplianceAgent
from ecom_orchestrator.agents.critic import CriticAgent
from ecom_orchestrator.agents.feasibility import FeasibilityAgent
from ecom_orchestrator.agents.info_structuring import InfoStructuringAgent
from ecom_orchestrator.agents.insight import InsightAgent
from ecom_orchestrator.agents.visual import VisualAgent
from ecom_orchestrator.domain.state import initial_state


def _insight(container, st):
    r = InsightAgent().run(container, st)
    return r.data["hypotheses"], r.data["signals"]


def _feasibility(container, st, hyps):
    r = FeasibilityAgent().run(container, {**st, "hypotheses": hyps})
    return r.data["hypotheses"]


def test_insight_produces_hypotheses_with_sources(service):
    st = initial_state("c1", "global")
    hyps, signals = _insight(service.container, st)
    assert hyps, "expected at least one hypothesis"
    assert signals
    for h in hyps:
        assert h["source_refs"], "hypothesis must carry source references"
        assert "feasibility" not in h


def test_feasibility_scores(service):
    st = initial_state("c1", "global")
    hyps, _ = _insight(service.container, st)
    scored = _feasibility(service.container, st, hyps)
    assert all("feasibility" in h for h in scored)
    assert all(0.0 <= h["feasibility"]["score"] <= 1.0 for h in scored)


def test_info_structuring_writes_pim_and_consistent(service):
    st = initial_state("c1", "global")
    hyps, _ = _insight(service.container, st)
    scored = _feasibility(service.container, st, hyps)
    st2 = {**st, "selected_hypothesis": scored[0]}
    r = InfoStructuringAgent().run(service.container, st2)
    assert r.ok is True
    assert r.data["pim_id"]
    info = r.data["info_structured"]
    assert info["title"] and info["category"] and info["selling_points"]
    assert r.data["consistency_ok"] is True


def test_visual_produces_normalized_results(service):
    st = initial_state("c1", "global")
    hyps, _ = _insight(service.container, st)
    scored = _feasibility(service.container, st, hyps)
    st2 = {**st, "selected_hypothesis": scored[0]}
    r1 = InfoStructuringAgent().run(service.container, st2)
    st3 = {**st2, "info_structured": r1.data["info_structured"]}
    r2 = VisualAgent().run(service.container, st3)
    results = r2.data["visual_results"]
    assert results, "expected visual results"
    required = {"task_id", "image_type", "image_url", "carries_selling_point", "quality_flags", "provider"}
    for v in results:
        assert required.issubset(v.keys())
    assert any(v["image_type"] == "main" for v in results)


def test_compliance_assigns_safety_level(service):
    st = initial_state("c1", "global")
    hyps, _ = _insight(service.container, st)
    scored = _feasibility(service.container, st, hyps)
    st2 = {**st, "selected_hypothesis": scored[0]}
    r1 = InfoStructuringAgent().run(service.container, st2)
    st3 = {**st2, "info_structured": r1.data["info_structured"]}
    r3 = ComplianceAgent().run(service.container, st3)
    status = r3.data["compliance_status"]
    assert status["safety_level"] in ("low", "medium", "high")


def test_critic_flags_no_critical_on_clean_data(service):
    st = initial_state("c1", "global")
    hyps, _ = _insight(service.container, st)
    scored = _feasibility(service.container, st, hyps)
    st2 = {**st, "selected_hypothesis": scored[0]}
    r1 = InfoStructuringAgent().run(service.container, st2)
    st3 = {**st2, "info_structured": r1.data["info_structured"]}
    r2 = VisualAgent().run(service.container, st3)
    st4 = {**st3, "visual_results": r2.data["visual_results"]}
    r4 = CriticAgent().run(service.container, st4)
    flags = r4.data["critic_flags"]
    critical = [f for f in flags if f.get("severity") == "critical"]
    assert not critical, f"unexpected critical flags: {flags}"
