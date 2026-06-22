import asyncio
import inspect
from typing import Any, Dict

import core.agents.ideation_bot as ideation_module
from core.agents.ideation_bot import IdeationBot
from core.llm.mock_client import MockLLMClient
from core.schemas.campaign import CampaignGenerationRequest


def test_ideation_bot_returns_ready_mock_result(
    campaign_request_data: Dict[str, Any],
) -> None:
    request = CampaignGenerationRequest.model_validate(campaign_request_data)
    result = asyncio.run(IdeationBot(MockLLMClient()).run(request))
    assert result.is_ready_for_planning is True
    assert result.follow_up_questions == []
    assert result.recommended_angles


def test_ideation_bot_returns_follow_up_questions(
    campaign_request_data: Dict[str, Any],
) -> None:
    campaign_request_data["user_prompt"] = "needs more ideation"
    request = CampaignGenerationRequest.model_validate(campaign_request_data)
    result = asyncio.run(IdeationBot(MockLLMClient()).run(request))
    assert result.is_ready_for_planning is False
    assert len(result.follow_up_questions) >= 1


def test_ideation_bot_does_not_import_concrete_providers() -> None:
    source = inspect.getsource(ideation_module)
    assert "openai_client" not in source
    assert "local_client" not in source
