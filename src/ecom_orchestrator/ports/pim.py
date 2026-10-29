"""Product Information Management (PIM) port. Default wiring uses SQLitePIM."""
from __future__ import annotations

from abc import ABC, abstractmethod


class PIMPort(ABC):
    @abstractmethod
    def save_product(self, case_id: str, info: dict) -> str:
        """Persist a structured product record; return its pim_id."""

    @abstractmethod
    def get_product(self, pim_id: str) -> dict:
        """Retrieve a product record by pim_id."""

    @abstractmethod
    def list_products(self, case_id: str) -> list[dict]:
        """List all product records for a case."""
