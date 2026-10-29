"""Application configuration via pydantic-settings.

All knobs come from environment variables (prefix LISTING_) so the project runs
identically offline (no docker, no network). Defaults wire in the fully
functional MOCK adapters.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # SQLite trace + snapshot database (self-initializing).
    LISTING_DB_PATH: str = "ecom_listing.db"

    # Empty => use MockVisualService (offline). Set to e.g. http://127.0.0.1:8012
    # to call Project B's real visual-generation service.
    LISTING_VISUAL_SERVICE_URL: str = ""

    # Address clients can reach Project B's artifacts on. Project B returns
    # relative paths ("/outputs/x.svg"); the service URL above is only valid
    # inside the compose network, so responses are prefixed with this one.
    # Empty => fall back to LISTING_VISUAL_SERVICE_URL.
    LISTING_VISUAL_PUBLIC_URL: str = ""

    # Overall deadline (seconds) for one visual batch: submit + poll every task
    # to a terminal state. Mock generation finishes in ~1s, so 60s was fine;
    # a real image provider (e.g. DashScope) needs ~50s PER image, so raise this
    # to ~600 when routing to a real backend.
    LISTING_VISUAL_TIMEOUT: float = 60.0

    # When True, all HITL gates auto-approve (no interrupt). Driven by the
    # LISTING_AUTO_APPROVE env var or the auto_approve run parameter.
    LISTING_AUTO_APPROVE: bool = False

    # Max REPLAN attempts before routing to HUMAN_ESCALATION (MAX_REPLAN = 2).
    LISTING_MAX_REPLAN: int = 2

    # Local cache dir for MockVisualService generated SVGs.
    LISTING_VISUAL_CACHE_DIR: str = "visual_cache"

    # Default platform and forbidden-terms list (used by rule compliance).
    # NOTE: forbidden terms are business DATA mandated by the cross-project
    # contract with Project B; they are not code identifiers.
    LISTING_PLATFORM: str = "global"
    LISTING_FORBIDDEN_TERMS: list[str] = ["最", "第一", "国家级", "顶级", "第一品牌"]

    # InfoEvaluator golden-set alignment gate (T6): minimum alignment rate the
    # evaluator must reach against the golden set before it is production-OK.
    LISTING_EVALUATOR_GOLDEN_THRESHOLD: float = 0.9

    @property
    def auto_approve(self) -> bool:
        return bool(self.LISTING_AUTO_APPROVE)

    @property
    def max_replan(self) -> int:
        return int(self.LISTING_MAX_REPLAN)

    @property
    def visual_url(self) -> str:
        return (self.LISTING_VISUAL_SERVICE_URL or "").strip()

    @property
    def use_http_visual(self) -> bool:
        return bool(self.visual_url)

    @property
    def visual_public_url(self) -> str:
        return (self.LISTING_VISUAL_PUBLIC_URL or "").strip() or self.visual_url

    @property
    def golden_threshold(self) -> float:
        return float(self.LISTING_EVALUATOR_GOLDEN_THRESHOLD)


def load_config() -> AppConfig:
    """Load configuration from environment / .env."""
    return AppConfig()
