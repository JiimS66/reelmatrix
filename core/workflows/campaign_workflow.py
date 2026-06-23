from core.agents.ideation_bot import IdeationBot
from core.agents.planning_bot import PlanningBot
from core.schemas.campaign import (
    CampaignGenerationRequest,
    CampaignWorkflowResponse,
    CampaignWorkflowStatus,
)


class CampaignWorkflow:
    def __init__(self, ideation_bot: IdeationBot, planning_bot: PlanningBot) -> None:
        self._ideation_bot = ideation_bot
        self._planning_bot = planning_bot

    async def run(
        self,
        request: CampaignGenerationRequest,
    ) -> CampaignWorkflowResponse:
        ideation_result = await self._ideation_bot.run(request)
        if not ideation_result.is_ready_for_planning:
            return CampaignWorkflowResponse(
                status=CampaignWorkflowStatus.NEEDS_MORE_IDEATION,
                ideation_result=ideation_result,
                campaign_plan=None,
            )

        campaign_plan = await self._planning_bot.run(request, ideation_result)
        return CampaignWorkflowResponse(
            status=CampaignWorkflowStatus.PLAN_GENERATED,
            ideation_result=ideation_result,
            campaign_plan=campaign_plan,
        )
