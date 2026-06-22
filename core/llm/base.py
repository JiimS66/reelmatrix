import json
from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class LLMError(RuntimeError):
    """Base error for LLM configuration, transport, and response failures."""


class LLMConfigurationError(LLMError):
    """Raised when an LLM provider is configured incorrectly."""


class LLMProviderError(LLMError):
    """Raised when an LLM provider request fails."""


class LLMResponseValidationError(LLMError):
    """Raised when an LLM response does not match the requested schema."""


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[StructuredModel],
    ) -> StructuredModel:
        raise NotImplementedError

    @staticmethod
    def validate_json_response(
        raw_response: str,
        response_model: Type[StructuredModel],
    ) -> StructuredModel:
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise LLMResponseValidationError(
                f"LLM returned invalid JSON for {response_model.__name__}: {exc.msg}"
            ) from exc
        return BaseLLMClient.validate_object_response(payload, response_model)

    @staticmethod
    def validate_object_response(
        payload: Any,
        response_model: Type[StructuredModel],
    ) -> StructuredModel:
        try:
            return response_model.model_validate(payload)
        except ValidationError as exc:
            raise LLMResponseValidationError(
                f"LLM response failed {response_model.__name__} validation: {exc}"
            ) from exc
