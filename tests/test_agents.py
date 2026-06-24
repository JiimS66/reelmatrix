import asyncio
from typing import Any, Dict

from core.agents.base import Agent
from core.agents.employees import IdeationAgent, PlanningAgent, agent_for_role
from core.agents.roles import ROLES
from core.llm.mock_client import MockLLMClient


def test_registry_resolves_roles_to_agents() -> None:
    client = MockLLMClient()
    assert isinstance(agent_for_role("ideation", client), IdeationAgent)
    assert isinstance(agent_for_role("planning", client), PlanningAgent)
    assert agent_for_role("planning", client).role.key == "planning"


def test_unknown_role_raises() -> None:
    try:
        agent_for_role("nope", MockLLMClient())
    except ValueError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for unknown role")


def test_roles_carry_job_descriptions() -> None:
    assert ROLES["ideation"].job_description
    assert ROLES["planning"].title == "Campaign planner"


def test_ideation_agent_runs_via_uniform_interface(
    campaign_request_data: Dict[str, Any],
) -> None:
    agent: Agent = agent_for_role("ideation", MockLLMClient())
    output = asyncio.run(agent.run({"request": campaign_request_data}))
    assert output["is_ready_for_planning"] is True
    assert output["core_message"]


def test_planning_agent_runs_from_context(
    campaign_request_data: Dict[str, Any],
) -> None:
    client = MockLLMClient()
    ideation = asyncio.run(
        agent_for_role("ideation", client).run({"request": campaign_request_data})
    )
    plan = asyncio.run(
        agent_for_role("planning", client).run(
            {"request": campaign_request_data, "ideation_result": ideation}
        )
    )
    assert plan["channels"]
    assert plan["campaign_name"]


def test_copywriter_agent_renders_one_asset_from_core() -> None:
    agent = agent_for_role("copywriter", MockLLMClient())
    out = asyncio.run(
        agent.run(
            {
                "channel": "LinkedIn",
                "core_message": "Give AI-native teams a verification loop they can trust.",
                "product_name": "TestSprite",
            }
        )
    )
    assert out["channel"] == "LinkedIn"
    assert out["content"]
    assert out["call_to_action"]
    assert "copywriter" in ROLES and ROLES["copywriter"].title == "Copywriter"
