import json

from core.llm.base import BaseLLMClient
from core.schemas.campaign import CampaignGenerationRequest, CampaignPlan, IdeationResult


PLANNING_SYSTEM_PROMPT = """
You are the Marketing Planning MasterBot, a senior integrated marketing planner.
Convert the finalized campaign concept into an actionable, coherent multi-channel
campaign plan. Preserve the approved audience insight and core message. Define the
role of each channel, content pillars, timeline, deliverables, measurable success
metrics, assumptions, and practical execution notes.

Do not reopen broad ideation or invent external execution results. Produce only a
machine-readable plan that downstream systems can execute in later phases.
""".strip()


class PlanningBot:
    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm_client = llm_client

    async def run(
        self,
        request: CampaignGenerationRequest,
        ideation_result: IdeationResult,
    ) -> CampaignPlan:
        if not ideation_result.is_ready_for_planning:
            raise ValueError("PlanningBot requires finalized ideation")
        prompt_payload = {
            "task": "campaign_planning",
            "request": request.model_dump(mode="json"),
            "ideation_result": ideation_result.model_dump(mode="json"),
        }
        result = await self._llm_client.generate_structured(
            system_prompt=PLANNING_SYSTEM_PROMPT,
            user_prompt=json.dumps(prompt_payload, ensure_ascii=False),
            response_model=CampaignPlan,
        )
        return CampaignPlan.model_validate(result)
