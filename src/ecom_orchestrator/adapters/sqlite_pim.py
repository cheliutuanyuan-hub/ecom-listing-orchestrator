"""PIM mock backed by SQLite. Self-initializing, fully functional offline."""
from __future__ import annotations

import json
import sqlite3
import threading

from ..ports.pim import PIMPort


class SQLitePIM(PIMPort):
    def __init__(self, db_path: str = "ecom_pim.db"):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pim_products (
                    pim_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    info_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_product(self, case_id: str, info: dict) -> str:
        import time
        import uuid

        pim_id = "pim-" + uuid.uuid4().hex[:10]
        record = dict(info)
        record["pim_id"] = pim_id
        record["case_id"] = case_id
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO pim_products (pim_id, case_id, info_json, created_at) VALUES (?,?,?,?)",
                (pim_id, case_id, json.dumps(record, ensure_ascii=False), str(time.time())),
            )
            conn.commit()
        return pim_id

    def get_product(self, pim_id: str) -> dict:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT info_json FROM pim_products WHERE pim_id = ?", (pim_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"pim_id not found: {pim_id}")
        return json.loads(row["info_json"])

    def list_products(self, case_id: str) -> list[dict]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT info_json FROM pim_products WHERE case_id = ?", (case_id,)
            ).fetchall()
        return [json.loads(r["info_json"]) for r in rows]
