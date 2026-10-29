"""Persistence: trace + snapshot repositories must survive writes."""
from __future__ import annotations


def test_trace_append_and_read(tmp_path):
    from ecom_orchestrator.persistence.sqlite import SqliteTraceRepository

    db = str(tmp_path / "t.db")
    repo = SqliteTraceRepository(db)
    repo.append_trace("c1", "SIGNAL_ANALYSIS", "insight_agent", "agent", {"n": 1})
    repo.append_trace("c1", "SELECTION_REVIEW", "gate", "approval", {"decision": "approve"})

    rows = repo.get_trace("c1")
    assert len(rows) == 2
    assert rows[0]["stage"] == "SIGNAL_ANALYSIS"
    assert rows[1]["kind"] == "approval"
    assert rows[1]["payload"] == {"decision": "approve"}


def test_trace_is_scoped_by_case(tmp_path):
    from ecom_orchestrator.persistence.sqlite import SqliteTraceRepository

    repo = SqliteTraceRepository(str(tmp_path / "t.db"))
    repo.append_trace("c1", "A", "x", "y", {})
    repo.append_trace("c2", "B", "x", "y", {})
    assert len(repo.get_trace("c1")) == 1
    assert len(repo.get_trace("c2")) == 1


def test_snapshot_save_and_get(tmp_path):
    from ecom_orchestrator.persistence.sqlite import SqliteSnapshotRepository

    repo = SqliteSnapshotRepository(str(tmp_path / "t.db"))
    state = {"case_id": "c1", "current_stage": "INFO_STRUCTURING", "foo": [1, 2]}
    repo.save("c1", "RUNNING", state)
    got = repo.get("c1")
    assert got is not None
    assert got["current_stage"] == "INFO_STRUCTURING"
    assert got["foo"] == [1, 2]
    assert got["case_status"] == "RUNNING"


def test_snapshot_overwrites(tmp_path):
    from ecom_orchestrator.persistence.sqlite import SqliteSnapshotRepository

    repo = SqliteSnapshotRepository(str(tmp_path / "t.db"))
    repo.save("c1", "RUNNING", {"case_id": "c1", "v": 1})
    repo.save("c1", "CLOSED", {"case_id": "c1", "v": 2})
    got = repo.get("c1")
    assert got["v"] == 2
    assert got["case_status"] == "CLOSED"
