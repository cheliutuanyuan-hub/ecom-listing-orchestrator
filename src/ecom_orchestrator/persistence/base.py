"""Persistence port abstractions (trace + snapshot)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class TraceRepository(ABC):
    @abstractmethod
    def append_trace(
        self, case_id: str, stage: str, actor: str, kind: str, payload: dict
    ) -> None:
        """Append an immutable trace record for a case."""

    @abstractmethod
    def get_trace(self, case_id: str) -> list[dict]:
        """Return all trace records for a case, in insertion order."""


class SnapshotRepository(ABC):
    @abstractmethod
    def save(self, case_id: str, status: str, state: dict) -> None:
        """Persist a full state snapshot for a case (overwrites prior)."""

    @abstractmethod
    def get(self, case_id: str) -> Optional[dict]:
        """Return the most recent snapshot for a case, or None."""
