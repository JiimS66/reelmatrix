from typing import Any, Dict

import pytest
from pydantic import ValidationError

from core.schemas.campaign import (
    CampaignGenerationRequest,
    CampaignPlan,
    ConversationMessage,
)


def test_campaign_request_accepts_valid_payload(
    campaign_request_data: Dict[str, Any],
) -> None:
    request = CampaignGenerationRequest.model_validate(campaign_request_data)
    assert request.product_name == "TensorGrowth"
    assert request.constraints == ["Small team", "Limited budget", "Organic-first"]
    assert request.target_market == "United States"
    assert request.selected_channels == ["LinkedIn", "Email", "Landing Page"]


def test_campaign_request_rejects_unknown_fields(
    campaign_request_data: Dict[str, Any],
) -> None:
    campaign_request_data["unexpected"] = "not allowed"
    with pytest.raises(ValidationError):
        CampaignGenerationRequest.model_validate(campaign_request_data)


def test_conversation_message_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        ConversationMessage(role="tool", content="Unsupported role")


def test_campaign_request_rejects_blank_required_text(
    campaign_request_data: Dict[str, Any],
) -> None:
    campaign_request_data["product_name"] = "   "
    with pytest.raises(ValidationError):
        CampaignGenerationRequest.model_validate(campaign_request_data)


def test_campaign_plan_accepts_assets_and_market_adaptation() -> None:
    plan = CampaignPlan.model_validate(
        {
            "campaign_name": "Cross-Border Launch Sprint",
            "campaign_objective": "Generate qualified waitlist signups",
            "target_audience": "Early-stage startup founders",
            "core_message": "Turn campaign planning into measurable momentum.",
            "channels": [
                {
                    "channel_name": "LinkedIn",
                    "role_in_campaign": "Build awareness",
                    "content_types": ["Founder post"],
                    "key_messages": ["Move from idea to campaign assets"],
                    "cadence": "Three posts per week",
                    "success_metrics": ["Waitlist clicks"],
                }
            ],
            "content_pillars": ["Practical campaign workflows"],
            "timeline": [
                {
                    "phase_name": "Foundation",
                    "timing": "Week 1",
                    "objective": "Clarify the message",
                    "key_activities": ["Publish the founder narrative"],
                }
            ],
            "deliverables": [
                {
                    "name": "Founder narrative",
                    "channel": "LinkedIn",
                    "format": "Text post",
                    "purpose": "Introduce the campaign point of view",
                }
            ],
            "success_metrics": ["Qualified signups"],
            "assumptions": ["A waitlist destination exists"],
            "execution_notes": ["Keep CTA consistent"],
            "market_adaptation": {
                "target_market": "United States",
                "language_strategy": "Use concise English benefit-led copy.",
                "positioning_recommendations": ["Lead with practical outcomes"],
                "localization_notes": ["Avoid literal translation"],
                "cultural_risks": ["Do not overpromise automation"],
                "suggested_phrases": ["Build a campaign package in one session"],
            },
            "draft_assets": [
                {
                    "asset_type": "Social post",
                    "channel": "LinkedIn",
                    "title": "Founder launch narrative",
                    "content": "A first-pass campaign post.",
                    "call_to_action": "Join the waitlist.",
                    "notes": ["Add proof before publishing"],
                }
            ],
        }
    )
    assert plan.market_adaptation is not None
    assert plan.draft_assets is not None
    assert plan.draft_assets[0].asset_type == "Social post"
