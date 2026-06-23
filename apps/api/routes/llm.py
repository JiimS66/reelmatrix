from fastapi import APIRouter, Depends, Request

from apps.api.services.campaign_generation import CampaignGenerationService
from core.schemas.provider import LLMProviderCatalog


router = APIRouter(prefix="/api/v1/llm", tags=["llm"])


def get_campaign_generation_service(
    request: Request,
) -> CampaignGenerationService:
    return request.app.state.campaign_generation_service


@router.get("/providers", response_model=LLMProviderCatalog)
async def list_llm_providers(
    service: CampaignGenerationService = Depends(
        get_campaign_generation_service
    ),
) -> LLMProviderCatalog:
    return service.get_provider_catalog()
