from configs.settings import AppSettings
from core.llm.base import BaseLLMClient, LLMConfigurationError
from core.llm.local_client import LocalLLMClient
from core.llm.mock_client import MockLLMClient
from core.llm.openai_client import OpenAILLMClient
from core.llm.qwen_client import QwenLLMClient


def create_llm_client(settings: AppSettings) -> BaseLLMClient:
    provider = settings.llm_provider
    if provider == "mock":
        return MockLLMClient()
    if provider == "openai":
        api_key = (settings.openai_api_key or "").strip()
        if not api_key:
            raise LLMConfigurationError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
            )
        if not settings.openai_model.strip():
            raise LLMConfigurationError(
                "OPENAI_MODEL is required when LLM_PROVIDER=openai"
            )
        return OpenAILLMClient(
            api_key=api_key,
            model=settings.openai_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if provider in {"dashscope", "qwen"}:
        api_key = (settings.dashscope_api_key or "").strip()
        base_url = settings.resolved_dashscope_base_url
        model = (settings.dashscope_model or "").strip()
        if not api_key:
            raise LLMConfigurationError(
                "DASHSCOPE_API_KEY is required when LLM_PROVIDER=dashscope"
            )
        if not base_url:
            raise LLMConfigurationError(
                "DASHSCOPE_WORKSPACE_ID or DASHSCOPE_BASE_URL is required "
                "when LLM_PROVIDER=dashscope"
            )
        if not model:
            raise LLMConfigurationError(
                "DASHSCOPE_MODEL is required when LLM_PROVIDER=dashscope"
            )
        return QwenLLMClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if provider == "siliconflow":
        api_key = (settings.siliconflow_api_key or "").strip()
        if not api_key:
            raise LLMConfigurationError(
                "SILICONFLOW_API_KEY is required when LLM_PROVIDER=siliconflow"
            )
        from core.llm.openai_compatible_client import OpenAICompatibleLLMClient

        return OpenAICompatibleLLMClient(
            base_url=settings.siliconflow_base_url,
            model=settings.siliconflow_model,
            api_key=api_key,
            timeout_seconds=settings.llm_timeout_seconds,
            provider_name="SiliconFlow",
        )
    if provider == "local":
        base_url = (settings.local_llm_base_url or "").strip()
        model = (settings.local_llm_model or "").strip()
        if not base_url:
            raise LLMConfigurationError(
                "LOCAL_LLM_BASE_URL is required when LLM_PROVIDER=local"
            )
        if not model:
            raise LLMConfigurationError(
                "LOCAL_LLM_MODEL is required when LLM_PROVIDER=local"
            )
        return LocalLLMClient(
            base_url=base_url,
            model=model,
            api_key=(settings.local_llm_api_key or "local-not-required"),
            timeout_seconds=settings.llm_timeout_seconds,
        )
    raise LLMConfigurationError(
        f"Unsupported LLM_PROVIDER '{provider}'. "
        "Expected one of: mock, openai, dashscope, qwen, siliconflow, local"
    )
