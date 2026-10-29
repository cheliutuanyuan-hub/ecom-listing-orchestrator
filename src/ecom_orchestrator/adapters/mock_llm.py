"""Offline mock LLM. Deterministic, template-based, no network."""
from __future__ import annotations

import re

from ..ports.llm import LLMProviderPort


class MockLLM(LLMProviderPort):
    """Fully-functional offline stand-in for an LLM.

    ``complete`` returns a templated, deterministic string. ``structured``
    fabricates a JSON object whose keys match the requested schema's
    ``required``/``properties`` so downstream agents can rely on a stable shape.
    """

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        snippet = re.sub(r"\s+", " ", (prompt or "")).strip()[:160]
        return f"[MOCK_LLM]{(' ' + system) if system else ''} :: {snippet}"

    def structured(self, prompt: str, schema: dict) -> dict:
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        required = schema.get("required", []) if isinstance(schema, dict) else []
        keys = list(properties.keys()) or list(required) or ["result"]
        out: dict = {}
        for key in keys:
            out[key] = self._value_for(key)
        return out

    @staticmethod
    def _value_for(key: str):
        kl = key.lower()
        if "title" in kl:
            return "Premium Eco-Friendly Product Title"
        if "category" in kl:
            return "general"
        if "score" in kl or "rating" in kl:
            return 0.8
        if "list" in kl or "points" in kl or "selling" in kl:
            return ["durable", "eco-friendly", "great value"]
        if "spec" in kl:
            return {"material": "alloy", "weight": "1.2kg"}
        if "bool" in kl or "ok" in kl:
            return True
        return "mock_value"
