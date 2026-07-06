from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routes.campaign import router as campaign_router
from apps.api.routes.events import router as events_router
from apps.api.routes.health import router as health_router
from apps.api.routes.integrations import router as integrations_router
from apps.api.routes.llm import router as llm_router
from apps.api.routes.team import router as team_router
from apps.api.services.campaign_generation import (
    CampaignGenerationService,
    ProviderSelectionError,
    ProviderUnavailableError,
)
from configs.settings import AppSettings, get_settings
from core.llm.base import LLMProviderError, LLMResponseValidationError


def create_app(settings: Optional[AppSettings] = None) -> FastAPI:
    active_settings = settings or get_settings()
    campaign_generation_service = CampaignGenerationService(active_settings)

    application = FastAPI(title="ReelMatrix API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[active_settings.web_origin.rstrip("/")],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-LLM-Provider", "X-Member-Id"],
    )
    application.state.campaign_generation_service = campaign_generation_service
    application.include_router(health_router)
    application.include_router(llm_router)
    application.include_router(campaign_router)
    application.include_router(team_router)
    application.include_router(integrations_router)
    application.include_router(events_router)

    @application.exception_handler(ProviderSelectionError)
    async def handle_provider_selection_error(
        request: Request,
        exc: ProviderSelectionError,
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @application.exception_handler(ProviderUnavailableError)
    async def handle_provider_unavailable_error(
        request: Request,
        exc: ProviderUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

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
