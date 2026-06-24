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

DEFAULT_CHANNELS = ["LinkedIn", "Email", "Blog"]


def resolve_default_assignees(
    session: Session, tenant_id: str
) -> dict[str, Optional[str]]:
    """Map each default role (ideation/planning/asset AI agents + lead) to a member id."""
    members = session.exec(
        select(Member).where(Member.tenant_id == tenant_id)
    ).all()
    assignees: dict[str, Optional[str]] = {
        "ideation": None,
        "planning": None,
        "asset": None,
        "lead": None,
    }
    for member in members:
        if member.kind == MemberKind.AI and member.agent_config:
            agent_kind = member.agent_config.get("agent_kind")
            if agent_kind in assignees and assignees[agent_kind] is None:
                assignees[agent_kind] = member.id
        elif (
            member.kind == MemberKind.HUMAN
            and member.role == MemberRole.LEAD
            and assignees["lead"] is None
        ):
            assignees["lead"] = member.id
    return assignees


def instantiate_campaign(
    session: Session,
    *,
    tenant_id: str,
    name: str,
    brief: dict,
    template: str = "general",
    created_by: Optional[str] = None,
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
    )
    session.add(campaign)

    assignees = resolve_default_assignees(session, tenant_id)

    ideation = Task(
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        kind=TaskKind.IDEATION,
        title="Ideation",
        assignee_id=assignees["ideation"],
        sequence=1,
    )
    session.add(ideation)

    planning = Task(
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        kind=TaskKind.PLANNING,
        title="Campaign plan",
        depends_on=[ideation.id],
        assignee_id=assignees["planning"],
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
                title=f"{channel} asset",
                depends_on=[planning.id],
                assignee_id=assignees["asset"],
                params={"channel": channel},
                sequence=sequence,
            )
        )
        sequence += 1

    # Fact-checking defaults to a human task assigned to the lead.
    session.add(
        Task(
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            kind=TaskKind.CLAIM_CHECK,
            title="Claim check",
            depends_on=[planning.id],
            execution_mode=ExecutionMode.HUMAN_ONLY,
            assignee_id=assignees["lead"],
            sequence=sequence,
        )
    )

    session.commit()
    return campaign
