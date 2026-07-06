"""Outbound integrations: route approved work into the customer's stack.

Credentials are stateless by design — they arrive with the request, are used
once, and are never persisted. Three capabilities ship today:

- ``webhook``: POST a JSON payload to any http(s) endpoint the customer controls
  (Slack/Feishu/DingTalk incoming webhooks, internal OA systems, Zapier, …).
- ``linear`` dispatch: create a single Linear issue via the public GraphQL API.
- ``linear`` campaign sync: mirror a campaign's launch timeline into Linear —
  one project per campaign, one issue per dated task (due date + status +
  content preview), **idempotently** via the ExternalLink mapping table, so
  re-syncing updates issues instead of duplicating them. One-way push v1:
  ReelMatrix is the source of truth.
"""

from __future__ import annotations

import ipaddress
import socket
from datetime import datetime, timezone
from typing import Literal, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from apps.api.routes.team import get_current_member
from apps.api.schemas.team import ExternalLinkRead
from core.db.engine import get_session
from core.db.models import Campaign, ExternalLink, Member, Task, TaskKind

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


# --- Campaign timeline sync: the launch schedule lives in the customer's OA ---


class SyncCampaignRequest(BaseModel):
    campaign_id: str
    # Linear personal API key. Used once, not stored.
    api_key: str = Field(min_length=1)


class SyncedIssue(BaseModel):
    task_id: str
    identifier: str
    url: Optional[str] = None


class SyncCampaignResult(BaseModel):
    ok: bool
    project_url: Optional[str] = None
    created: int = 0
    updated: int = 0
    issues: list[SyncedIssue] = []
    detail: str = ""


_STATUS_LABEL = {
    "todo": "Todo",
    "in_progress": "In progress",
    "needs_review": "In review (waiting on a human)",
    "done": "Approved",
    "blocked": "Blocked",
}


async def _linear_query(
    client: httpx.AsyncClient, api_key: str, query: str, variables: Optional[dict] = None
) -> dict:
    response = await client.post(
        LINEAR_GRAPHQL_URL,
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": api_key, "Content-Type": "application/json"},
    )
    if response.status_code in {400, 401, 403}:
        raise HTTPException(status_code=400, detail="Linear rejected the request/API key.")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502, detail=f"Linear answered {response.status_code}."
        )
    body = response.json()
    if body.get("errors"):
        message = body["errors"][0].get("message", "Linear returned an error.")
        raise HTTPException(status_code=502, detail=f"Linear: {message}")
    return body.get("data", {})


def _issue_description(campaign: Campaign, task: Task) -> str:
    output = task.output or {}
    lines = [
        f"Status: {_STATUS_LABEL.get(task.status.value, task.status.value)}",
        f"Channel: {(task.params or {}).get('channel', '—')}",
        f"Campaign: {campaign.name} (ReelMatrix)",
    ]
    title = str(output.get("title", "")).strip()
    content = str(output.get("content", "")).strip()
    if title:
        lines += ["", f"**{title}**"]
    if content:
        preview = content if len(content) <= 1500 else content[:1500] + " …"
        lines += ["", preview]
    return "\n".join(lines)


def _get_link(
    session: Session, tenant_id: str, local_kind: str, local_id: str
) -> Optional[ExternalLink]:
    return session.exec(
        select(ExternalLink).where(
            ExternalLink.tenant_id == tenant_id,
            ExternalLink.provider == "linear",
            ExternalLink.local_kind == local_kind,
            ExternalLink.local_id == local_id,
        )
    ).first()


@router.post("/linear/sync-campaign", response_model=SyncCampaignResult)
async def sync_campaign_to_linear(
    payload: SyncCampaignRequest,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> SyncCampaignResult:
    """Mirror the campaign's dated tasks into a Linear project, idempotently."""
    campaign = session.get(Campaign, payload.campaign_id)
    if campaign is None or campaign.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    tasks = [
        t
        for t in session.exec(
            select(Task)
            .where(Task.campaign_id == campaign.id)
            .order_by(Task.due_date, Task.sequence)
        ).all()
        if t.due_date and t.kind in (TaskKind.ASSET, TaskKind.CLAIM_CHECK)
    ]
    if not tasks:
        raise HTTPException(
            status_code=400,
            detail="This campaign has no dated tasks yet — run it first.",
        )

    now = datetime.now(timezone.utc)
    created = updated = 0
    issues: list[SyncedIssue] = []
    try:
        async with _outbound_client() as client:
            teams = await _linear_query(
                client, payload.api_key, "{ teams(first: 1) { nodes { id name } } }"
            )
            team_nodes = teams.get("teams", {}).get("nodes", [])
            if not team_nodes:
                raise HTTPException(
                    status_code=400, detail="No Linear team is visible to this API key."
                )
            team = team_nodes[0]

            # Project: reuse the linked one, else create and link it.
            project_link = _get_link(session, campaign.tenant_id, "campaign", campaign.id)
            if project_link is None:
                data = await _linear_query(
                    client,
                    payload.api_key,
                    "mutation($input: ProjectCreateInput!) { projectCreate(input: $input)"
                    " { success project { id url } } }",
                    {
                        "input": {
                            "teamIds": [team["id"]],
                            "name": f"{campaign.name} — launch timeline",
                        }
                    },
                )
                project = (data.get("projectCreate", {}) or {}).get("project") or {}
                if not project:
                    raise HTTPException(
                        status_code=502, detail="Linear did not create the project."
                    )
                project_link = ExternalLink(
                    tenant_id=campaign.tenant_id,
                    provider="linear",
                    local_kind="campaign",
                    local_id=campaign.id,
                    external_id=project["id"],
                    url=project.get("url"),
                )
                session.add(project_link)
                session.flush()

            for task in tasks:
                issue_title = f"[{(task.params or {}).get('channel') or task.kind.value}] {task.title}"
                issue_input = {
                    "title": issue_title,
                    "description": _issue_description(campaign, task),
                    "dueDate": task.due_date,
                }
                link = _get_link(session, campaign.tenant_id, "task", task.id)
                if link is None:
                    data = await _linear_query(
                        client,
                        payload.api_key,
                        "mutation($input: IssueCreateInput!) { issueCreate(input: $input)"
                        " { success issue { id identifier url } } }",
                        {
                            "input": {
                                **issue_input,
                                "teamId": team["id"],
                                "projectId": project_link.external_id,
                            }
                        },
                    )
                    issue = (data.get("issueCreate", {}) or {}).get("issue") or {}
                    if not issue:
                        continue
                    session.add(
                        ExternalLink(
                            tenant_id=campaign.tenant_id,
                            provider="linear",
                            local_kind="task",
                            local_id=task.id,
                            external_id=issue["id"],
                            url=issue.get("url"),
                        )
                    )
                    created += 1
                    issues.append(
                        SyncedIssue(
                            task_id=task.id,
                            identifier=issue.get("identifier", ""),
                            url=issue.get("url"),
                        )
                    )
                else:
                    await _linear_query(
                        client,
                        payload.api_key,
                        "mutation($id: String!, $input: IssueUpdateInput!)"
                        " { issueUpdate(id: $id, input: $input) { success } }",
                        {"id": link.external_id, "input": issue_input},
                    )
                    link.updated_at = now
                    session.add(link)
                    updated += 1
                    issues.append(
                        SyncedIssue(task_id=task.id, identifier="", url=link.url)
                    )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Linear unreachable ({exc.__class__.__name__})."
        ) from exc

    session.commit()
    return SyncCampaignResult(
        ok=True,
        project_url=project_link.url,
        created=created,
        updated=updated,
        issues=issues,
        detail=(
            f"Synced {created + updated} tasks to {team.get('name', 'Linear')} "
            f"({created} created, {updated} updated)."
        ),
    )


@router.get("/links", response_model=list[ExternalLinkRead])
def list_external_links(
    campaign_id: str,
    actor: Member = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[ExternalLinkRead]:
    """Every external mapping for a campaign (the project + its task issues)."""
    campaign = session.get(Campaign, campaign_id)
    if campaign is None or campaign.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    task_ids = {
        t.id
        for t in session.exec(select(Task).where(Task.campaign_id == campaign.id)).all()
    }
    rows = session.exec(
        select(ExternalLink).where(ExternalLink.tenant_id == actor.tenant_id)
    ).all()
    return [
        ExternalLinkRead.model_validate(link)
        for link in rows
        if (link.local_kind == "campaign" and link.local_id == campaign.id)
        or (link.local_kind == "task" and link.local_id in task_ids)
    ]
