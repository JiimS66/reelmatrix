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
