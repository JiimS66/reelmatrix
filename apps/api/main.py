from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from apps.api.routes.campaign import router as campaign_router
from apps.api.routes.health import router as health_router
from configs.settings import AppSettings, get_settings
from core.agents.ideation_bot import IdeationBot
from core.agents.planning_bot import PlanningBot
from core.llm.base import LLMProviderError, LLMResponseValidationError
from core.llm.factory import create_llm_client
from core.workflows.campaign_workflow import CampaignWorkflow


def create_app(settings: Optional[AppSettings] = None) -> FastAPI:
    active_settings = settings or get_settings()
    llm_client = create_llm_client(active_settings)
    workflow = CampaignWorkflow(
        ideation_bot=IdeationBot(llm_client),
        planning_bot=PlanningBot(llm_client),
    )

    application = FastAPI(title="ReelMatrix API", version="0.1.0")
    application.state.campaign_workflow = workflow
    application.include_router(health_router)
    application.include_router(campaign_router)

    @application.exception_handler(LLMResponseValidationError)
    async def handle_llm_validation_error(
        request: Request,
        exc: LLMResponseValidationError,
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @application.exception_handler(LLMProviderError)
    async def handle_llm_provider_error(
        request: Request,
        exc: LLMProviderError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"detail": "The configured LLM provider request failed."},
        )

    return application


app = create_app()
