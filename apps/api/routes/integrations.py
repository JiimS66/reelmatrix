"""Outbound integrations: route approved work into the customer's stack.

Stateless by design — credentials arrive with the request, are used once, and are
never persisted. Two targets ship today:

- ``webhook``: POST a JSON payload to any http(s) endpoint the customer controls
  (Slack/Feishu/DingTalk incoming webhooks, internal OA systems, Zapier, …).
- ``linear``: create a real Linear issue via the public GraphQL API using a
  personal API key.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Literal, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/team/integrations", tags=["integrations"])

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
_OUTBOUND_TIMEOUT_SECONDS = 8.0


class DispatchRequest(BaseModel):
    target: Literal["linear", "webhook"]
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(default="", max_length=8000)
    campaign_id: Optional[str] = None
    # Webhook target endpoint (required when target == "webhook").
    url: Optional[str] = None
    # Linear personal API key (required when target == "linear"). Used once, not stored.
    api_key: Optional[str] = None


class DispatchResult(BaseModel):
    ok: bool
    target: str
    permalink: Optional[str] = None
    detail: str


def _outbound_client() -> httpx.AsyncClient:
    """Factory for the outbound HTTP client (patched in tests)."""

    return httpx.AsyncClient(timeout=_OUTBOUND_TIMEOUT_SECONDS)


def _assert_public_http_url(raw_url: str) -> str:
    """Refuse webhook targets that are not plain public http(s) endpoints.

    The URL is user-supplied and the request originates from our server, so this
    is the minimal SSRF guard: http(s) only, and the host must not resolve to a
    loopback / private / link-local / reserved address.
    """

    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="Webhook URL must be an http(s) URL with a hostname.",
        )
    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(
            status_code=400,
            detail="Webhook host could not be resolved.",
        ) from exc
    for family_info in resolved:
        address = ipaddress.ip_address(family_info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        ):
            raise HTTPException(
                status_code=400,
                detail="Webhook host resolves to a private address — refusing to send.",
            )
    return raw_url


async def _dispatch_webhook(payload: DispatchRequest) -> DispatchResult:
    if not payload.url:
        raise HTTPException(status_code=400, detail="url is required for webhook dispatch.")
    target_url = _assert_public_http_url(payload.url)
    body = {
        "source": "reelmatrix",
        "campaign_id": payload.campaign_id,
        "title": payload.title,
        "body": payload.body,
    }
    try:
        async with _outbound_client() as client:
            response = await client.post(target_url, json=body)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Webhook endpoint unreachable ({exc.__class__.__name__}).",
        ) from exc
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Webhook endpoint answered {response.status_code}.",
        )
    host = urlparse(target_url).hostname
    return DispatchResult(
        ok=True,
        target="webhook",
        detail=f"Delivered to {host} ({response.status_code}).",
    )


async def _dispatch_linear(payload: DispatchRequest) -> DispatchResult:
    if not payload.api_key:
        raise HTTPException(status_code=400, detail="api_key is required for Linear dispatch.")
    headers = {"Authorization": payload.api_key, "Content-Type": "application/json"}
    try:
        async with _outbound_client() as client:
            teams_response = await client.post(
                LINEAR_GRAPHQL_URL,
                json={"query": "{ teams(first: 1) { nodes { id name } } }"},
                headers=headers,
            )
            if teams_response.status_code in {400, 401, 403}:
                raise HTTPException(
                    status_code=400,
                    detail="Linear rejected the API key.",
                )
            if teams_response.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"Linear answered {teams_response.status_code}.",
                )
            team_nodes = (
                teams_response.json()
                .get("data", {})
                .get("teams", {})
                .get("nodes", [])
            )
            if not team_nodes:
                raise HTTPException(
                    status_code=400,
                    detail="No Linear team is visible to this API key.",
                )
            team = team_nodes[0]
            create_response = await client.post(
                LINEAR_GRAPHQL_URL,
                json={
                    "query": (
                        "mutation($input: IssueCreateInput!) {"
                        " issueCreate(input: $input) {"
                        " success issue { url identifier } } }"
                    ),
                    "variables": {
                        "input": {
                            "teamId": team["id"],
                            "title": payload.title,
                            "description": payload.body,
                        }
                    },
                },
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Linear unreachable ({exc.__class__.__name__}).",
        ) from exc
    if create_response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Linear answered {create_response.status_code}.",
        )
    issue_payload = (
        create_response.json().get("data", {}).get("issueCreate", {}) or {}
    )
    issue = issue_payload.get("issue") or {}
    if not issue_payload.get("success") or not issue:
        raise HTTPException(status_code=502, detail="Linear did not create the issue.")
    identifier = issue.get("identifier", "issue")
    return DispatchResult(
        ok=True,
        target="linear",
        permalink=issue.get("url"),
        detail=f"Created {identifier} in {team.get('name', 'Linear')}.",
    )


@router.post("/dispatch", response_model=DispatchResult)
async def dispatch_integration(payload: DispatchRequest) -> DispatchResult:
    if payload.target == "webhook":
        return await _dispatch_webhook(payload)
    return await _dispatch_linear(payload)
