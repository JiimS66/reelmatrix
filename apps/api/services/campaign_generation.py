from typing import Dict, Optional

from configs.settings import AppSettings
from core.agents.ideation_bot import IdeationBot
from core.agents.planning_bot import PlanningBot
from core.llm.base import LLMConfigurationError
from core.llm.factory import create_llm_client
from core.schemas.campaign import CampaignGenerationRequest, CampaignWorkflowResponse
from core.schemas.provider import (
    LLMProviderCatalog,
    LLMProviderInfo,
    LLMProviderKind,
)
from core.workflows.campaign_workflow import CampaignWorkflow


SUPPORTED_PROVIDERS = ("mock", "local", "openai", "dashscope")
PROVIDER_ALIASES = {"qwen": "dashscope"}


class ProviderSelectionError(RuntimeError):
    pass


class ProviderUnavailableError(RuntimeError):
    pass


class CampaignGenerationService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._default_provider = self._normalize_provider(settings.llm_provider)
        self._workflows: Dict[str, CampaignWorkflow] = {
            self._default_provider: self._create_workflow(
                self._default_provider,
                wrap_configuration_error=False,
            )
        }

    async def run(
        self,
        request: CampaignGenerationRequest,
        provider_id: Optional[str] = None,
    ) -> CampaignWorkflowResponse:
        selected_provider = self._normalize_provider(
            provider_id or self._default_provider
        )
        workflow = self._workflows.get(selected_provider)
        if workflow is None:
            workflow = self._create_workflow(
                selected_provider,
                wrap_configuration_error=True,
            )
            self._workflows[selected_provider] = workflow
        return await workflow.run(request)

    def get_provider_catalog(self) -> LLMProviderCatalog:
        return LLMProviderCatalog(
            providers=[
                self._provider_info(provider_id)
                for provider_id in SUPPORTED_PROVIDERS
            ]
        )

    def _create_workflow(
        self,
        provider_id: str,
        *,
        wrap_configuration_error: bool,
    ) -> CampaignWorkflow:
        provider_settings = self._settings.model_copy(
            update={"llm_provider": provider_id}
        )
        try:
            llm_client = create_llm_client(provider_settings)
        except LLMConfigurationError as exc:
            if not wrap_configuration_error:
                raise
            raise ProviderUnavailableError(
                f"The selected provider '{provider_id}' is not configured on the backend."
            ) from exc
        return CampaignWorkflow(
            ideation_bot=IdeationBot(llm_client),
            planning_bot=PlanningBot(llm_client),
        )

    def _normalize_provider(self, provider_id: str) -> str:
        normalized = provider_id.strip().lower()
        normalized = PROVIDER_ALIASES.get(normalized, normalized)
        if normalized not in SUPPORTED_PROVIDERS:
            supported = ", ".join(SUPPORTED_PROVIDERS)
            raise ProviderSelectionError(
                f"Unsupported model provider '{provider_id}'. Choose one of: {supported}."
            )
        return normalized

    def _provider_info(self, provider_id: str) -> LLMProviderInfo:
        if provider_id == "mock":
            return LLMProviderInfo(
                provider_id="mock",
                display_name="Mock model",
                model_name="deterministic-mock",
                kind=LLMProviderKind.DEVELOPMENT,
                description="Deterministic local responses for development and tests.",
                configured=True,
                is_default=self._default_provider == provider_id,
            )
        if provider_id == "local":
            base_url = (self._settings.local_llm_base_url or "").strip()
            model = (self._settings.local_llm_model or "").strip()
            return LLMProviderInfo(
                provider_id="local",
                display_name="Local model",
                model_name=model or "Not configured",
                kind=LLMProviderKind.LOCAL,
                description="OpenAI-compatible model running on your local network.",
                configured=bool(base_url and model),
                is_default=self._default_provider == provider_id,
            )
        if provider_id == "openai":
            api_key = (self._settings.openai_api_key or "").strip()
            model = self._settings.openai_model.strip()
            return LLMProviderInfo(
                provider_id="openai",
                display_name="ChatGPT",
                model_name=model or "Not configured",
                kind=LLMProviderKind.REMOTE,
                description="OpenAI-hosted model using the configured API key.",
                configured=bool(api_key and model),
                is_default=self._default_provider == provider_id,
            )

        api_key = (self._settings.dashscope_api_key or "").strip()
        base_url = self._settings.resolved_dashscope_base_url
        model = (self._settings.dashscope_model or "").strip()
        return LLMProviderInfo(
            provider_id="dashscope",
            display_name="Qwen",
            model_name=model or "Not configured",
            kind=LLMProviderKind.REMOTE,
            description="Qwen through Alibaba Cloud Model Studio OpenAI compatibility.",
            configured=bool(api_key and base_url and model),
            is_default=self._default_provider == provider_id,
        )
