import asyncio
from typing import Any, Callable

import httpx
from fastapi import FastAPI

from apps.api.main import create_app
from apps.api.routes import integrations
from configs.settings import AppSettings


def build_app() -> FastAPI:
    settings = AppSettings(_env_file=None, app_env="test", llm_provider="mock")
    return create_app(settings)


async def request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, **kwargs)


def _patch_outbound(
    monkeypatch: Any,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(integrations, "_outbound_client", factory)


def test_webhook_dispatch_delivers_payload(monkeypatch: Any) -> None:
    seen: dict[str, Any] = {}

    def handler(outbound: httpx.Request) -> httpx.Response:
        seen["url"] = str(outbound.url)
        seen["json"] = outbound.read()
        return httpx.Response(200, json={"ok": True})

    _patch_outbound(monkeypatch, handler)
    monkeypatch.setattr(
        integrations, "_assert_public_http_url", lambda raw_url: raw_url
    )

    response = asyncio.run(
        request(
            "POST",
            "/api/v1/team/integrations/dispatch",
            json={
                "target": "webhook",
                "url": "https://hooks.example.com/reelmatrix",
                "title": "LinkedIn update: launch recap",
                "body": "3 posts live, 41 signups.",
                "campaign_id": "camp-1",
            },
        )
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True and payload["target"] == "webhook"
    assert seen["url"] == "https://hooks.example.com/reelmatrix"
    assert b"reelmatrix" in seen["json"]


def test_webhook_dispatch_refuses_private_hosts() -> None:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/team/integrations/dispatch",
            json={
                "target": "webhook",
                "url": "http://127.0.0.1:9000/internal",
                "title": "should not send",
            },
        )
    )
    assert response.status_code == 400
    assert "private address" in response.json()["detail"]


def test_webhook_dispatch_requires_url() -> None:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/team/integrations/dispatch",
            json={"target": "webhook", "title": "no url"},
        )
    )
    assert response.status_code == 400


def test_linear_dispatch_creates_issue(monkeypatch: Any) -> None:
    calls: list[str] = []

    def handler(outbound: httpx.Request) -> httpx.Response:
        body = outbound.read().decode()
        calls.append(body)
        assert outbound.headers["Authorization"] == "lin_api_test_key"
        if "teams(first" in body:
            return httpx.Response(
                200,
                json={"data": {"teams": {"nodes": [{"id": "team-1", "name": "Growth"}]}}},
            )
        return httpx.Response(
            200,
            json={
                "data": {
                    "issueCreate": {
                        "success": True,
                        "issue": {
                            "url": "https://linear.app/growth/issue/GRO-7",
                            "identifier": "GRO-7",
                        },
                    }
                }
            },
        )

    _patch_outbound(monkeypatch, handler)

    response = asyncio.run(
        request(
            "POST",
            "/api/v1/team/integrations/dispatch",
            json={
                "target": "linear",
                "api_key": "lin_api_test_key",
                "title": "Ship launch recap post",
                "body": "Approved in ReelMatrix — ready to publish.",
            },
        )
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["permalink"] == "https://linear.app/growth/issue/GRO-7"
    assert "GRO-7" in payload["detail"]
    assert len(calls) == 2


def test_linear_dispatch_requires_api_key() -> None:
    response = asyncio.run(
        request(
            "POST",
            "/api/v1/team/integrations/dispatch",
            json={"target": "linear", "title": "missing key"},
        )
    )
    assert response.status_code == 400


def test_linear_dispatch_surfaces_rejected_key(monkeypatch: Any) -> None:
    def handler(outbound: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"errors": [{"message": "bad key"}]})

    _patch_outbound(monkeypatch, handler)

    response = asyncio.run(
        request(
            "POST",
            "/api/v1/team/integrations/dispatch",
            json={"target": "linear", "api_key": "bad", "title": "x"},
        )
    )
    assert response.status_code == 400
    assert "rejected" in response.json()["detail"]
