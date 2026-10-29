"""SQLite-backed trace + snapshot repositories. Self-initializing, offline."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time

from .base import SnapshotRepository, TraceRepository


class SqliteTraceRepository(TraceRepository):
    def __init__(self, db_path: str = "ecom_listing.db"):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self._db_path)) or ".", exist_ok=True)
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    ts REAL NOT NULL
                )
                """
            )
            conn.commit()

    def append_trace(self, case_id, stage, actor, kind, payload):
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO trace (case_id, stage, actor, kind, payload_json, ts) "
                "VALUES (?,?,?,?,?,?)",
                (
                    case_id,
                    stage,
                    actor,
                    kind,
                    json.dumps(payload, ensure_ascii=False),
                    time.time(),
                ),
            )
            conn.commit()

    def get_trace(self, case_id):
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT case_id, stage, actor, kind, payload_json, ts FROM trace "
                "WHERE case_id = ? ORDER BY id ASC",
                (case_id,),
            ).fetchall()
        return [
            {
                "case_id": r["case_id"],
                "stage": r["stage"],
                "actor": r["actor"],
                "kind": r["kind"],
                "payload": json.loads(r["payload_json"]),
                "ts": r["ts"],
            }
            for r in rows
        ]


class SqliteSnapshotRepository(SnapshotRepository):
    def __init__(self, db_path: str = "ecom_listing.db"):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self._db_path)) or ".", exist_ok=True)
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshot (
                    case_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    ts REAL NOT NULL
                )
                """
            )
            conn.commit()

    def save(self, case_id, status, state):
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO snapshot (case_id, status, state_json, ts) "
                "VALUES (?,?,?,?)",
                (case_id, status, json.dumps(state, ensure_ascii=False), time.time()),
            )
            conn.commit()

    def get(self, case_id):
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT status, state_json FROM snapshot WHERE case_id = ?", (case_id,)
            ).fetchone()
        if row is None:
            return None
        state = json.loads(row["state_json"])
        state["case_status"] = row["status"]
        return state
