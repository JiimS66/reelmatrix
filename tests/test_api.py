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
    assert response.json() == {"status": "ok"}


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
    assert body["status"] == "plan_generated"
    assert body["campaign_plan"]["campaign_name"] == "TensorGrowth Lean Growth Launch"


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
