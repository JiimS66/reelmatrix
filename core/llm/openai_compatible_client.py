import json
from typing import Type

from openai import AsyncOpenAI, OpenAIError

from core.llm.base import BaseLLMClient, LLMProviderError, StructuredModel


class OpenAICompatibleLLMClient(BaseLLMClient):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: float,
        provider_name: str,
    ) -> None:
        self._model = model
        self._provider_name = provider_name
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout_seconds,
        )

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        return await self._complete(system_prompt=system_prompt, user_prompt=user_prompt)

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[StructuredModel],
    ) -> StructuredModel:
        schema = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        structured_prompt = (
            f"{system_prompt}\n\nReturn only valid JSON matching this JSON Schema. "
            f"Do not include Markdown fences or commentary: {schema}"
        )
        raw_response = await self._complete(
            system_prompt=structured_prompt,
            user_prompt=user_prompt,
        )
        return self.validate_json_response(raw_response, response_model)

    async def _complete(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except OpenAIError as exc:
            raise LLMProviderError(
                f"{self._provider_name} request failed: {exc}"
            ) from exc
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMProviderError(f"{self._provider_name} returned an empty response")
        return content
