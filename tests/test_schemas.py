from typing import Any, Dict

import pytest
from pydantic import ValidationError

from core.schemas.campaign import (
    CampaignGenerationRequest,
    ConversationMessage,
)


def test_campaign_request_accepts_valid_payload(
    campaign_request_data: Dict[str, Any],
) -> None:
    request = CampaignGenerationRequest.model_validate(campaign_request_data)
    assert request.product_name == "TensorGrowth"
    assert request.constraints == ["Small team", "Limited budget", "Organic-first"]


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
