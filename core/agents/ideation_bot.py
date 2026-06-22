import json

from core.llm.base import BaseLLMClient
from core.schemas.campaign import CampaignGenerationRequest, IdeationResult


IDEATION_SYSTEM_PROMPT = """
You are the Marketing Ideation ChatBot, a senior creative marketing strategist.
Refine the user's campaign idea before execution planning. Identify the sharpest
campaign concept, core message, audience insight, useful creative angles, and any
risks or assumptions. Do not produce a detailed channel plan or timeline.

If the product, audience, goal, campaign promise, or desired action is too vague,
ask focused follow-up questions and set is_ready_for_planning to false. Set it to
true only when the concept is specific enough for a planning specialist to create
an actionable campaign. Keep the result concise and evidence-aware.
""".strip()


class IdeationBot:
    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm_client = llm_client

    async def run(self, request: CampaignGenerationRequest) -> IdeationResult:
        prompt_payload = {
            "task": "marketing_ideation",
            "request": request.model_dump(mode="json"),
        }
        result = await self._llm_client.generate_structured(
            system_prompt=IDEATION_SYSTEM_PROMPT,
            user_prompt=json.dumps(prompt_payload, ensure_ascii=False),
            response_model=IdeationResult,
        )
        return IdeationResult.model_validate(result)
