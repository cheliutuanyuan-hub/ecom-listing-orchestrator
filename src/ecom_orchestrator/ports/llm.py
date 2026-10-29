"""LLM provider port. Default wiring uses MockLLM (offline)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProviderPort(ABC):
    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return generated text for the given prompt."""

    @abstractmethod
    def structured(self, prompt: str, schema: dict) -> dict:
        """Return a JSON object conforming to the given JSON-schema-like dict.

        ``schema`` follows a minimal subset: {"required": [...], "properties": {k: {...}}}).
        """
