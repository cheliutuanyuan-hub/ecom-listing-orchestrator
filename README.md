# ecom-listing-orchestrator (Project A)

LangGraph multi-agent orchestration for an e-commerce product-listing production
line. Hexagonal (ports/adapters) architecture: every external system sits behind
an interface, and the default wiring uses **fully-functional MOCK adapters** so
the entire pipeline runs **OFFLINE** — no Docker, no network, no external API.

This is one half of a two-project system. Project B is the visual-generation
service; the cross-project contract is enforced by `VisualServicePort`.

## Production-shaped, NOT a demo
- Real layered architecture: `domain` -> `ports` -> `adapters`/`agents` ->
  `orchestration` -> `persistence`/`service` -> `api`.
- Real LangGraph `StateGraph` with conditional edges (gates, REPLAN, escalation).
- Real HITL via `langgraph.types.interrupt` (4 gates; skipped under auto-approve).
- Real REPLAN routing + `HUMAN_ESCALATION` terminal state.
- Real Critic cross-validation that can trigger REPLAN.
- Real SQLite trace + snapshot persistence (self-initializing).
- Real FastAPI: `POST /cases` (start) + `POST /cases/{id}/approve` (resume).
- Real pytest suite + Dockerfile/docker-compose + this README.

## Architecture

```
                          +-----------------------------+
                          |         FastAPI /api         |
                          |  POST /cases  (start_case)   |
                          |  GET  /cases/{id}            |
                          |  POST /cases/{id}/approve    |
                          +-------------+----------------+
                                            |
                                            v
                          +-----------------------------+
                          |       CaseService            |
                          |  compiled graph + checkpointer(thread_id=case_id)
                          +-------------+----------------+
                                            |
                                            v
   +-------------------------------------------------------------------+
   |  LangGraph StateGraph (conditional edges == HITL gates + REPLAN)   |
   |                                                                   |
   |  SIGNAL_ANALYSIS                                                  |
   |    InsightAgent  -> hypotheses(+sources)                          |
   |    FeasibilityAgent -> feasibility scores                         |
   |      |                                                            |
   |      v  [GATE: SELECTION_REVIEW]  (interrupt / auto-approve)      |
   |  INFO_STRUCTURING                                                |
   |    InfoStructuringAgent -> PIM write + consistency check          |
   |      |                                                            |
   |      v  [GATE: INFO_STRUCTURING]                                 |
   |  VISUAL_PRODUCTION                                               |
   |    VisualAgent -> VisualServicePort.submit_batch()                |
   |      |                                                            |
   |      v  [GATE: VISUAL]                                           |
   |  COMPLIANCE_CHECK                                                |
   |    ComplianceAgent (monotonic safety level)                       |
   |      |                                                            |
   |      v  [GATE: COMPLIANCE]                                       |
   |  CRITIC  -> cross-validate                                       |
   |      | critical flag?                                            |
   |      +-- yes --> REPLAN (attempts++, adjust, re-enter) --> ...    |
   |      |                 | attempts > MAX_REPLAN                   |
   |      |                 +------------------> HUMAN_ESCALATION      |
   |      no                                                  |        |
   |      v                                                   v        |
   |  LISTING --> FEEDBACK --> CLOSED                   (terminal)     |
   +-------------------------------------------------------------------+
        | every agent call / approval / replan traced + snapshotted
        v
   +-----------------------------+        +-----------------------------+
   | TraceRepository (SQLite)    |        | SnapshotRepository (SQLite)  |
   +-----------------------------+        +-----------------------------+

   Ports (interfaces)                Default adapters (mock, offline)
   --------------------              ---------------------------------
   LLMProviderPort        -> MockLLM
   MarketSignalSourcePort-> MockMarket (+ constraint pool)
   PIMPort               -> SQLitePIM
   VisualServicePort     -> MockVisualService  (or HttpVisualClient)
   ComplianceRulePort    -> RuleCompliance
```

## Stages & agents (split by JUDGMENT TYPE)
- `SIGNAL_ANALYSIS`: **InsightAgent** (signals -> hypotheses w/ source refs) +
  **FeasibilityAgent** (constraint-pool scoring).
- `SELECTION_REVIEW`: pick best hypothesis. **GATE** approve chosen hypothesis.
- `INFO_STRUCTURING`: **InfoStructuringAgent** writes PIM + consistency check.
  **GATE** approve structured info.
- `VISUAL_PRODUCTION`: **VisualAgent** calls visual service. **GATE** approve assets.
- `COMPLIANCE_CHECK`: **ComplianceAgent** (forbidden terms, rules; raises safety
  only). **GATE** approve risk escalation.
- `CRITIC` (**CriticAgent**): rule checks (insight vs feasibility, visual vs
  selling points) + **InfoEvaluator** LLM-as-judge scores (factuality /
  coverage / compliance) + per-asset **alignment** scores from Project B.
  Critical flag -> REPLAN.
- `LISTING` -> `FEEDBACK` -> `CLOSED`. `REPLAN` re-enters a stage; `> MAX_REPLAN`
  -> `HUMAN_ESCALATION` (terminal).

## Run it (offline, no docker)

```bash
# 1) Install deps
pip install -r requirements.txt

# 2) Run the standalone verification (prints "VERIFICATION PASSED", exit 0)
PYTHONPATH=src python demo.py

# 3) Run the test suite
PYTHONPATH=src python -m pytest -q

# 4) Golden-set gate: the InfoEvaluator must align >= 90% with the annotated
#    golden set before it is considered production-ready (exit 0 = PASS)
PYTHONPATH=src python scripts/validate_evaluator.py

# 5) Serve the FastAPI app
PYTHONPATH=src python -m ecom_orchestrator api --port 8000
#    then: POST /cases  ->  GET /cases/{id}  -> POST /cases/{id}/approve
```

Set `LISTING_AUTO_APPROVE=true` to skip all HITL interrupts (used by the demo
and the full-case test). With it false, the API flow is: start -> read
`pending_gates` -> POST approve to resume, repeating until `status=CLOSED` or
`HUMAN_ESCALATION`.

## Cross-project contract (Project B)
`VisualServicePort.submit_batch(case_id, platform, category_spec, selling_points,
plan) -> list[dict]` with each dict normalized to:

```
{"task_id","image_type","image_url","carries_selling_point","quality_flags",
 "alignment_score","alignment_flags","provider"}
```

`alignment_score` (0-1) comes from Project B's `AlignmentChecker`; the Critic
treats `< 0.6` as critical and a missing score as a warning.

- If `LISTING_VISUAL_SERVICE_URL` is empty -> `MockVisualService` writes a local
  SVG and returns the same normalized shape (verifies standalone).
- If set -> `HttpVisualClient`:
  - `POST {base}/v1/generate/batch` (body: `case_id, platform, category_spec,
    selling_points, images[]`) -> `{"batch_id","task_ids","status":"accepted"}`.
  - Poll `GET {base}/v1/tasks/{task_id}` until `succeeded`/`failed` (timeout 60s,
    every 1s); normalize B's top-level fields into the shape above.
  - A failed task raises a clear error so the orchestrator can route to
    REPLAN / HUMAN_ESCALATION.

## Production-grade features (P0)

**LLM-as-judge evaluation layer.** `InfoEvaluator` scores every structured-info
output on three dimensions — `factuality` (selling points traceable to the
hypothesis rationale), `coverage` (core fields present), `compliance`
(forbidden terms absent from the title). Scores below 0.6 become Critic flags
(critical for factuality/compliance, warning for coverage). The evaluator must
pass a **golden-set alignment gate** before production use: 10 annotated cases
in `eval_sets/golden/`, alignment rate >= `LISTING_EVALUATOR_GOLDEN_THRESHOLD`
(default 0.9) via `scripts/validate_evaluator.py`.

**Reflection-based REPLAN.** `replan_policy` structures critical failure
reasons into reflection texts accumulated in `state["reflections"]`; the
`VisualAgent` injects the latest reflection into the next round's
`required_elements`, so retries are constrained by *why* the last round failed
— not a blind re-run of the same prompt.

**Evidence chain (3-piece + 3-dimension).** Every stage leaves a three-piece
record: agent traces, **raw tool-call traces** (endpoint, duration, status and
a sampled response for the visual service; PIM id for the PIM write), and
state snapshots. `quality/evidence.py` scores each case on
`completeness` / `safety` / `robustness`, attached to the listing result.

## Honest limitations
- Mock LLM/market/PIM are deterministic stand-ins, not real models/SaaS; the
  evaluator's offline scoring is the same deterministic formula (the LLM port
  is reserved for a real judge model).
- The real visual service is only contacted when `LISTING_VISUAL_SERVICE_URL` is
  set; `HttpVisualClient` is a real-adapter implementation, not exercised offline.
- No pixel-level QA on generated images; validation is structural (normalized
  shape, `carries_selling_point`, `quality_flags`, metadata-level alignment).
- Real external LLM/PIM/Market SaaS adapters are intentionally structured stubs
  (raise `NotImplementedError` with endpoint notes) — the mock adapters are the
  default and fully functional.
- HITL interrupt/resume verified via the FastAPI flow; the offline demo/tests
  exercise the auto-approve path to reach `CLOSED`.
