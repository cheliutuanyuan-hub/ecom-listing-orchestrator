"""Offline mock visual service. Writes a local SVG per image, returns the
normalized shape required by VisualServicePort (and matched by Project B).
"""
from __future__ import annotations

import json
import os
import uuid

from ..ports.visual import VisualServicePort


def _svg(content: str, canvas: str, color: str) -> str:
    w, h = ("800x800".split("x") if "x" not in canvas else canvas.split("x"))
    w, h = int(w), int(h)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">'
        f'<rect width="100%" height="100%" fill="{color}"/>'
        f'<text x="50%" y="50%" font-family="sans-serif" font-size="24" '
        f'fill="#ffffff" text-anchor="middle" dominant-baseline="middle">'
        f"{content}</text></svg>"
    )


class MockVisualService(VisualServicePort):
    """Default visual adapter: no network, writes SVGs to a local cache dir."""

    COLORS = {"main": "#2b6cb0", "scene": "#2f855a", "detail": "#805ad5"}
    PROVIDER = "mock"

    def __init__(self, cache_dir: str = "visual_cache"):
        self._cache_dir = cache_dir
        os.makedirs(self._cache_dir, exist_ok=True)

    def submit_batch(self, case_id, platform, category_spec, selling_points, plan):
        results = []
        case_dir = os.path.join(self._cache_dir, str(case_id))
        os.makedirs(case_dir, exist_ok=True)
        for item in plan:
            image_type = item.get("image_type", "main")
            canvas = item.get("canvas", "800x800")
            sp = item.get("selling_point") or ""
            task_id = "task-" + uuid.uuid4().hex[:10]
            fname = f"{image_type}_{task_id}.svg"
            fpath = os.path.join(case_dir, fname)
            color = self.COLORS.get(image_type, "#555555")
            with open(fpath, "w", encoding="utf-8") as fh:
                fh.write(_svg(f"{image_type}:{sp}", canvas, color))
            results.append(
                {
                    "task_id": task_id,
                    "image_type": image_type,
                    "image_url": "file://" + os.path.abspath(fpath),
                    "carries_selling_point": sp,
                    "quality_flags": [],
                    # Mock parity with Project B's mock: every required element
                    # is recorded as present, so alignment is a full 1.0.
                    "alignment_score": 1.0,
                    "alignment_flags": ["selling_point:carried"],
                    "provider": self.PROVIDER,
                }
            )
        return results
