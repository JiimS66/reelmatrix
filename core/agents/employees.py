"""Concrete digital employees.

Thin agents that wrap the typed bot logic under the uniform ``Agent`` interface,
plus the role registry the runner resolves against. The bots keep their typed,
unit-tested signatures; these adapters expose them as interchangeable employees.
"""

import json

from core.agents.base import Agent
from core.agents.ideation_bot import IdeationBot
from core.agents.planning_bot import PlanningBot
from core.agents.roles import COPYWRITER, IDEATION, PLANNING
from core.llm.base import BaseLLMClient
from core.schemas.campaign import (
    CampaignAsset,
    CampaignGenerationRequest,
    IdeationResult,
)


class IdeationAgent(Agent):
    role = IDEATION

    async def run(self, context: dict) -> dict:
        request = CampaignGenerationRequest.model_validate(context["request"])
        result = await IdeationBot(self._llm_client).run(request)
        return result.model_dump(mode="json")


class PlanningAgent(Agent):
    role = PLANNING

    async def run(self, context: dict) -> dict:
        request = CampaignGenerationRequest.model_validate(context["request"])
        ideation = IdeationResult.model_validate(context["ideation_result"])
        plan = await PlanningBot(self._llm_client).run(request, ideation)
        return plan.model_dump(mode="json")


COPYWRITER_SYSTEM_PROMPT = """
You are a senior marketing copywriter. Render ONE platform-optimized post from the
shared campaign content core, the platform's format spec, and the brand. Keep the
same core message and only the approved claims as the other channels — be
consistent, and never invent unsourced performance, funding, customer, or
user-count claims. Obey the brand voice, tone rules, and forbidden words, and the
platform's length and structure. If revision_notes lists problems with a previous
draft, fix exactly those issues and change nothing else. Return only the single asset.
""".strip()


class CopywriterAgent(Agent):
    role = COPYWRITER

    async def run(self, context: dict) -> dict:
        payload = {
            "task": "copywriting",
            "channel": context.get("channel", ""),
            "core_message": context.get("core_message", ""),
            "product_name": context.get("product_name", ""),
            "platform": context.get("platform", {}),
            "brand": context.get("brand", {}),
            "recent_feedback": context.get("recent_feedback", []),
            "revision_notes": context.get("revision_notes", []),
        }
        asset = await self._llm_client.generate_structured(
            system_prompt=COPYWRITER_SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
            response_model=CampaignAsset,
        )
        return asset.model_dump(mode="json")


_REGISTRY: dict[str, type[Agent]] = {
    IdeationAgent.role.key: IdeationAgent,
    PlanningAgent.role.key: PlanningAgent,
    CopywriterAgent.role.key: CopywriterAgent,
}


def agent_for_role(role_key: str, llm_client: BaseLLMClient) -> Agent:
    agent_cls = _REGISTRY.get(role_key)
    if agent_cls is None:
        raise ValueError(f"No agent registered for role '{role_key}'.")
    return agent_cls(llm_client)
