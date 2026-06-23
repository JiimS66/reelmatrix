import asyncio
from types import SimpleNamespace
from typing import Any, Dict

from core.llm.openai_client import OpenAILLMClient


class CompletionStub:
    def __init__(self) -> None:
        self.arguments: Dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.arguments = kwargs
        message = SimpleNamespace(content="plain text response")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_text_generation_omits_structured_response_format() -> None:
    completion_stub = CompletionStub()
    client = OpenAILLMClient(
        api_key="test-key",
        model="test-model",
        timeout_seconds=1,
    )
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=completion_stub),
    )

    result = asyncio.run(
        client.generate_text(system_prompt="system", user_prompt="user")
    )

    assert result == "plain text response"
    assert "response_format" not in completion_stub.arguments
