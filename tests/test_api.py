import asyncio
from typing import Any, Dict

import httpx
from fastapi import FastAPI

from apps.api.main import create_app
from configs.settings import AppSettings


def build_app() -> FastAPI:
    settings = AppSettings(_env_file=None, app_env="test", llm_provider="mock")
    return create_app(settings)


async def request(
    method: str,
    path: str,
    **kwargs: Any,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, **kwargs)


def test_health_endpoint() -> None:
    response = asyncio.run(request("GET", "/health"))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # Deploy marker: the deployed commit (or "unknown" outside a stamped release).
    assert isinstance(body["commit"], str) and body["commit"]


def test_cors_preflight_allows_configured_web_origin() -> None:
    response = asyncio.run(
        request(
            "OPTIONS",
            "/api/v1/campaign/generate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:3000"
    )
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "X-LLM-Provider" in response.headers[
        "access-control-allow-headers"
    ]


def test_provider_catalog_exposes_local_and_remote_choices() -> None:
    response = asyncio.run(request("GET", "/api/v1/llm/providers"))
    assert response.status_code == 200
    providers = {
        item["provider_id"]: item for item in response.json()["providers"]
    }
    assert providers["local"]["kind"] == "local"
    assert providers["openai"]["display_name"] == "ChatGPT"
    assert providers["openai"]["kind"] == "remote"
    assert providers["dashscope"]["display_name"] == "Qwen"
    assert providers["dashscope"]["kind"] == "remote"
    assert providers["mock"]["is_default"] is True


def test_campaign_endpoint_generates_plan(
    campaign_request_data: Dict[str, Any],
) -> None:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/campaign/generate",
            json=campaign_request_data,
        )
    )
    assert response.status_code == 200
    body = response.json()
    plan = body["campaign_plan"]
    assert body["status"] == "plan_generated"
    assert plan["campaign_name"] == "TensorGrowth Cross-Border Launch Sprint"
    assert plan["market_adaptation"]["target_market"] == "United States"
    assert len(plan["draft_assets"]) == 3
    assert {asset["channel"] for asset in plan["draft_assets"]} == {
        "LinkedIn",
        "Email",
        "Landing Page",
    }


def test_campaign_endpoint_generates_developer_tool_package(
    campaign_request_data: Dict[str, Any],
) -> None:
    campaign_request_data.update(
        {
            "product_name": "TestSprite",
            "product_description": "An agentic testing platform for AI-native teams.",
            "target_audience": "Engineering leaders and developers using coding agents",
            "marketing_goal": "Generate API key starts and technical demo calls",
            "campaign_template": "developer_tool",
            "selected_channels": ["Blog", "GitHub / CLI", "Email"],
            "brand_context": {
                "target_personas": ["AI-native engineering teams"],
                "proof_points": [
                    {
                        "claim": "TestSprite announced $6.7M in seed funding",
                        "source": "https://www.geekwire.com/",
                    },
                    {
                        "claim": "CLI install volume is growing",
                        "source": None,
                    },
                ],
                "forbidden_words": ["bug-free"],
                "competitors": ["Cypress", "Playwright"],
                "tone_rules": ["Lead with technical proof"],
                "source_links": ["https://www.testsprite.com/"],
            },
        }
    )
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/campaign/generate",
            json=campaign_request_data,
        )
    )

    assert response.status_code == 200
    plan = response.json()["campaign_plan"]
    assert plan["campaign_name"] == "TestSprite Developer Trust Launch"
    assert {asset["channel"] for asset in plan["draft_assets"]} == {
        "Blog",
        "GitHub / CLI",
        "Email",
    }
    assert any(
        claim["claim"] == "TestSprite announced $6.7M in seed funding"
        and claim["status"] == "source_backed"
        for claim in plan["claim_checks"]
    )
    assert any(
        claim["claim"] == "CLI install volume is growing"
        and claim["status"] == "needs_validation"
        for claim in plan["claim_checks"]
    )


def test_campaign_endpoint_accepts_explicit_provider_selection(
    campaign_request_data: Dict[str, Any],
) -> None:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/campaign/generate",
            headers={"X-LLM-Provider": "mock"},
            json=campaign_request_data,
        )
    )
    assert response.status_code == 200
    assert response.json()["status"] == "plan_generated"


def test_campaign_endpoint_rejects_unknown_provider(
    campaign_request_data: Dict[str, Any],
) -> None:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/campaign/generate",
            headers={"X-LLM-Provider": "unknown"},
            json=campaign_request_data,
        )
    )
    assert response.status_code == 400
    assert "Unsupported model provider" in response.json()["detail"]


def test_campaign_endpoint_reports_unconfigured_provider(
    campaign_request_data: Dict[str, Any],
) -> None:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/campaign/generate",
            headers={"X-LLM-Provider": "openai"},
            json=campaign_request_data,
        )
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_campaign_endpoint_returns_more_ideation_branch(
    campaign_request_data: Dict[str, Any],
) -> None:
    campaign_request_data["user_prompt"] = "needs more ideation"
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/campaign/generate",
            json=campaign_request_data,
        )
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_more_ideation"
    assert body["campaign_plan"] is None


def test_campaign_endpoint_returns_clear_validation_error(
    campaign_request_data: Dict[str, Any],
) -> None:
    del campaign_request_data["product_name"]
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/campaign/generate",
            json=campaign_request_data,
        )
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "product_name"
