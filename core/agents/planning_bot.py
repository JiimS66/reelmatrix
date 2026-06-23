import json

from core.llm.base import BaseLLMClient
from core.schemas.campaign import CampaignGenerationRequest, CampaignPlan, IdeationResult


PLANNING_SYSTEM_PROMPT = """
You are the Marketing Planning MasterBot, a senior integrated marketing planner
for small teams and cross-border founders. Convert the finalized campaign concept
into an actionable, coherent multi-channel campaign package. Preserve the approved
audience insight and core message. Define the role of each channel, content
pillars, timeline, deliverables, measurable success metrics, assumptions, and
practical execution notes.

When the request includes a target market, output language, selected channels, or
campaign duration, use those constraints directly. Include a market_adaptation
section for cross-border positioning and a draft_assets section with first-pass
marketing materials that a small team can edit, copy, and export. Draft assets
should be channel-specific and execution-ready enough for a human marketer to
revise, not generic placeholders.

When brand_context is present, use it as the source of truth for proof points,
competitors, forbidden words, target personas, tone rules, and source links. Do
not state unsourced performance, funding, customer, or user-count claims as fact.
Put every proof-oriented statement in claim_checks with status source_backed when
it has a provided source, otherwise needs_validation. If campaign_template is
"developer_tool", prioritize developer-trust channels such as launch blog,
GitHub or CLI quickstart copy, technical social posts, and engineering-lead email.

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
            "task": "campaign_planning_with_assets",
            "request": request.model_dump(mode="json"),
            "ideation_result": ideation_result.model_dump(mode="json"),
        }
        result = await self._llm_client.generate_structured(
            system_prompt=PLANNING_SYSTEM_PROMPT,
            user_prompt=json.dumps(prompt_payload, ensure_ascii=False),
            response_model=CampaignPlan,
        )
        return CampaignPlan.model_validate(result)
