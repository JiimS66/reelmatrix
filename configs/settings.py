from functools import lru_cache
from typing import Literal, Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    llm_provider: str = "mock"
    llm_timeout_seconds: float = Field(default=60, gt=0)
    web_origin: str = "http://localhost:3000"
    database_url: str = "sqlite:///./reelmatrix.db"
    # Enterprise deployment posture — on_prem/air_gapped force local providers + gate any
    # data leaving the environment (see core/privacy + docs/deployment-onprem.md).
    deployment_profile: Literal["cloud", "hybrid", "on_prem", "air_gapped"] = "cloud"

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    dashscope_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DASHSCOPE_API_KEY", "QWEN_API_KEY"),
    )
    dashscope_workspace_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "DASHSCOPE_WORKSPACE_ID", "QWEN_WORKSPACE_ID"
        ),
    )
    dashscope_base_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DASHSCOPE_BASE_URL", "QWEN_BASE_URL"),
    )
    dashscope_model: Optional[str] = Field(
        default="qwen-plus",
        validation_alias=AliasChoices("DASHSCOPE_MODEL", "QWEN_MODEL"),
    )

    local_llm_base_url: Optional[str] = "http://localhost:11434/v1"
    local_llm_api_key: Optional[str] = None
    local_llm_model: Optional[str] = "llama3.1"

    # SiliconFlow: cheap hosted endpoint for open-weight models from a DIFFERENT
    # family than Qwen (default DeepSeek) — the cross-model Auditor's channel, so
    # writer and judge errors decorrelate. Pin the Auditor to it in the Team tab.
    siliconflow_api_key: Optional[str] = None
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_model: str = "deepseek-ai/DeepSeek-V3"

    # Parallel drafts per post: with a real (cheap open-weight) model the runner
    # renders N candidates and keeps the best by content score. 1 = off — the
    # right value for mock/demo, since identical drafts would tie anyway.
    asset_draft_fanout: int = Field(default=1, ge=1, le=8)

    # Fire-and-forget JSON POST when work lands in a human's review queue.
    notify_webhook_url: Optional[str] = None

    # Conversion attribution source (mock | plausible). Plausible is
    # self-hostable, so analytics can stay inside the customer's environment —
    # same posture as the on-prem model story.
    analytics_source: str = "mock"
    plausible_base_url: str = "https://plausible.io"
    plausible_site_id: Optional[str] = None
    plausible_api_key: Optional[str] = None
    plausible_signup_goal: str = "Signup"

    # Hot-topic feed behind core/trends (mock | hackernews). The HN source is a
    # free keyless API — safe to enable in any deployment.
    trend_source: str = "mock"

    # Visual generation/understanding behind core/media.
    # media: mock | dashscope (Qwen-Image via DashScope) | zimage (local Z-Image-Turbo)
    # vision: mock | dashscope (Qwen3-VL via the OpenAI-compatible endpoint)
    media_provider: str = "mock"
    vision_provider: str = "mock"
    dashscope_image_model: str = "qwen-image"
    dashscope_vl_model: str = "qwen3-vl-plus"
    zimage_base_url: Optional[str] = None  # e.g. http://localhost:9800

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: object) -> str:
        if value is None:
            return "mock"
        normalized = str(value).strip().lower()
        return normalized or "mock"

    @property
    def resolved_dashscope_base_url(self) -> Optional[str]:
        workspace_id = (self.dashscope_workspace_id or "").strip()
        if workspace_id:
            return (
                f"https://{workspace_id}.ap-southeast-1.maas.aliyuncs.com/"
                "compatible-mode/v1"
            )

        base_url = (self.dashscope_base_url or "").strip().rstrip("/")
        return base_url or None


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
