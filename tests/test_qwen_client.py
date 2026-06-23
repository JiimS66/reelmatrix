import asyncio
import json
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from core.llm.base import LLMResponseValidationError
from core.llm.qwen_client import QwenLLMClient
from core.schemas.campaign import IdeationResult


VALID_IDEATION_RESULT = {
    "campaign_concept": "Focused launch",
    "core_message": "Turn campaign planning into measurable progress.",
    "target_audience_insight": "Lean teams need clarity without more overhead.",
    "recommended_angles": ["One guided campaign workflow"],
    "risks_or_assumptions": ["The audience recognizes the planning problem"],
    "follow_up_questions": [],
    "is_ready_for_planning": True,
}


class CompletionStub:
    def __init__(self, content: str) -> None:
        self._content = content
        self.arguments: Dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.arguments = kwargs
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def build_client(completion_stub: CompletionStub) -> QwenLLMClient:
    client = QwenLLMClient(
        api_key="test-key",
        base_url=(
            "https://workspace-id.ap-southeast-1.maas.aliyuncs.com/"
            "compatible-mode/v1"
        ),
        model="qwen-plus",
        timeout_seconds=1,
    )
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=completion_stub),
    )
    return client


def test_qwen_structured_generation_uses_compatible_chat_api() -> None:
    completion_stub = CompletionStub(json.dumps(VALID_IDEATION_RESULT))
    client = build_client(completion_stub)

    result = asyncio.run(
        client.generate_structured(
            system_prompt="system",
            user_prompt="user",
            response_model=IdeationResult,
        )
    )

    assert result.is_ready_for_planning is True
    assert completion_stub.arguments["model"] == "qwen-plus"
    assert "response_format" not in completion_stub.arguments
    assert completion_stub.arguments["messages"][0]["role"] == "system"


def test_qwen_invalid_json_has_clear_error() -> None:
    client = build_client(CompletionStub("not-json"))

    with pytest.raises(LLMResponseValidationError, match="invalid JSON"):
        asyncio.run(
            client.generate_structured(
                system_prompt="system",
                user_prompt="user",
                response_model=IdeationResult,
            )
        )
