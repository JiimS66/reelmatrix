from typing import Optional

from fastapi import APIRouter, Depends, Header, Request

from apps.api.services.campaign_generation import CampaignGenerationService
from core.schemas.campaign import CampaignGenerationRequest, CampaignWorkflowResponse


router = APIRouter(prefix="/api/v1/campaign", tags=["campaign"])


def get_campaign_generation_service(
    request: Request,
) -> CampaignGenerationService:
    return request.app.state.campaign_generation_service


@router.post("/generate", response_model=CampaignWorkflowResponse)
async def generate_campaign(
    request_body: CampaignGenerationRequest,
    llm_provider: Optional[str] = Header(
        default=None,
        alias="X-LLM-Provider",
    ),
    service: CampaignGenerationService = Depends(
        get_campaign_generation_service
    ),
) -> CampaignWorkflowResponse:
    return await service.run(request_body, provider_id=llm_provider)
