import asyncio
import inspect
from typing import Any, Dict

import pytest

import core.agents.planning_bot as planning_module
from core.agents.ideation_bot import IdeationBot
from core.agents.planning_bot import PlanningBot
from core.llm.mock_client import MockLLMClient
from core.schemas.campaign import CampaignGenerationRequest


def test_planning_bot_returns_structured_mock_plan(
    campaign_request_data: Dict[str, Any],
) -> None:
    request = CampaignGenerationRequest.model_validate(campaign_request_data)
    llm_client = MockLLMClient()
    ideation = asyncio.run(IdeationBot(llm_client).run(request))
    plan = asyncio.run(PlanningBot(llm_client).run(request, ideation))
    assert plan.campaign_name == "TensorGrowth Lean Growth Launch"
    assert len(plan.channels) == 2
    assert plan.deliverables


def test_planning_bot_rejects_unfinished_ideation(
    campaign_request_data: Dict[str, Any],
) -> None:
    campaign_request_data["user_prompt"] = "needs more ideation"
    request = CampaignGenerationRequest.model_validate(campaign_request_data)
    llm_client = MockLLMClient()
    ideation = asyncio.run(IdeationBot(llm_client).run(request))
    with pytest.raises(ValueError, match="finalized ideation"):
        asyncio.run(PlanningBot(llm_client).run(request, ideation))


def test_planning_bot_does_not_import_concrete_providers() -> None:
    source = inspect.getsource(planning_module)
    assert "openai_client" not in source
    assert "local_client" not in source
