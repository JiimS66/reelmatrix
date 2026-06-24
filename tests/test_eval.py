"""A miniature eval set: run representative briefs through the agent pipeline and
assert the rendered posts pass the deterministic checks and stay consistent with
the shared core. A quality-regression gate (M5)."""

import asyncio

from core.agents.employees import agent_for_role
from core.content.platform_specs import format_checks
from core.llm.mock_client import MockLLMClient

BRIEFS = [
    {
        "product_name": "TestSprite",
        "product_description": "An agentic testing platform that verifies AI-generated code with live browsers and APIs.",
        "target_audience": "Engineering leaders and AI-native developers using coding agents",
        "marketing_goal": "Generate qualified developer signups and API key starts",
        "user_prompt": "ready for planning: launch campaign for TestSprite",
        "selected_channels": ["LinkedIn", "Email", "Landing Page"],
    },
    {
        "product_name": "TensorGrowth",
        "product_description": "An AI marketing workspace that helps founders generate and plan campaigns end to end.",
        "target_audience": "Early-stage startup founders and lean marketing teams",
        "marketing_goal": "Generate qualified waitlist signups within one quarter",
        "user_prompt": "ready for planning: create a launch campaign concept",
        "selected_channels": ["LinkedIn", "Email"],
    },
]


def _run_pipeline(brief: dict):
    client = MockLLMClient()
    ideation = asyncio.run(agent_for_role("ideation", client).run({"request": brief}))
    plan = asyncio.run(
        agent_for_role("planning", client).run(
            {"request": brief, "ideation_result": ideation}
        )
    )
    posts = []
    for channel in brief["selected_channels"]:
        post = asyncio.run(
            agent_for_role("copywriter", client).run(
                {
                    "channel": channel,
                    "core_message": plan["core_message"],
                    "product_name": brief["product_name"],
                }
            )
        )
        posts.append((channel, post))
    return plan, posts


def test_eval_posts_pass_checks_and_stay_consistent() -> None:
    for brief in BRIEFS:
        plan, posts = _run_pipeline(brief)
        assert plan["core_message"]
        for channel, post in posts:
            # Format-clean for its platform.
            assert format_checks(post, channel) == []
            # Cross-platform consistency: every post carries the shared core message.
            assert plan["core_message"] in post["content"]
            assert post["call_to_action"]
