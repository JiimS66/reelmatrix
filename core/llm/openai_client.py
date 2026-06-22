import json
from typing import Type

from openai import AsyncOpenAI, OpenAIError

from core.llm.base import (
    BaseLLMClient,
    LLMProviderError,
    StructuredModel,
)


class OpenAILLMClient(BaseLLMClient):
    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)

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
            f"{system_prompt}\n\nReturn only a JSON object matching this JSON Schema: {schema}"
        )
        raw_response = await self._complete(
            system_prompt=structured_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )
        return self.validate_json_response(raw_response, response_model)

    async def _complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            if json_mode:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
            else:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                )
        except OpenAIError as exc:
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMProviderError("OpenAI returned an empty response")
        return content
