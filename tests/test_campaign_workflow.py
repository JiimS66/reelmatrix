import asyncio
from typing import Any, Dict

from core.agents.ideation_bot import IdeationBot
from core.agents.planning_bot import PlanningBot
from core.llm.mock_client import MockLLMClient
from core.schemas.campaign import CampaignGenerationRequest, CampaignWorkflowStatus
from core.workflows.campaign_workflow import CampaignWorkflow


def build_workflow() -> CampaignWorkflow:
    llm_client = MockLLMClient()
    return CampaignWorkflow(IdeationBot(llm_client), PlanningBot(llm_client))


def test_workflow_stops_when_more_ideation_is_needed(
    campaign_request_data: Dict[str, Any],
) -> None:
    campaign_request_data["user_prompt"] = "needs more ideation"
    request = CampaignGenerationRequest.model_validate(campaign_request_data)
    result = asyncio.run(build_workflow().run(request))
    assert result.status == CampaignWorkflowStatus.NEEDS_MORE_IDEATION
    assert result.campaign_plan is None


def test_workflow_generates_plan_when_ideation_is_ready(
    campaign_request_data: Dict[str, Any],
) -> None:
    request = CampaignGenerationRequest.model_validate(campaign_request_data)
    result = asyncio.run(build_workflow().run(request))
    assert result.status == CampaignWorkflowStatus.PLAN_GENERATED
    assert result.campaign_plan is not None
    assert result.ideation_result.is_ready_for_planning is True
