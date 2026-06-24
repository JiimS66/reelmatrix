"""Instantiate a campaign brief into a fixed task template.

This is the task-based successor to ``CampaignWorkflow``: instead of running
ideation then planning synchronously, it persists a campaign and a small graph
of tasks (ideation -> planning -> assets + claim check) that humans and AI
members work through asynchronously. The old single-shot workflow is kept for
the existing /generate endpoint.
"""

from typing import Optional

from sqlmodel import Session, select

from core.db.models import (
    Campaign,
    ExecutionMode,
    Member,
    MemberKind,
    MemberRole,
    Task,
    TaskKind,
)
from core.workflows.scheduler import generate_schedule

DEFAULT_CHANNELS = ["LinkedIn", "Email", "Blog"]


def route_assignees(session: Session, tenant_id: str) -> dict[str, Optional[str]]:
    """Map each task kind to the member configured to own it (``handles_kinds``).

    This is the per-tenant org routing: whoever declares a kind handles it, so a
    tenant reconfigures who does what without touching this code. When two members
    declare the same kind the earliest-created wins (a stable default). The claim
    check falls back to the lead so fact-checking always reaches a human even in an
    under-configured org.
    """
    members = list(
        session.exec(
            select(Member)
            .where(Member.tenant_id == tenant_id)
            .order_by(Member.created_at)
        ).all()
    )
    routes: dict[str, Optional[str]] = {}
    for member in members:
        for kind in member.handles_kinds or []:
            routes.setdefault(kind, member.id)

    if routes.get(TaskKind.CLAIM_CHECK.value) is None:
        lead = next(
            (
                m
                for m in members
                if m.kind == MemberKind.HUMAN and m.role == MemberRole.LEAD
            ),
            None,
        )
        if lead is not None:
            routes[TaskKind.CLAIM_CHECK.value] = lead.id
    return routes


def instantiate_campaign(
    session: Session,
    *,
    tenant_id: str,
    name: str,
    brief: dict,
    template: str = "general",
    created_by: Optional[str] = None,
    event_name: Optional[str] = None,
    event_date: Optional[str] = None,
    asset_mode: ExecutionMode = ExecutionMode.AI_AUTO,
) -> Campaign:
    """Create a campaign plus its fixed task graph, returning the campaign.

    Tasks are created but not run; a task runner executes AI tasks once their
    dependencies are satisfied.
    """
    campaign = Campaign(
        tenant_id=tenant_id,
        name=name,
        template=template,
        brief=brief,
        created_by=created_by,
        event_name=event_name,
        event_date=event_date,
    )
    session.add(campaign)

    routes = route_assignees(session, tenant_id)

    ideation = Task(
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        kind=TaskKind.IDEATION,
        title="Ideation",
        execution_mode=ExecutionMode.AI_AUTO,
        assignee_id=routes.get(TaskKind.IDEATION.value),
        sequence=1,
    )
    session.add(ideation)

    planning = Task(
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        kind=TaskKind.PLANNING,
        title="Campaign plan",
        execution_mode=ExecutionMode.AI_AUTO,
        depends_on=[ideation.id],
        assignee_id=routes.get(TaskKind.PLANNING.value),
        sequence=2,
    )
    session.add(planning)

    channels = brief.get("selected_channels") or DEFAULT_CHANNELS
    sequence = 3
    for channel in channels:
        session.add(
            Task(
                tenant_id=tenant_id,
                campaign_id=campaign.id,
                kind=TaskKind.ASSET,
                title=f"{channel} post",
                execution_mode=asset_mode,
                depends_on=[planning.id],
                assignee_id=routes.get(TaskKind.ASSET.value),
                params={"channel": channel},
                sequence=sequence,
            )
        )
        sequence += 1

    # Fact-checking is a human-only task; route_assignees guarantees a lead fallback.
    session.add(
        Task(
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            kind=TaskKind.CLAIM_CHECK,
            title="Claim check",
            depends_on=[planning.id],
            execution_mode=ExecutionMode.HUMAN_ONLY,
            assignee_id=routes.get(TaskKind.CLAIM_CHECK.value),
            sequence=sequence,
        )
    )

    generate_schedule(session, campaign)
    session.commit()
    return campaign
