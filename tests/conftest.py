import os
from typing import Any, Dict

import pytest


os.environ["APP_ENV"] = "test"
os.environ["LLM_PROVIDER"] = "mock"


@pytest.fixture
def campaign_request_data() -> Dict[str, Any]:
    return {
        "product_name": "TensorGrowth",
        "product_description": (
            "An AI marketing workspace that helps founders generate and plan campaigns."
        ),
        "target_audience": "Early-stage startup founders and lean marketing teams",
        "marketing_goal": "Generate qualified waitlist signups",
        "brand_voice": "Sharp, practical, founder-friendly",
        "constraints": ["Small team", "Limited budget", "Organic-first"],
        "user_prompt": (
            "ready for planning: create a launch campaign concept for this product"
        ),
    }
