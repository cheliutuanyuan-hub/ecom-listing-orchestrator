"""HTTP visual client implementing the exact Project B contract.

Used ONLY when LISTING_VISUAL_SERVICE_URL is set. Calls:
  POST {base}/v1/generate/batch   -> {"batch_id","task_ids","status":"accepted"}
  GET  {base}/v1/tasks/{task_id}  -> task object (poll until succeeded/failed)

The returned task JSON is normalized to VisualServicePort's shape.
"""
from __future__ import annotations

import time

import httpx

from ..ports.visual import VisualServicePort


class HttpVisualClient(VisualServicePort):
    """Real-adapter stub that talks to Project B.

    This is wired when LISTING_VISUAL_SERVICE_URL is configured. It is NOT used
    in the offline default path; it is provided so integration with Project B
    works without code changes once the URL is set.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
        poll_interval: float = 1.0,
        public_base: str = "",
    ):
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._poll = poll_interval
        # Project B returns "/outputs/x.svg"; prefix it with the address the
        # caller can actually reach (inside compose, the service hostname is
        # not resolvable from outside the network).
        self._public_base = (public_base or "").rstrip("/")

    def submit_batch(self, case_id, platform, category_spec, selling_points, plan):
        body = {
            "case_id": case_id,
            "platform": platform,
            "category_spec": category_spec,
            "selling_points": list(selling_points),
            "images": plan,
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(f"{self._base}/v1/generate/batch", json=body)
            resp.raise_for_status()
            accepted = resp.json()
            task_ids = accepted.get("task_ids", [])
            if not task_ids:
                raise RuntimeError(f"Visual service returned no task_ids: {accepted}")

            results = []
            deadline = time.time() + self._timeout
            for tid in task_ids:
                task = self._poll_task(client, tid, deadline)
                results.append(self._normalize(task))
            return results

    def _poll_task(self, client: httpx.Client, task_id: str, deadline: float) -> dict:
        while time.time() < deadline:
            resp = client.get(f"{self._base}/v1/tasks/{task_id}")
            resp.raise_for_status()
            task = resp.json()
            status = task.get("status")
            if status == "succeeded":
                return task
            if status == "failed":
                raise RuntimeError(
                    f"Visual task {task_id} failed: {task.get('error', 'unknown')}"
                )
            time.sleep(self._poll)
        raise TimeoutError(f"Visual task {task_id} timed out after {self._timeout}s")

    def _normalize(self, task: dict) -> dict:
        # Project B returns top-level: image_type, image_url,
        # carries_selling_point, quality_flags, provider (+ task_id/status),
        # plus alignment = {"score": float, "flags": [...]} when scored.
        alignment = task.get("alignment") or {}
        image_url = task.get("image_url")
        if image_url and self._public_base and str(image_url).startswith("/"):
            image_url = f"{self._public_base}{image_url}"
        return {
            "task_id": task.get("task_id"),
            "image_type": task.get("image_type"),
            "image_url": image_url,
            "carries_selling_point": task.get("carries_selling_point"),
            "quality_flags": task.get("quality_flags", []),
            "alignment_score": alignment.get("score"),
            "alignment_flags": alignment.get("flags", []),
            "provider": task.get("provider", "project_b"),
        }
