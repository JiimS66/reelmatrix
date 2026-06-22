from fastapi import APIRouter, Depends, Request

from core.schemas.campaign import CampaignGenerationRequest, CampaignWorkflowResponse
from core.workflows.campaign_workflow import CampaignWorkflow


router = APIRouter(prefix="/api/v1/campaign", tags=["campaign"])


def get_campaign_workflow(request: Request) -> CampaignWorkflow:
    return request.app.state.campaign_workflow


@router.post("/generate", response_model=CampaignWorkflowResponse)
async def generate_campaign(
    request_body: CampaignGenerationRequest,
    workflow: CampaignWorkflow = Depends(get_campaign_workflow),
) -> CampaignWorkflowResponse:
    return await workflow.run(request_body)
