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
    assert plan.campaign_name == "TensorGrowth Cross-Border Launch Sprint"
    assert len(plan.channels) == 3
    assert plan.deliverables
    assert plan.market_adaptation is not None
    assert plan.market_adaptation.target_market == "United States"
    assert plan.draft_assets is not None
    assert {asset.channel for asset in plan.draft_assets} == {
        "LinkedIn",
        "Email",
        "Landing Page",
    }


def test_planning_bot_returns_developer_tool_package(
    campaign_request_data: Dict[str, Any],
) -> None:
    campaign_request_data.update(
        {
            "product_name": "TestSprite",
            "campaign_template": "developer_tool",
            "selected_channels": ["Blog", "GitHub / CLI"],
            "brand_context": {
                "target_personas": ["AI-native engineering teams"],
                "proof_points": [
                    {
                        "claim": "TestSprite announced $6.7M in seed funding",
                        "source": "https://www.geekwire.com/",
                    }
                ],
                "forbidden_words": ["bug-free"],
                "competitors": ["Cypress"],
                "tone_rules": ["Use technical proof"],
                "source_links": ["https://www.testsprite.com/"],
            },
        }
    )
    request = CampaignGenerationRequest.model_validate(campaign_request_data)
    llm_client = MockLLMClient()
    ideation = asyncio.run(IdeationBot(llm_client).run(request))
    plan = asyncio.run(PlanningBot(llm_client).run(request, ideation))

    assert plan.campaign_name == "TestSprite Developer Trust Launch"
    assert plan.draft_assets is not None
    assert {asset.channel for asset in plan.draft_assets} == {"Blog", "GitHub / CLI"}
    assert plan.claim_checks is not None
    assert plan.claim_checks[0].status == "source_backed"
    assert "bug-free" in " ".join(plan.execution_notes)


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
