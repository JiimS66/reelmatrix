from core.llm.openai_compatible_client import OpenAICompatibleLLMClient


class QwenLLMClient(OpenAICompatibleLLMClient):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: float,
    ) -> None:
        super().__init__(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            provider_name="Qwen",
        )
