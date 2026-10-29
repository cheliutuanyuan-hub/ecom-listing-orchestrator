"""Visual-generation service port (Project B contract).

``submit_batch`` returns a normalized list of dicts:
    {"task_id", "image_type", "image_url", "carries_selling_point",
     "quality_flags", "provider"}.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class VisualServicePort(ABC):
    @abstractmethod
    def submit_batch(
        self,
        case_id: str,
        platform: str,
        category_spec: dict,
        selling_points: list[str],
        plan: list[dict],
    ) -> list[dict]:
        """Submit a batch of image-generation tasks and return normalized results.

        ``plan`` items shape:
            {"image_type", "canvas", "selling_point", "required_elements",
             "forbidden_elements", "style_preset"}.
        ``category_spec`` shape:
            {"category", "canvas_presets": {...}, "forbidden_terms": [...]}.
        """
