"""Concrete digital employees.

Thin agents that wrap the typed bot logic under the uniform ``Agent`` interface,
plus the role registry the runner resolves against. The bots keep their typed,
unit-tested signatures; these adapters expose them as interchangeable employees.
"""

from core.agents.base import Agent
from core.agents.ideation_bot import IdeationBot
from core.agents.planning_bot import PlanningBot
from core.agents.roles import IDEATION, PLANNING
from core.llm.base import BaseLLMClient
from core.schemas.campaign import CampaignGenerationRequest, IdeationResult


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


_REGISTRY: dict[str, type[Agent]] = {
    IdeationAgent.role.key: IdeationAgent,
    PlanningAgent.role.key: PlanningAgent,
}


def agent_for_role(role_key: str, llm_client: BaseLLMClient) -> Agent:
    agent_cls = _REGISTRY.get(role_key)
    if agent_cls is None:
        raise ValueError(f"No agent registered for role '{role_key}'.")
    return agent_cls(llm_client)
