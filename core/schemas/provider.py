from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict


class LLMProviderKind(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"
    DEVELOPMENT = "development"


class LLMProviderInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    display_name: str
    model_name: str
    kind: LLMProviderKind
    description: str
    configured: bool
    is_default: bool


class LLMProviderCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: List[LLMProviderInfo]
