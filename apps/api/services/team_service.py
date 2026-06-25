"""Service layer for the human-AI team workspace.

Holds the DB operations and permission checks behind the team API. Every query
is scoped to the acting member's tenant. The runner (AI execution) is invoked
from the route layer because it is async; this module stays synchronous.
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlmodel import Session, select

from core.db.models import (
    Annotation,
    AttributeOutcome,
    BrandProfile,
    BrandTerm,
    Campaign,
    Comment,
    ConsentRecord,
    ContentAtom,
    ContentVersion,
    DirectMessage,
    DiscoveredSegmentCandidate,
    EpisodicNote,
    Experiment,
    ExperimentVariant,
    IncrementalityTest,
    ExecutionMode,
    Member,
    MemberKind,
    MemberRole,
    MetricSnapshot,
    Milestone,
    OutboundProspect,
    PillarAsset,
    PlannedAction,
    Post,
    Task,
    TaskEvent,
    TaskEventType,
    TaskKind,
    TaskStatus,
    UsageEvent,
    WinningPattern,
)
from configs.settings import get_settings
from core.agents.roles import ROLES
from core.content.scoring import content_score
from core.content.tracking import mock_metrics
from core.llm.base import BaseLLMClient
from core.trends.safety import angle_safety
from core.growth.experiments import design_variants, simulated_outcome
from core.growth.incrementality import measure_lift
from core.growth.learner import attribute_insights, learn_outcomes, learned_priors
from core.content.repurpose import create_repurpose_provider
from core.ingest.factory import create_import_provider
from core.privacy.factory import create_egress_gate
from core.growth.segments import discover_segments, score_segments
from core.growth.stats import create_stats_provider
from core.market.factory import create_market_provider
from core.media.clips import create_clip_provider
from core.media.video import create_video_provider
from core.outbound.base import enrich_waterfall
from core.outbound.factory import create_deliverability_guard, create_enrichment_waterfall
from core.outbound.mock import personalized_line
from core.paid.factory import create_budget_allocator, create_creative_scorer
from core.paid.optimizer import ChannelCurve, optimize_budget as _optimize_budget
from core.policy.gate import policy_issues
from core.workflows.campaign_instantiation import (
    assign_segment,
    instantiate_campaign,
    route_assignees,
    targeted_segments,
)
from core.workflows.task_runner import (
    TaskRunner,
    complete_task,
    default_client_for_provider,
    recompute_asset_checks,
    snapshot_version,
)


def _require_lead(actor: Member) -> None:
    if not (actor.kind == MemberKind.HUMAN and actor.role == MemberRole.LEAD):
        raise HTTPException(status_code=403, detail="This action requires the lead role.")


def _require_same_tenant(actor: Member, tenant_id: str) -> None:
    if actor.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Resource belongs to another tenant.")


def _get_campaign(session: Session, actor: Member, campaign_id: str) -> Campaign:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    _require_same_tenant(actor, campaign.tenant_id)
    return campaign


def _get_task(session: Session, actor: Member, task_id: str) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    _require_same_tenant(actor, task.tenant_id)
    return task


def _record_event(
    session: Session,
    task: Task,
    event_type: TaskEventType,
    *,
    actor_id: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    session.add(
        TaskEvent(
            tenant_id=task.tenant_id,
            task_id=task.id,
            actor_id=actor_id,
            type=event_type,
            payload=payload,
        )
    )


def record_episodic_note(session: Session, task: Task, *, kind: str, text: str) -> None:
    """Append to the campaign's episodic memory (lead decisions/feedback)."""
    session.add(
        EpisodicNote(
            tenant_id=task.tenant_id, campaign_id=task.campaign_id, kind=kind, text=text
        )
    )


def create_campaign(
    session: Session,
    actor: Member,
    *,
    name: str,
    brief: dict,
    template: str,
    event_name: Optional[str] = None,
    event_date: Optional[str] = None,
    review_assets: bool = False,
    with_visuals: bool = False,
) -> Campaign:
    _require_lead(actor)
    asset_mode = (
        ExecutionMode.AI_DRAFT_HUMAN_REVIEW if review_assets else ExecutionMode.AI_AUTO
    )
    return instantiate_campaign(
        session,
        tenant_id=actor.tenant_id,
        name=name,
        brief=brief,
        template=template,
        created_by=actor.id,
        event_name=event_name,
        event_date=event_date,
        asset_mode=asset_mode,
        with_visuals=with_visuals,
    )


def get_campaign_for_lead(session: Session, actor: Member, campaign_id: str) -> Campaign:
    """A lead-only, tenant-scoped campaign lookup (e.g. for refreshing trends)."""
    _require_lead(actor)
    return _get_campaign(session, actor, campaign_id)


def _brand_keywords(brand: Optional[BrandProfile]) -> list[str]:
    if brand is None:
        return []
    words = list(brand.approved_phrases or [])
    words += [w for w in (brand.voice or "").replace(",", " ").split() if len(w) > 3]
    return words


def _planning_task(session: Session, campaign_id: str) -> Optional[Task]:
    return session.exec(
        select(Task).where(
            Task.campaign_id == campaign_id, Task.kind == TaskKind.PLANNING
        )
    ).first()


def score_angles(session: Session, actor: Member, campaign_id: str) -> list[dict]:
    """The campaign's detected trend angles, each with a safety verdict + fit score —
    so the UI can gate the 'draft a rapid post' action on a safe, on-brand angle."""
    campaign = _get_campaign(session, actor, campaign_id)
    planning = _planning_task(session, campaign.id)
    angles = ((planning.output or {}).get("timely_angles") if planning else None) or []
    keywords = _brand_keywords(get_brand(session, actor))
    return [{"angle": a, **angle_safety(a, keywords)} for a in angles]


def create_trend_draft(
    session: Session, actor: Member, campaign_id: str, *, angle: str, channel: str
) -> Task:
    """Turn a safe trend angle into a near-term ASSET task in the plan, ALWAYS
    review-gated (a trend post never auto-ships), tagged with the hot topic."""
    _require_lead(actor)
    campaign = _get_campaign(session, actor, campaign_id)
    if not (angle or "").strip():
        raise HTTPException(status_code=400, detail="angle cannot be empty.")
    verdict = angle_safety(angle, _brand_keywords(get_brand(session, actor)))
    if not verdict["safe"]:
        raise HTTPException(status_code=409, detail=f"Blocked — {verdict['reason']}.")

    planning = _planning_task(session, campaign.id)
    routes = route_assignees(session, actor.tenant_id)
    segments = targeted_segments(session, actor.tenant_id, campaign.brief or {})
    last = max(
        (t.sequence for t in session.exec(
            select(Task).where(Task.campaign_id == campaign.id)
        ).all()),
        default=0,
    )
    task = Task(
        tenant_id=actor.tenant_id,
        campaign_id=campaign.id,
        kind=TaskKind.ASSET,
        title=f"{channel} rapid post — {angle[:40]}",
        execution_mode=ExecutionMode.AI_DRAFT_HUMAN_REVIEW,  # trend posts are never auto
        depends_on=[planning.id] if planning is not None else [],
        assignee_id=routes.get(TaskKind.ASSET.value),
        params={
            "channel": channel,
            "angle": angle,
            "provenance": "trend",
            **assign_segment(channel, segments),
        },
        due_date=campaign.event_date,
        phase="launch",
        sequence=last + 1,
    )
    session.add(task)
    _record_event(session, task, TaskEventType.CREATED, actor_id=actor.id, payload={"trend": angle})
    session.commit()
    session.refresh(task)
    return task


_DIRECT_CAMPAIGN_NAME = "Direct assignments"


def _direct_campaign(session: Session, actor: Member) -> Campaign:
    """The per-tenant inbox campaign that holds ad-hoc directive tasks (lazily created).
    It borrows the brand's name for product context so a directive draft isn't starved."""
    existing = session.exec(
        select(Campaign).where(
            Campaign.tenant_id == actor.tenant_id, Campaign.template == "direct"
        )
    ).first()
    if existing is not None:
        return existing
    campaign = Campaign(
        tenant_id=actor.tenant_id,
        name=_DIRECT_CAMPAIGN_NAME,
        template="direct",
        brief={"product_name": _DIRECT_CAMPAIGN_NAME},
        created_by=actor.id,
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


def _directive_task(
    session: Session, actor: Member, member: Member, *, title: Optional[str], body: str
) -> Task:
    """Spin a directive into a real tracked task in the tenant's Direct-assignments
    campaign, assigned to the member. AI → review-gated draft; human → human-only to do."""
    campaign = _direct_campaign(session, actor)
    last = max(
        (t.sequence for t in session.exec(
            select(Task).where(Task.campaign_id == campaign.id)
        ).all()),
        default=0,
    )
    is_ai = member.kind == MemberKind.AI
    task = Task(
        tenant_id=actor.tenant_id,
        campaign_id=campaign.id,
        kind=TaskKind.ASSET,
        title=title.strip() if (title or "").strip() else f"Directive — {body[:40]}",
        execution_mode=(
            ExecutionMode.AI_DRAFT_HUMAN_REVIEW if is_ai else ExecutionMode.HUMAN_ONLY
        ),
        assignee_id=member.id,
        params={"channel": "LinkedIn", "directive": body, "provenance": "directive"},
        phase="followup",
        sequence=last + 1,
    )
    session.add(task)
    _record_event(session, task, TaskEventType.CREATED, actor_id=actor.id, payload={"directive": True})
    session.commit()
    session.refresh(task)
    return task


def get_schedule(
    session: Session, actor: Member, campaign_id: str
) -> tuple[Campaign, list[Milestone], list[Task], list[str]]:
    campaign = _get_campaign(session, actor, campaign_id)
    milestones = list(
        session.exec(
            select(Milestone)
            .where(Milestone.campaign_id == campaign.id)
            .order_by(Milestone.date)
        ).all()
    )
    tasks = list(
        session.exec(
            select(Task)
            .where(Task.campaign_id == campaign.id)
            .order_by(Task.sequence)
        ).all()
    )
    planning = next((t for t in tasks if t.kind == TaskKind.PLANNING), None)
    angles: list[str] = []
    if planning is not None and planning.output:
        angles = planning.output.get("timely_angles") or []
    return campaign, milestones, tasks, angles


def get_todo(session: Session, actor: Member) -> list[tuple[str, Task]]:
    """Scheduled, not-done tasks by due date. The lead sees the team's; a member
    sees their own."""
    query = select(Task).where(
        Task.tenant_id == actor.tenant_id,
        Task.due_date.is_not(None),  # type: ignore[union-attr]
        Task.status != TaskStatus.DONE,
    )
    if not (actor.kind == MemberKind.HUMAN and actor.role == MemberRole.LEAD):
        query = query.where(Task.assignee_id == actor.id)
    tasks = sorted(session.exec(query).all(), key=lambda t: t.due_date or "")

    campaign_ids = list({t.campaign_id for t in tasks})
    names: dict[str, str] = {}
    if campaign_ids:
        names = {
            c.id: c.name
            for c in session.exec(
                select(Campaign).where(Campaign.id.in_(campaign_ids))  # type: ignore[attr-defined]
            ).all()
        }
    return [(names.get(t.campaign_id, ""), t) for t in tasks]


def list_tenant_members(session: Session, tenant_id: str) -> list[Member]:
    return list(
        session.exec(select(Member).where(Member.tenant_id == tenant_id)).all()
    )


def list_all_members(session: Session) -> list[Member]:
    """Dev bootstrap: every member so a stub UI can choose who to act as.

    Unauthenticated, like the X-Member-Id stub — remove with real auth.
    """
    return list(session.exec(select(Member)).all())


def agent_fleet(session: Session, actor: Member) -> list[dict]:
    """Per-AI-employee observability from the data already captured: LLM calls
    (UsageEvent), tasks owned, average content score, and self-correction passes.
    Productizes the cross-model audit into a fleet view the lead can watch."""
    members = session.exec(
        select(Member).where(
            Member.tenant_id == actor.tenant_id, Member.kind == MemberKind.AI
        )
    ).all()
    usage = session.exec(
        select(UsageEvent).where(UsageEvent.tenant_id == actor.tenant_id)
    ).all()
    tasks = session.exec(
        select(Task).where(Task.tenant_id == actor.tenant_id)
    ).all()
    corrections = session.exec(
        select(TaskEvent).where(
            TaskEvent.tenant_id == actor.tenant_id,
            TaskEvent.type == TaskEventType.SELF_CORRECTED,
        )
    ).all()
    runs_by = Counter(u.member_id for u in usage if u.member_id)
    corrections_by: Counter = Counter()
    for event in corrections:
        passes = (event.payload or {}).get("passes", 1) if event.payload else 1
        if event.actor_id:
            corrections_by[event.actor_id] += passes

    fleet: list[dict] = []
    for member in members:
        owned = [t for t in tasks if t.assignee_id == member.id]
        scores = [
            score["overall"]
            for t in owned
            if (score := content_score(t.checks)) is not None
        ]
        config = member.agent_config or {}
        fleet.append(
            {
                "member_id": member.id,
                "display_name": member.display_name,
                "role": config.get("role") or config.get("agent_kind") or "",
                "provider": config.get("provider", "mock"),
                "model": config.get("model"),
                "runs": runs_by.get(member.id, 0),
                "tasks_owned": len(owned),
                "avg_score": round(sum(scores) / len(scores)) if scores else None,
                "self_corrections": corrections_by.get(member.id, 0),
            }
        )
    fleet.sort(key=lambda row: row["runs"], reverse=True)
    return fleet


def _get_member(session: Session, actor: Member, member_id: str) -> Member:
    member = session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    _require_same_tenant(actor, member.tenant_id)
    return member


def member_profile(
    session: Session, actor: Member, member_id: str
) -> tuple[Member, Optional[dict], list[Task]]:
    """A member's profile: who they are, their fleet stat (AI), and their tasks."""
    member = _get_member(session, actor, member_id)
    stat = next(
        (f for f in agent_fleet(session, actor) if f["member_id"] == member.id), None
    )
    tasks = list(
        session.exec(
            select(Task)
            .where(Task.tenant_id == actor.tenant_id, Task.assignee_id == member.id)
            .order_by(Task.updated_at.desc())  # type: ignore[attr-defined]
        ).all()
    )
    return member, stat, tasks


def list_member_messages(
    session: Session, actor: Member, member_id: str
) -> list[DirectMessage]:
    _get_member(session, actor, member_id)
    return list(
        session.exec(
            select(DirectMessage)
            .where(DirectMessage.member_id == member_id)
            .order_by(DirectMessage.created_at)
        ).all()
    )


async def _agent_reply(
    member: Member,
    body: str,
    kind: str,
    title: Optional[str],
    client_for_provider,
) -> str:
    """The AI employee's in-role reply to the lead (real LLM, or a role-aware mock)."""
    config = member.agent_config or {}
    role_key = config.get("role", "")
    provider = config.get("provider", "mock")
    role_title = ROLES[role_key].title if role_key in ROLES else "your agent"
    if provider == "mock":
        if kind == "directive":
            return (
                f"On it — I'll take “{(title or body)[:48]}” as {member.display_name} "
                f"({role_title}) and come back with a draft for your review."
            )
        return (
            f"Thanks. As {member.display_name} I'd focus on {body[:60]}… "
            "Want me to draft something?"
        )
    client: BaseLLMClient = (client_for_provider or default_client_for_provider)(provider)
    job = ROLES[role_key].job_description if role_key in ROLES else ""
    system = (
        f"You are {member.display_name}, the team's {role_title}. {job} "
        "Reply concisely and helpfully to the marketing lead."
    )
    user = f"[Directive: {title}]\n{body}" if kind == "directive" else body
    return await client.generate_text(system_prompt=system, user_prompt=user)


async def send_member_message(
    session: Session,
    actor: Member,
    member_id: str,
    *,
    body: str,
    kind: str,
    title: Optional[str],
    client_for_provider=None,
) -> list[DirectMessage]:
    """Lead sends a message/directive to a member; AI members auto-reply in role."""
    _require_lead(actor)
    member = _get_member(session, actor, member_id)
    if not (body or "").strip():
        raise HTTPException(status_code=400, detail="message body cannot be empty.")
    if kind not in ("message", "directive"):
        raise HTTPException(status_code=400, detail="kind must be 'message' or 'directive'.")

    # A directive becomes a real, tracked task in the team's Direct-assignments campaign,
    # linked from the message so it shows in the thread and the cross-campaign queue.
    directive_task: Optional[Task] = None
    if kind == "directive":
        directive_task = _directive_task(
            session, actor, member, title=title, body=body.strip()
        )
    session.add(
        DirectMessage(
            tenant_id=actor.tenant_id, member_id=member_id, sender="lead",
            kind=kind, title=title, body=body.strip(),
            task_id=directive_task.id if directive_task is not None else None,
        )
    )
    if member.kind == MemberKind.AI:
        reply = await _agent_reply(member, body.strip(), kind, title, client_for_provider)
        session.add(
            DirectMessage(
                tenant_id=actor.tenant_id, member_id=member_id, sender="agent",
                kind="message", body=reply,
            )
        )
    session.commit()
    # An AI member drafts the directive task immediately so a real deliverable comes back
    # (review-gated). Runs the inbox campaign; only fresh TODO directive tasks are picked.
    if directive_task is not None and member.kind == MemberKind.AI:
        await TaskRunner(session, client_for_provider).run_ready_tasks(
            directive_task.campaign_id
        )
    return list_member_messages(session, actor, member_id)


# --- Org configuration (the per-tenant digital-employee roster) ---


def get_org(session: Session, actor: Member) -> list[Member]:
    """The actor's tenant roster, oldest first (so the org chart is stable)."""
    return list(
        session.exec(
            select(Member)
            .where(Member.tenant_id == actor.tenant_id)
            .order_by(Member.created_at)
        ).all()
    )


def _validate_org_inputs(
    session: Session,
    actor: Member,
    *,
    role: Optional[str],
    handles_kinds: Optional[list[str]],
    reports_to: Optional[str],
    member_id: Optional[str] = None,
) -> None:
    """Guard the org-config inputs so a bad config can't silently wedge routing."""
    if handles_kinds is not None:
        valid = {kind.value for kind in TaskKind}
        unknown = [kind for kind in handles_kinds if kind not in valid]
        if unknown:
            raise HTTPException(
                status_code=400, detail=f"Unknown task kinds: {unknown}."
            )
    if role is not None and role not in ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent role '{role}'. Available: {sorted(ROLES)}.",
        )
    if reports_to is not None:
        if member_id is not None and reports_to == member_id:
            raise HTTPException(status_code=400, detail="A member cannot report to itself.")
        manager = session.get(Member, reports_to)
        if manager is None or manager.tenant_id != actor.tenant_id:
            raise HTTPException(
                status_code=400, detail="reports_to must be a member of this tenant."
            )


def create_org_member(
    session: Session,
    actor: Member,
    *,
    display_name: str,
    role: str,
    job_description: str = "",
    handles_kinds: Optional[list[str]] = None,
    provider: str = "mock",
    model: Optional[str] = None,
    reports_to: Optional[str] = None,
) -> Member:
    """Add an AI digital employee to the actor's tenant (lead only)."""
    _require_lead(actor)
    _validate_org_inputs(
        session, actor, role=role, handles_kinds=handles_kinds, reports_to=reports_to
    )
    agent_config: dict = {"role": role, "provider": provider}
    if model:
        agent_config["model"] = model
    member = Member(
        tenant_id=actor.tenant_id,
        kind=MemberKind.AI,
        role=MemberRole.MEMBER,
        display_name=display_name,
        job_description=job_description,
        reports_to=reports_to,
        handles_kinds=handles_kinds or [],
        agent_config=agent_config,
    )
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


def update_org_member(
    session: Session,
    actor: Member,
    member_id: str,
    *,
    job_description: Optional[str] = None,
    handles_kinds: Optional[list[str]] = None,
    reports_to: Optional[str] = None,
    role: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Member:
    """Reconfigure a digital employee (lead only). Omitted fields are left as-is."""
    _require_lead(actor)
    member = session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    _require_same_tenant(actor, member.tenant_id)
    _validate_org_inputs(
        session, actor, role=role, handles_kinds=handles_kinds,
        reports_to=reports_to, member_id=member_id,
    )

    is_agent_change = role is not None or provider is not None or model is not None
    if is_agent_change and member.kind != MemberKind.AI:
        raise HTTPException(
            status_code=400, detail="role/provider/model only apply to AI members."
        )

    if job_description is not None:
        member.job_description = job_description
    if handles_kinds is not None:
        member.handles_kinds = handles_kinds
    if reports_to is not None:
        member.reports_to = reports_to
    if is_agent_change:
        config = dict(member.agent_config or {})
        if role is not None:
            config["role"] = role
        if provider is not None:
            config["provider"] = provider
        if model is not None:
            config["model"] = model
        member.agent_config = config  # reassign so the JSON column registers the change

    session.add(member)
    session.commit()
    session.refresh(member)
    return member


def list_campaigns(session: Session, actor: Member) -> list[Campaign]:
    """The actor's tenant campaigns, newest first."""
    return list(
        session.exec(
            select(Campaign)
            .where(Campaign.tenant_id == actor.tenant_id)
            .order_by(Campaign.created_at.desc())  # type: ignore[attr-defined]
        ).all()
    )


def get_board(
    session: Session, actor: Member, campaign_id: str
) -> tuple[Campaign, list[Task], list[Member]]:
    campaign = _get_campaign(session, actor, campaign_id)
    tasks = list(
        session.exec(
            select(Task)
            .where(Task.campaign_id == campaign.id)
            .order_by(Task.sequence)
        ).all()
    )
    members = list_tenant_members(session, campaign.tenant_id)
    return campaign, tasks, members


_INBOX_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.NEEDS_REVIEW)


def get_review_queue(session: Session, actor: Member) -> list[tuple[str, Task]]:
    """The cross-campaign "needs your call" queue (Workfront-style): for a lead, every
    needs-review task, open claim-check, or blocked task across ALL campaigns, each
    labelled with its campaign; for a member, their own awaiting-review tasks. A decision
    completes the task, so it leaves the queue."""
    is_lead = actor.kind == MemberKind.HUMAN and actor.role == MemberRole.LEAD
    query = select(Task).where(Task.tenant_id == actor.tenant_id)
    if is_lead:
        query = query.where(
            or_(
                Task.status == TaskStatus.NEEDS_REVIEW,
                Task.status == TaskStatus.BLOCKED,
                and_(Task.kind == TaskKind.CLAIM_CHECK, Task.status != TaskStatus.DONE),
            )
        )
    else:
        query = query.where(
            Task.assignee_id == actor.id, Task.status == TaskStatus.NEEDS_REVIEW
        )
    tasks = list(session.exec(query.order_by(Task.sequence)).all())
    campaign_ids = list({t.campaign_id for t in tasks})
    names: dict[str, str] = {}
    if campaign_ids:
        names = {
            c.id: c.name
            for c in session.exec(
                select(Campaign).where(Campaign.id.in_(campaign_ids))  # type: ignore[attr-defined]
            ).all()
        }
    items = [(names.get(t.campaign_id, "—"), t) for t in tasks]
    return sorted(items, key=lambda it: (it[0], it[1].sequence))


def get_inbox(session: Session, actor: Member) -> list[Task]:
    return list(
        session.exec(
            select(Task)
            .where(
                Task.tenant_id == actor.tenant_id,
                Task.assignee_id == actor.id,
                Task.status.in_(_INBOX_STATUSES),  # type: ignore[attr-defined]
            )
            .order_by(Task.sequence)
        ).all()
    )


def get_task_detail(
    session: Session, actor: Member, task_id: str
) -> tuple[Task, list[Comment], list[TaskEvent]]:
    task = _get_task(session, actor, task_id)
    comments = list(
        session.exec(
            select(Comment).where(Comment.task_id == task.id).order_by(Comment.created_at)
        ).all()
    )
    events = list(
        session.exec(
            select(TaskEvent)
            .where(TaskEvent.task_id == task.id)
            .order_by(TaskEvent.created_at)
        ).all()
    )
    return task, comments, events


def assign_task(
    session: Session,
    actor: Member,
    task_id: str,
    *,
    member_id: Optional[str],
    execution_mode: Optional[ExecutionMode],
) -> Task:
    _require_lead(actor)
    task = _get_task(session, actor, task_id)
    if member_id is None and execution_mode is None:
        raise HTTPException(status_code=400, detail="Provide member_id and/or execution_mode.")

    if member_id is not None:
        member = session.get(Member, member_id)
        if member is None or member.tenant_id != actor.tenant_id:
            raise HTTPException(status_code=400, detail="Unknown member for this tenant.")

    # Reject combinations that would wedge the task (an AI agent can never work a
    # human-only task, and the runner won't pick it up).
    final_assignee_id = member_id if member_id is not None else task.assignee_id
    final_mode = execution_mode if execution_mode is not None else task.execution_mode
    final_member = session.get(Member, final_assignee_id) if final_assignee_id else None
    if (
        final_member is not None
        and final_member.kind == MemberKind.AI
        and final_mode == ExecutionMode.HUMAN_ONLY
    ):
        raise HTTPException(
            status_code=400, detail="Cannot pair an AI agent with human-only execution."
        )

    if member_id is not None:
        task.assignee_id = member_id
    if execution_mode is not None:
        task.execution_mode = execution_mode
    task.updated_at = datetime.now(timezone.utc)
    _record_event(
        session, task, TaskEventType.ASSIGNED, actor_id=actor.id,
        payload={"member_id": member_id, "execution_mode": execution_mode},
    )
    session.add(task)
    session.commit()
    return task


def submit_task(
    session: Session, actor: Member, task_id: str, *, output: Optional[dict]
) -> Task:
    task = _get_task(session, actor, task_id)
    if actor.kind != MemberKind.HUMAN:
        raise HTTPException(status_code=403, detail="Only a human member can submit a task.")
    if task.assignee_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the assignee can submit this task.")
    if task.status not in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
        raise HTTPException(status_code=409, detail="Task is not in a submittable state.")
    if task.locked:
        raise HTTPException(status_code=409, detail="Content is locked; unlock to edit.")
    if output is not None:
        task.output = output
        snapshot_version(session, task, source="submit", member_id=actor.id)
    _record_event(session, task, TaskEventType.SUBMITTED, actor_id=actor.id)
    if task.execution_mode == ExecutionMode.HUMAN_ONLY:
        complete_task(session, task, actor_id=actor.id)
    else:
        task.status = TaskStatus.NEEDS_REVIEW
        session.add(task)
    session.commit()
    return task


def review_task(
    session: Session,
    actor: Member,
    task_id: str,
    *,
    action: str,
    output: Optional[dict],
    note: Optional[str],
) -> Task:
    _require_lead(actor)
    if action not in ("approve", "request_changes"):
        raise HTTPException(status_code=400, detail="Unknown review action.")
    task = _get_task(session, actor, task_id)
    if task.status != TaskStatus.NEEDS_REVIEW:
        raise HTTPException(status_code=409, detail="Task is not awaiting review.")
    if task.locked:
        raise HTTPException(status_code=409, detail="Content is locked; unlock to review.")

    if action == "approve":
        if output is not None:
            task.output = output
            snapshot_version(session, task, source="review_edit", member_id=actor.id)
            _record_event(session, task, TaskEventType.EDITED, actor_id=actor.id)
        complete_task(session, task, actor_id=actor.id)
    else:  # request_changes
        task.status = TaskStatus.IN_PROGRESS
        _record_event(
            session, task, TaskEventType.CHANGES_REQUESTED, actor_id=actor.id,
            payload={"note": note},
        )
        record_episodic_note(
            session, task, kind="feedback",
            text=f"Changes requested on '{task.title}': {note or 'see thread'}",
        )
        session.add(task)
    session.commit()
    return task


def edit_task(session: Session, actor: Member, task_id: str, *, output: dict) -> Task:
    """Modify a task's output at any stage. Asset checks are recomputed."""
    task = _get_task(session, actor, task_id)
    is_lead = actor.kind == MemberKind.HUMAN and actor.role == MemberRole.LEAD
    is_assignee = task.assignee_id == actor.id and actor.kind == MemberKind.HUMAN
    if not (is_lead or is_assignee):
        raise HTTPException(
            status_code=403, detail="Only the lead or the assignee can edit this task."
        )
    if task.locked:
        raise HTTPException(status_code=409, detail="Content is locked; unlock to edit.")
    task.output = output
    task.updated_at = datetime.now(timezone.utc)
    if task.kind == TaskKind.ASSET:
        task.checks = recompute_asset_checks(session, task)
    snapshot_version(session, task, source="edit", member_id=actor.id)
    _record_event(session, task, TaskEventType.EDITED, actor_id=actor.id)
    record_episodic_note(session, task, kind="feedback", text=f"Lead edited '{task.title}'.")
    session.add(task)
    session.commit()
    return task


def guard_post_edit(session: Session, actor: Member, task_id: str) -> Task:
    """Permission gate for AI re-renders on a post (sync-visual / improve): the lead or
    the human assignee, the task is a post, and it isn't locked."""
    task = _get_task(session, actor, task_id)
    is_lead = actor.kind == MemberKind.HUMAN and actor.role == MemberRole.LEAD
    is_assignee = task.assignee_id == actor.id and actor.kind == MemberKind.HUMAN
    if not (is_lead or is_assignee):
        raise HTTPException(status_code=403, detail="Only the lead or the assignee can do this.")
    if task.locked:
        raise HTTPException(status_code=409, detail="Content is locked; unlock first.")
    if task.kind != TaskKind.ASSET:
        raise HTTPException(status_code=400, detail="Only posts support this action.")
    return task


def lock_task(session: Session, actor: Member, task_id: str, *, locked: bool) -> Task:
    """Lead sign-off: lock (or unlock) a task's content. While locked, edits/submits
    are rejected, and the approved version is pinned."""
    _require_lead(actor)
    task = _get_task(session, actor, task_id)
    task.locked = locked
    if locked:
        latest = session.exec(
            select(ContentVersion)
            .where(ContentVersion.task_id == task.id)
            .order_by(ContentVersion.number.desc())  # type: ignore[attr-defined]
        ).first()
        task.locked_version_id = latest.id if latest is not None else None
    else:
        task.locked_version_id = None
    _record_event(
        session, task, TaskEventType.STATUS_CHANGED, actor_id=actor.id,
        payload={"locked": locked},
    )
    session.add(task)
    session.commit()
    return task


def list_versions(session: Session, actor: Member, task_id: str) -> list[ContentVersion]:
    task = _get_task(session, actor, task_id)
    return list(
        session.exec(
            select(ContentVersion)
            .where(ContentVersion.task_id == task.id)
            .order_by(ContentVersion.number)
        ).all()
    )


def list_annotations(session: Session, actor: Member, task_id: str) -> list[Annotation]:
    task = _get_task(session, actor, task_id)
    return list(
        session.exec(
            select(Annotation)
            .where(Annotation.task_id == task.id)
            .order_by(Annotation.created_at)
        ).all()
    )


def create_annotation(
    session: Session,
    actor: Member,
    task_id: str,
    *,
    body: str,
    target: str,
    anchor: dict,
) -> Annotation:
    task = _get_task(session, actor, task_id)
    if not (body or "").strip():
        raise HTTPException(status_code=400, detail="annotation body cannot be empty.")
    row = Annotation(
        tenant_id=task.tenant_id,
        task_id=task.id,
        author_id=actor.id,
        target=target or "general",
        anchor=anchor or {},
        body=body.strip(),
    )
    session.add(row)
    _record_event(session, task, TaskEventType.COMMENTED, actor_id=actor.id)
    session.commit()
    session.refresh(row)
    return row


def resolve_annotation(
    session: Session, actor: Member, annotation_id: str, *, resolved: bool
) -> Annotation:
    row = session.get(Annotation, annotation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    _require_same_tenant(actor, row.tenant_id)
    row.resolved = resolved
    row.resolved_by = actor.id if resolved else None
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def available_actions(actor: Member, task: Task) -> list[str]:
    """Intervention affordances for this actor on this task, for a friendly UI."""
    actions = ["comment", "annotate"]
    is_lead = actor.kind == MemberKind.HUMAN and actor.role == MemberRole.LEAD
    is_assignee = task.assignee_id == actor.id and actor.kind == MemberKind.HUMAN
    if (is_lead or is_assignee) and not task.locked:
        actions.append("edit")
    if is_lead:
        actions.append("assign")
        actions.append("unlock" if task.locked else "lock")
    if is_lead and task.status == TaskStatus.NEEDS_REVIEW:
        actions.append("review")
    if is_assignee and task.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
        actions.append("submit")
    return actions


def add_comment(session: Session, actor: Member, task_id: str, *, body: str) -> Comment:
    task = _get_task(session, actor, task_id)
    comment = Comment(
        tenant_id=task.tenant_id, task_id=task.id, author_id=actor.id, body=body
    )
    session.add(comment)
    _record_event(session, task, TaskEventType.COMMENTED, actor_id=actor.id)
    session.commit()
    return comment


def get_brand(session: Session, actor: Member) -> Optional[BrandProfile]:
    """The tenant's brand profile (voice, proof points, ICP segments) — the fact-check
    reference + audience library. Readable by any member."""
    return session.exec(
        select(BrandProfile).where(BrandProfile.tenant_id == actor.tenant_id)
    ).first()


def upsert_segment(
    session: Session,
    actor: Member,
    *,
    name: str,
    description: str,
    profile: str,
    platforms: list[str],
    pain_points: list[str],
    value_props: list[str],
    objections: list[str],
    reach_tactics: list[str],
) -> BrandProfile:
    """Add or replace (by name) an ICP segment on the tenant's brand (lead only)."""
    _require_lead(actor)
    if not (name or "").strip():
        raise HTTPException(status_code=400, detail="segment name cannot be empty.")
    brand = get_brand(session, actor)
    if brand is None:
        brand = BrandProfile(tenant_id=actor.tenant_id)
        session.add(brand)
    segments = [s for s in (brand.segments or []) if s.get("name") != name.strip()]
    segments.append(
        {
            "name": name.strip(),
            "description": description or "",
            "profile": profile or "",
            "platforms": platforms or [],
            "pain_points": pain_points or [],
            "value_props": value_props or [],
            "objections": objections or [],
            "reach_tactics": reach_tactics or [],
        }
    )
    brand.segments = segments  # reassign so the JSON column registers the change
    session.add(brand)
    session.commit()
    session.refresh(brand)
    return brand


def delete_segment(session: Session, actor: Member, name: str) -> BrandProfile:
    _require_lead(actor)
    brand = get_brand(session, actor)
    if brand is None:
        raise HTTPException(status_code=404, detail="No brand profile.")
    brand.segments = [s for s in (brand.segments or []) if s.get("name") != name]
    session.add(brand)
    session.commit()
    session.refresh(brand)
    return brand


_TERM_TYPES = ("approved", "avoid", "use_carefully")


def list_terms(session: Session, actor: Member) -> list[BrandTerm]:
    return list(
        session.exec(
            select(BrandTerm)
            .where(BrandTerm.tenant_id == actor.tenant_id)
            .order_by(BrandTerm.term)
        ).all()
    )


def create_term(
    session: Session,
    actor: Member,
    *,
    term: str,
    term_type: str,
    replacement: Optional[str],
    case_sensitive: bool,
    note: str,
) -> BrandTerm:
    _require_lead(actor)
    if term_type not in _TERM_TYPES:
        raise HTTPException(status_code=400, detail=f"term_type must be one of {_TERM_TYPES}.")
    if not (term or "").strip():
        raise HTTPException(status_code=400, detail="term cannot be empty.")
    row = BrandTerm(
        tenant_id=actor.tenant_id,
        term=term.strip(),
        term_type=term_type,
        replacement=(replacement or "").strip() or None,
        case_sensitive=case_sensitive,
        note=note or "",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_term(session: Session, actor: Member, term_id: str) -> None:
    _require_lead(actor)
    row = session.get(BrandTerm, term_id)
    if row is None or row.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Term not found.")
    session.delete(row)
    session.commit()


def list_atoms(
    session: Session,
    actor: Member,
    *,
    kind: Optional[str] = None,
    tag: Optional[str] = None,
) -> list[ContentAtom]:
    """Reusable content atoms for the actor's tenant, filtered by kind/tag."""
    query = select(ContentAtom).where(ContentAtom.tenant_id == actor.tenant_id)
    if kind:
        query = query.where(ContentAtom.kind == kind)
    atoms = list(session.exec(query.order_by(ContentAtom.created_at)).all())
    if tag:
        atoms = [atom for atom in atoms if tag in (atom.tags or [])]
    return atoms


def campaign_performance(
    session: Session, actor: Member, campaign_id: str
) -> tuple[Campaign, list[dict], dict]:
    """Performance grouped by platform; each platform lists its published posts.

    Metrics use the latest stored MetricSnapshot for a post, else deterministic
    mock metrics so the view is demoable before a real source is connected.
    """
    campaign = _get_campaign(session, actor, campaign_id)
    posts = list(
        session.exec(
            select(Post)
            .where(Post.campaign_id == campaign.id)
            .order_by(Post.platform, Post.published_at)
        ).all()
    )
    asset_titles = {
        t.id: t.title
        for t in session.exec(
            select(Task).where(
                Task.campaign_id == campaign.id, Task.kind == TaskKind.ASSET
            )
        ).all()
    }

    platforms: dict[str, dict] = {}
    totals = {"impressions": 0, "clicks": 0, "signups": 0}
    for post in posts:
        snapshot = session.exec(
            select(MetricSnapshot)
            .where(MetricSnapshot.post_id == post.id)
            .order_by(MetricSnapshot.captured_at.desc())  # type: ignore[attr-defined]
        ).first()
        if snapshot is not None:
            metrics = {
                "impressions": snapshot.impressions,
                "clicks": snapshot.clicks,
                "signups": snapshot.signups,
                "source": snapshot.source,
            }
        else:
            metrics = mock_metrics(post.id)
        group = platforms.setdefault(
            post.platform,
            {
                "platform": post.platform,
                "impressions": 0,
                "clicks": 0,
                "signups": 0,
                "posts": [],
            },
        )
        group["posts"].append(
            {
                "post_id": post.id,
                "title": asset_titles.get(post.asset_task_id, "Post"),
                "url": post.url,
                "published_at": post.published_at,
                "publish_status": post.publish_status,
                "permalink": post.permalink,
                **metrics,
            }
        )
        for key in ("impressions", "clicks", "signups"):
            group[key] += metrics[key]
            totals[key] += metrics[key]
    return campaign, list(platforms.values()), totals


def record_metrics(
    session: Session,
    actor: Member,
    post_id: str,
    *,
    impressions: int,
    clicks: int,
    signups: int,
) -> MetricSnapshot:
    """Manually record a performance snapshot for a post (lead only)."""
    _require_lead(actor)
    post = session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found.")
    _require_same_tenant(actor, post.tenant_id)
    snapshot = MetricSnapshot(
        tenant_id=post.tenant_id,
        campaign_id=post.campaign_id,
        post_id=post.id,
        source="manual",
        impressions=impressions,
        clicks=clicks,
        signups=signups,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def get_growth_insights(session: Session, actor: Member) -> dict:
    """The learned 'what's working' scoreboard + priors — the effect flywheel made
    visible to the lead (the same priors the agents now generate from)."""
    _require_lead(actor)
    return {
        "attributes": attribute_insights(session, actor.tenant_id),
        "priors": learned_priors(session, actor.tenant_id),
    }


def relearn_outcomes(session: Session, actor: Member) -> dict:
    """Rebuild the attribute posteriors from current post outcomes, then return them."""
    _require_lead(actor)
    learn_outcomes(session, actor.tenant_id)
    return get_growth_insights(session, actor)


def run_incrementality(session: Session, actor: Member) -> dict:
    """Phase 11 — measure causal lift per attribute (mock GeoHoldout), store the de-bias
    multipliers, and re-learn so the flywheel reflects CAUSATION not just correlation. A
    high-converting attribute with low incrementality is shrunk toward baseline. Lead only."""
    _require_lead(actor)
    for t in session.exec(
        select(IncrementalityTest).where(IncrementalityTest.tenant_id == actor.tenant_id)
    ).all():
        session.delete(t)
    session.commit()
    learn_outcomes(session, actor.tenant_id)  # naive baseline (no multipliers)
    naive_rows = session.exec(
        select(AttributeOutcome).where(
            AttributeOutcome.tenant_id == actor.tenant_id,
            AttributeOutcome.channel == "",
            AttributeOutcome.segment == "",
        )
    ).all()
    results = []
    for r in naive_rows:
        readout = measure_lift(r.attribute_value, r.conversions)
        session.add(
            IncrementalityTest(
                tenant_id=actor.tenant_id, attribute_type=r.attribute_type,
                attribute_value=r.attribute_value, naive_conversions=r.conversions,
                incremental_conversions=readout["incremental_conversions"],
                multiplier=readout["multiplier"], lift_pct=readout["lift_pct"],
            )
        )
        results.append(
            {
                "attribute_type": r.attribute_type, "attribute_value": r.attribute_value,
                "naive_conversions": r.conversions,
                "incremental_conversions": readout["incremental_conversions"],
                "multiplier": readout["multiplier"], "lift_pct": readout["lift_pct"],
            }
        )
    session.commit()
    learn_outcomes(session, actor.tenant_id)  # de-biased re-learn
    results.sort(key=lambda x: x["multiplier"])  # most over-claimed first
    return {"tests": results, "insights": get_growth_insights(session, actor)}


# --- Phase 14: the autonomous orchestrator (observe → decide → propose) ---


def _planned_dict(a: PlannedAction) -> dict:
    return {
        "id": a.id, "type": a.type, "title": a.title, "rationale": a.rationale,
        "priority": a.priority, "autonomy_level": a.autonomy_level, "status": a.status,
    }


def list_planned_actions(session: Session, actor: Member) -> list[dict]:
    _require_lead(actor)
    rows = session.exec(
        select(PlannedAction)
        .where(
            PlannedAction.tenant_id == actor.tenant_id,
            PlannedAction.status == "proposed",
        )
        .order_by(PlannedAction.priority.desc())  # type: ignore[attr-defined]
    ).all()
    return [_planned_dict(a) for a in rows]


def plan_actions(session: Session, actor: Member) -> list[dict]:
    """The orchestrator's observe→decide: read the current state across capabilities and
    emit a ranked queue of proposed next actions. Each maps to an existing capability —
    the brain selects + sequences, it doesn't invent."""
    _require_lead(actor)
    for a in session.exec(
        select(PlannedAction).where(
            PlannedAction.tenant_id == actor.tenant_id,
            PlannedAction.status == "proposed",
        )
    ).all():
        session.delete(a)

    proposals: list[tuple] = []  # (type, title, rationale, priority, payload)
    insights = get_growth_insights(session, actor)
    if not insights["attributes"]:
        proposals.append((
            "import_history", "Warm-start from historical data",
            "No outcome data yet — import past content so the flywheel isn't cold-starting.",
            95, {},
        ))
    else:
        has_test = session.exec(
            select(IncrementalityTest).where(IncrementalityTest.tenant_id == actor.tenant_id)
        ).first() is not None
        if not has_test:
            proposals.append((
                "run_incrementality", "De-bias the flywheel (measure causal lift)",
                "The flywheel learned priors but never measured causal lift — it may be "
                "amplifying correlation, not causation.",
                90, {},
            ))

    scorecard = get_segment_scorecard(session, actor)
    unproven = next((s for s in scorecard["segments"] if s["status"] == "unproven"), None)
    if unproven:
        proposals.append((
            "validate_segment", f"Validate the '{unproven['segment']}' segment",
            f"'{unproven['segment']}' is unproven (n={unproven['n_posts']}) — run content "
            "to test the hypothesis.",
            70, {"segment": unproven["segment"]},
        ))

    intel = get_market_intel(session, actor)
    if intel["whitespace"]:
        proposals.append((
            "draft_whitespace", "Address a market whitespace", intel["whitespace"][0],
            60, {"angle": intel["whitespace"][0]},
        ))

    weak = next(
        (r for r in reliability_scorecard(session, actor)
         if r["recommended_mode"] == "human_only" and r["runs"] >= 3),
        None,
    )
    if weak:
        proposals.append((
            "review_autonomy", f"Review {weak['display_name']}'s autonomy",
            f"Reliability {weak['reliability']} — recommend keeping on human review.",
            40, {},
        ))

    for typ, title, rationale, prio, payload in proposals:
        session.add(
            PlannedAction(
                tenant_id=actor.tenant_id, type=typ, title=title, rationale=rationale,
                priority=prio, payload=payload,
            )
        )
    session.commit()
    return list_planned_actions(session, actor)


def _get_planned_action(session: Session, actor: Member, action_id: str) -> PlannedAction:
    a = session.get(PlannedAction, action_id)
    if a is None or a.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Action not found.")
    return a


def accept_action(session: Session, actor: Member, action_id: str) -> list[dict]:
    """Accept a proposal: auto-run the safe ones (causal de-bias), mark the rest accepted
    (the human acts in the matching tab)."""
    _require_lead(actor)
    a = _get_planned_action(session, actor, action_id)
    if a.type == "run_incrementality":
        run_incrementality(session, actor)
    a.status = "accepted"
    session.add(a)
    session.commit()
    return list_planned_actions(session, actor)


def ignore_action(session: Session, actor: Member, action_id: str) -> list[dict]:
    _require_lead(actor)
    a = _get_planned_action(session, actor, action_id)
    a.status = "ignored"
    session.add(a)
    session.commit()
    return list_planned_actions(session, actor)


# --- Phase 5b: the experiment ledger (variants → stats → winning patterns) ---


def _experiment_dict(session: Session, exp: Experiment) -> dict:
    variants = list(
        session.exec(
            select(ExperimentVariant).where(ExperimentVariant.experiment_id == exp.id)
        ).all()
    )
    return {
        "id": exp.id,
        "hypothesis": exp.hypothesis,
        "channel": exp.channel,
        "segment": exp.segment,
        "status": exp.status,
        "variants": [
            {
                "key": v.key,
                "attributes": v.attributes,
                "rationale": v.rationale,
                "impressions": v.impressions,
                "conversions": v.conversions,
                "cvr": round(v.conversions / v.impressions * 100, 2) if v.impressions else 0.0,
                "chance_to_beat_control": round(v.chance_to_beat_control, 3),
                "result_status": v.result_status,
            }
            for v in sorted(variants, key=lambda x: x.key)
        ],
    }


def list_experiments(session: Session, actor: Member, campaign_id: str) -> list[dict]:
    campaign = _get_campaign(session, actor, campaign_id)
    exps = list(
        session.exec(
            select(Experiment)
            .where(Experiment.campaign_id == campaign.id)
            .order_by(Experiment.created_at.desc())  # type: ignore[attr-defined]
        ).all()
    )
    return [_experiment_dict(session, e) for e in exps]


def design_experiment(
    session: Session,
    actor: Member,
    campaign_id: str,
    *,
    hypothesis: str,
    channel: str = "",
    segment: str = "",
    n: int = 3,
) -> dict:
    """Design N attribute-tagged variants of one brief (the ExperimentDesigner step)."""
    _require_lead(actor)
    campaign = _get_campaign(session, actor, campaign_id)
    if not (hypothesis or "").strip():
        raise HTTPException(status_code=400, detail="hypothesis cannot be empty.")
    exp = Experiment(
        tenant_id=actor.tenant_id, campaign_id=campaign.id,
        hypothesis=hypothesis.strip(), channel=channel, segment=segment,
    )
    session.add(exp)
    session.commit()
    session.refresh(exp)
    for spec in design_variants(hypothesis, n):
        session.add(
            ExperimentVariant(
                tenant_id=actor.tenant_id, experiment_id=exp.id, key=spec["key"],
                attributes=spec["attributes"], content=spec["content"],
                rationale=spec["rationale"],
                result_status="control" if spec["key"] == "control" else "untested",
            )
        )
    session.commit()
    return _experiment_dict(session, exp)


def decide_experiment(session: Session, actor: Member, experiment_id: str) -> dict:
    """Score variants against control (Bayesian chance-to-beat), mark the winner, and
    promote winning attribute combos to WinningPatterns. Auto-simulates mock metrics if
    none are recorded yet (a demo affordance — real metrics arrive via GA4 sync)."""
    _require_lead(actor)
    exp = session.get(Experiment, experiment_id)
    if exp is None or exp.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    variants = list(
        session.exec(
            select(ExperimentVariant).where(ExperimentVariant.experiment_id == exp.id)
        ).all()
    )
    control = next((v for v in variants if v.key == "control"), variants[0] if variants else None)
    if control is None:
        raise HTTPException(status_code=409, detail="Experiment has no variants.")

    if all(v.impressions == 0 for v in variants):  # demo: fabricate a mock market
        for v in variants:
            v.impressions, v.conversions = simulated_outcome(v.attributes)

    stats = create_stats_provider(exp.stats_method)
    for v in variants:
        if v.key == "control":
            v.result_status, v.chance_to_beat_control = "control", 0.0
        else:
            ctbc = stats.chance_to_beat_control(control, v)
            v.chance_to_beat_control = ctbc
            v.result_status = (
                "winner" if ctbc >= 0.95 else "loser" if ctbc <= 0.05 else "inconclusive"
            )
        session.add(v)

    control_cvr = control.conversions / max(1, control.impressions)
    for v in variants:
        if v.result_status == "winner":
            v_cvr = v.conversions / max(1, v.impressions)
            lift = (v_cvr / control_cvr - 1.0) if control_cvr > 0 else 0.0
            session.add(
                WinningPattern(
                    tenant_id=actor.tenant_id, attributes=v.attributes,
                    channel=exp.channel, segment=exp.segment, lift=lift,
                    confidence=v.chance_to_beat_control, evidence_experiment_id=exp.id,
                )
            )
    exp.status = "decided"
    exp.decided_at = datetime.now(timezone.utc)
    session.add(exp)
    session.commit()
    return _experiment_dict(session, exp)


# --- Phase 6: ICP validation/discovery + market intelligence ---


def get_segment_scorecard(session: Session, actor: Member) -> dict:
    """Each ICP segment's validation status (0–100 + status + attribute drivers) + the
    pending discovery candidates — ICP as a tested result, not a static assumption."""
    _require_lead(actor)
    brand = get_brand(session, actor)
    names = [s.get("name", "") for s in (brand.segments if brand else [])]
    candidates = session.exec(
        select(DiscoveredSegmentCandidate).where(
            DiscoveredSegmentCandidate.tenant_id == actor.tenant_id,
            DiscoveredSegmentCandidate.status == "pending",
        )
    ).all()
    return {
        "segments": score_segments(session, actor.tenant_id, names),
        "candidates": [
            {"id": c.id, "name": c.name, "rationale": c.rationale, "evidence": c.evidence}
            for c in candidates
        ],
    }


def discover_segment_candidates(session: Session, actor: Member) -> dict:
    """Surface high-converting sub-clusters as candidate segments (mock clustering)."""
    _require_lead(actor)
    brand = get_brand(session, actor)
    names = [s.get("name", "") for s in (brand.segments if brand else [])]
    seen = {
        c.name
        for c in session.exec(
            select(DiscoveredSegmentCandidate).where(
                DiscoveredSegmentCandidate.tenant_id == actor.tenant_id
            )
        ).all()
    }
    for found in discover_segments(session, actor.tenant_id, names + list(seen)):
        session.add(
            DiscoveredSegmentCandidate(
                tenant_id=actor.tenant_id, name=found["name"],
                rationale=found["rationale"], evidence=found["evidence"],
            )
        )
    session.commit()
    return get_segment_scorecard(session, actor)


def _get_candidate(
    session: Session, actor: Member, candidate_id: str
) -> DiscoveredSegmentCandidate:
    cand = session.get(DiscoveredSegmentCandidate, candidate_id)
    if cand is None or cand.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return cand


def promote_segment_candidate(
    session: Session, actor: Member, candidate_id: str
) -> dict:
    """Promote a discovered candidate into a tracked ICP segment on the brand."""
    _require_lead(actor)
    cand = _get_candidate(session, actor, candidate_id)
    upsert_segment(
        session, actor, name=cand.name, description=cand.rationale, profile="",
        platforms=[], pain_points=[], value_props=[], objections=[], reach_tactics=[],
    )
    cand.status = "promoted"
    session.add(cand)
    session.commit()
    return get_segment_scorecard(session, actor)


def dismiss_segment_candidate(
    session: Session, actor: Member, candidate_id: str
) -> dict:
    _require_lead(actor)
    cand = _get_candidate(session, actor, candidate_id)
    cand.status = "dismissed"
    session.add(cand)
    session.commit()
    return get_segment_scorecard(session, actor)


def get_market_intel(session: Session, actor: Member) -> dict:
    """Competitor positioning, share of voice, audience questions, and whitespace — the
    market context a brief should never be written without (mock provider)."""
    brand = get_brand(session, actor)
    intel = create_market_provider().intel(brand_keywords=_brand_keywords(brand))
    return {
        "competitors": [
            {"name": c.name, "positioning": c.positioning, "recent_change": c.recent_change}
            for c in intel.competitors
        ],
        "audience_questions": intel.audience_questions,
        "share_of_voice": intel.share_of_voice,
        "whitespace": intel.whitespace,
    }


async def spawn_whitespace_task(
    session: Session, actor: Member, *, angle: str, client_for_provider=None
) -> dict:
    """Turn a market-whitespace angle into a tracked, AI-drafted task (reuses the
    directive→task machinery), landing in the cross-campaign review queue."""
    _require_lead(actor)
    if not (angle or "").strip():
        raise HTTPException(status_code=400, detail="angle cannot be empty.")
    routes = route_assignees(session, actor.tenant_id)
    writer_id = routes.get(TaskKind.ASSET.value)
    writer = session.get(Member, writer_id) if writer_id else None
    if writer is None:
        raise HTTPException(status_code=409, detail="No writer configured for asset work.")
    task = _directive_task(
        session, actor, writer,
        title=f"Whitespace: {angle.strip()[:40]}", body=angle.strip(),
    )
    if writer.kind == MemberKind.AI:
        await TaskRunner(session, client_for_provider).run_ready_tasks(task.campaign_id)
    return {"task_id": task.id}


# --- Phase 7: brand narrative, funnel coverage, content atomization ---

_FUNNEL_STAGES = ("TOFU", "MOFU", "BOFU")
_FUNNEL_ACTION = {
    "TOFU": "build awareness — earn a click/follow",
    "MOFU": "earn consideration — drive a signup/trial",
    "BOFU": "drive conversion — get a paid start",
}


def get_brand_narrative(session: Session, actor: Member) -> dict:
    brand = get_brand(session, actor)
    return {
        "value_proposition": brand.value_proposition if brand else "",
        "messaging_pillars": brand.messaging_pillars if brand else [],
    }


def set_brand_narrative(
    session: Session, actor: Member, *, value_proposition: str, messaging_pillars: list[dict]
) -> dict:
    """The persistent messaging pyramid above any one campaign (lead only)."""
    _require_lead(actor)
    brand = get_brand(session, actor)
    if brand is None:
        brand = BrandProfile(tenant_id=actor.tenant_id)
        session.add(brand)
    brand.value_proposition = value_proposition or ""
    brand.messaging_pillars = messaging_pillars or []
    session.add(brand)
    session.commit()
    return get_brand_narrative(session, actor)


def funnel_coverage(session: Session, actor: Member, campaign_id: str) -> dict:
    """A funnel × segment matrix of asset counts; empty cells are coverage gaps."""
    campaign = _get_campaign(session, actor, campaign_id)
    tasks = list(
        session.exec(
            select(Task).where(
                Task.campaign_id == campaign.id, Task.kind == TaskKind.ASSET
            )
        ).all()
    )
    segments = sorted(
        {(t.params or {}).get("segment", "") or "(untargeted)" for t in tasks}
    ) or ["(untargeted)"]
    matrix = {st: {sg: 0 for sg in segments} for st in _FUNNEL_STAGES}
    for t in tasks:
        st = (t.params or {}).get("funnel_stage", "")
        sg = (t.params or {}).get("segment", "") or "(untargeted)"
        if st in matrix and sg in matrix[st]:
            matrix[st][sg] += 1
    gaps = [
        {"funnel_stage": st, "segment": sg}
        for st in _FUNNEL_STAGES
        for sg in segments
        if matrix[st][sg] == 0
    ]
    return {
        "stages": list(_FUNNEL_STAGES),
        "segments": segments,
        "matrix": matrix,
        "gaps": gaps,
    }


async def draft_for_gap(
    session: Session,
    actor: Member,
    campaign_id: str,
    *,
    funnel_stage: str,
    segment: str,
    client_for_provider=None,
) -> dict:
    """Fill a funnel×segment coverage gap with a new AI-drafted asset task."""
    _require_lead(actor)
    campaign = _get_campaign(session, actor, campaign_id)
    planning = _planning_task(session, campaign.id)
    routes = route_assignees(session, actor.tenant_id)
    brand = get_brand(session, actor)
    seg_obj = next(
        (s for s in (brand.segments if brand else []) if s.get("name") == segment), {}
    )
    channel = (seg_obj.get("platforms") or ["LinkedIn"])[0]
    last = max(
        (t.sequence for t in session.exec(
            select(Task).where(Task.campaign_id == campaign.id)
        ).all()),
        default=0,
    )
    task = Task(
        tenant_id=actor.tenant_id, campaign_id=campaign.id, kind=TaskKind.ASSET,
        title=f"{funnel_stage} · {segment} post",
        execution_mode=ExecutionMode.AI_DRAFT_HUMAN_REVIEW,
        depends_on=[planning.id] if planning is not None else [],
        assignee_id=routes.get(TaskKind.ASSET.value),
        params={
            "channel": channel, "funnel_stage": funnel_stage,
            "desired_action": _FUNNEL_ACTION.get(funnel_stage, ""),
            "segment": segment, "pain_point": (seg_obj.get("pain_points") or [""])[0],
        },
        phase="followup", sequence=last + 1,
    )
    session.add(task)
    _record_event(session, task, TaskEventType.CREATED, actor_id=actor.id, payload={"gap": True})
    session.commit()
    await TaskRunner(session, client_for_provider).run_ready_tasks(campaign.id)
    return funnel_coverage(session, actor, campaign_id)


def list_pillars(session: Session, actor: Member, campaign_id: str) -> list[dict]:
    campaign = _get_campaign(session, actor, campaign_id)
    pillars = list(
        session.exec(
            select(PillarAsset).where(PillarAsset.campaign_id == campaign.id)
        ).all()
    )
    return [
        {
            "id": p.id, "title": p.title, "kind": p.kind,
            "derivatives": len(
                session.exec(select(Task).where(Task.pillar_id == p.id)).all()
            ),
        }
        for p in pillars
    ]


def create_pillar(
    session: Session, actor: Member, campaign_id: str, *, title: str, kind: str, source_text: str
) -> dict:
    _require_lead(actor)
    campaign = _get_campaign(session, actor, campaign_id)
    if not (title or "").strip():
        raise HTTPException(status_code=400, detail="pillar title cannot be empty.")
    pillar = PillarAsset(
        tenant_id=actor.tenant_id, campaign_id=campaign.id,
        title=title.strip(), kind=kind or "doc", source_text=source_text or "",
    )
    session.add(pillar)
    session.commit()
    return {"created": pillar.id, "pillars": list_pillars(session, actor, campaign_id)}


async def atomize_pillar(
    session: Session, actor: Member, pillar_id: str, *, channels: list[str], client_for_provider=None
) -> dict:
    """Atomize one pillar into channel derivatives — a hub-and-spoke fan-out where each
    spoke carries pillar_id back to the hub and a rotating funnel stage."""
    _require_lead(actor)
    pillar = session.get(PillarAsset, pillar_id)
    if pillar is None or pillar.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Pillar not found.")
    planning = _planning_task(session, pillar.campaign_id)
    routes = route_assignees(session, actor.tenant_id)
    derivs = create_repurpose_provider().atomize(
        pillar_title=pillar.title, source_text=pillar.source_text,
        channels=channels or ["LinkedIn", "Email", "X / Twitter"],
    )
    last = max(
        (t.sequence for t in session.exec(
            select(Task).where(Task.campaign_id == pillar.campaign_id)
        ).all()),
        default=0,
    )
    for d in derivs:
        last += 1
        session.add(
            Task(
                tenant_id=actor.tenant_id, campaign_id=pillar.campaign_id,
                kind=TaskKind.ASSET, title=d.title,
                execution_mode=ExecutionMode.AI_DRAFT_HUMAN_REVIEW,
                depends_on=[planning.id] if planning is not None else [],
                assignee_id=routes.get(TaskKind.ASSET.value),
                params={
                    "channel": d.channel, "funnel_stage": d.funnel_stage,
                    "desired_action": _FUNNEL_ACTION.get(d.funnel_stage, ""),
                    "provenance": "repurpose",
                },
                pillar_id=pillar.id, phase="followup", sequence=last,
            )
        )
    session.commit()
    await TaskRunner(session, client_for_provider).run_ready_tasks(pillar.campaign_id)
    return {"pillar_id": pillar.id, "derivatives": len(derivs)}


# --- Phase 8: short-video generation + long-to-short clips ---


async def attach_video(
    session: Session, actor: Member, task: Task, *, video_provider: str = "mock"
) -> Task:
    """Script a post into a VideoSpec and render it (mock), attaching the result to the
    post's visual — copy + image + video as one deliverable. Caller has already guarded."""
    output = dict(task.output or {})
    provider = create_video_provider(video_provider)
    scenes = provider.script(
        topic=output.get("title", ""), copy=output.get("content", ""),
        channel=(task.params or {}).get("channel", ""),
    )
    manifest = await provider.render(scenes)
    visual = dict(output.get("visual") or {})
    visual["video_ref"] = manifest["video_ref"]
    visual["video_spec"] = manifest["scenes"]
    visual["video_duration"] = manifest["duration"]
    output["visual"] = visual
    task.output = output
    task.updated_at = datetime.now(timezone.utc)
    snapshot_version(session, task, source="video", member_id=actor.id)
    _record_event(session, task, TaskEventType.EDITED, actor_id=actor.id, payload={"video": True})
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def rank_clips(session: Session, actor: Member, pillar_id: str) -> dict:
    """Rank candidate short clips from a pillar's transcript (score + reason + hook)."""
    pillar = session.get(PillarAsset, pillar_id)
    if pillar is None or pillar.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Pillar not found.")
    clips = create_clip_provider().rank(pillar.source_text)
    return {
        "pillar_id": pillar.id,
        "clips": [
            {
                "hook_sentence": c.hook_sentence, "clip_score": c.clip_score,
                "reason": c.reason, "start": c.start, "end": c.end,
            }
            for c in clips
        ],
    }


async def draft_short_from_clip(
    session: Session, actor: Member, pillar_id: str, *, hook_sentence: str, client_for_provider=None
) -> dict:
    """Turn a chosen clip into a tracked short-video asset task (AI-drafted, review-gated)."""
    _require_lead(actor)
    pillar = session.get(PillarAsset, pillar_id)
    if pillar is None or pillar.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Pillar not found.")
    if not (hook_sentence or "").strip():
        raise HTTPException(status_code=400, detail="hook cannot be empty.")
    planning = _planning_task(session, pillar.campaign_id)
    routes = route_assignees(session, actor.tenant_id)
    last = max(
        (t.sequence for t in session.exec(
            select(Task).where(Task.campaign_id == pillar.campaign_id)
        ).all()),
        default=0,
    )
    task = Task(
        tenant_id=actor.tenant_id, campaign_id=pillar.campaign_id, kind=TaskKind.ASSET,
        title=f"Short: {hook_sentence.strip()[:40]}",
        execution_mode=ExecutionMode.AI_DRAFT_HUMAN_REVIEW,
        depends_on=[planning.id] if planning is not None else [],
        assignee_id=routes.get(TaskKind.ASSET.value),
        params={
            "channel": "Short Video", "funnel_stage": "TOFU",
            "desired_action": _FUNNEL_ACTION["TOFU"], "angle": hook_sentence.strip(),
            "provenance": "clip",
        },
        pillar_id=pillar.id, phase="followup", sequence=last + 1,
    )
    session.add(task)
    _record_event(session, task, TaskEventType.CREATED, actor_id=actor.id, payload={"clip": True})
    session.commit()
    await TaskRunner(session, client_for_provider).run_ready_tasks(pillar.campaign_id)
    return {"task_id": task.id}


# --- Phase 9: governance — adaptive autonomy + the compliance gate ---


def reliability_scorecard(session: Session, actor: Member) -> list[dict]:
    """Per-AI-employee reliability + the autonomy it has EARNED. Graduated autonomy:
    proven reliability widens autonomy, weak/unproven narrows it (Agentforce/Copilot
    confidence-gating). Reuses the fleet stats already captured — automation level should
    be the OUTPUT of a policy, not a static field."""
    out = []
    for f in agent_fleet(session, actor):
        runs = f.get("runs", 0)
        avg = f.get("avg_score") or 0
        corrections = f.get("self_corrections", 0)
        if runs < 3:  # unproven → stay review-gated
            score, mode = 0, "ai_draft_human_review"
        else:
            rate = corrections / max(1, runs)
            score = max(0, min(100, round(avg - rate * 20)))
            mode = (
                "ai_auto" if score >= 85
                else "ai_draft_human_review" if score >= 60
                else "human_only"
            )
        out.append({
            "member_id": f["member_id"], "display_name": f["display_name"],
            "role": f.get("role", ""), "runs": runs, "reliability": score,
            "recommended_mode": mode,
        })
    return out


def policy_check(session: Session, actor: Member, task_id: str) -> dict:
    """Run the all-outbound compliance gate over a task's current output — returns the
    decision object {allow, violations} (the kill-switch is one rule in the pack)."""
    task = _get_task(session, actor, task_id)
    output = task.output or {}
    text = " ".join(
        str(output.get(k, "")) for k in ("title", "content", "call_to_action")
    )
    issues = policy_issues(text, channel=(task.params or {}).get("channel", ""))
    return {
        "allow": not any(i["severity"] == "block" for i in issues),
        "violations": issues,
    }


# --- Phase 10: paid creative loop + scaled 1:1 outbound ---


def plan_paid_creative(
    session: Session, actor: Member, task_id: str, *, total_budget: float = 1000.0
) -> dict:
    """Generate paid creative variants from a post, score each PRE-spend, and allocate a
    (mock) budget toward winners — the create→test→reallocate loop on mock spend."""
    task = _get_task(session, actor, task_id)
    output = task.output or {}
    headline = output.get("title", "Your offer")
    channel = (task.params or {}).get("channel", "")
    templates = [
        ("Pain-led", f"Still struggling? {headline}"),
        ("Proof-led", f"{headline} — proven on 1,000+ teams"),
        ("Outcome-led", f"Ship faster — {headline}"),
        ("Curiosity", f"What if {headline.lower()}?"),
    ]
    scorer = create_creative_scorer()
    allocator = create_budget_allocator()
    rows = []
    for angle, hl in templates:
        score, ctr = scorer.score(headline=hl, angle=angle, channel=channel)
        rows.append(
            {"angle": angle, "headline": hl, "creative_score": score, "predicted_ctr": ctr}
        )
    budgets = allocator.allocate([r["creative_score"] for r in rows], total_budget)
    for row, budget in zip(rows, budgets):
        row["allocated_budget"] = budget
    rows.sort(key=lambda r: -r["creative_score"])
    return {"total_budget": total_budget, "variants": rows}


_CHANNEL_CURVES = {
    "LinkedIn": (8000.0, 2000.0),
    "Email": (5000.0, 800.0),
    "X / Twitter": (4000.0, 1500.0),
    "Landing Page": (6000.0, 1200.0),
}


def optimize_paid_budget(session: Session, actor: Member, *, total: float = 5000.0) -> dict:
    """Allocate a budget across channels by marginal ROI (equimarginal principle). Mock
    Hill-saturation response curves now; MMM curves (PyMC-Marketing/Meridian) later."""
    _require_lead(actor)
    curves = [ChannelCurve(c, v_max, k) for c, (v_max, k) in _CHANNEL_CURVES.items()]
    return _optimize_budget(curves, total)


def _prospect_dict(p: OutboundProspect) -> dict:
    return {
        "id": p.id, "name": p.name, "company": p.company, "title": p.title,
        "signal": p.signal, "personalized_line": p.personalized_line, "status": p.status,
    }


def list_prospects(session: Session, actor: Member, campaign_id: str) -> list[dict]:
    campaign = _get_campaign(session, actor, campaign_id)
    prospects = session.exec(
        select(OutboundProspect)
        .where(OutboundProspect.campaign_id == campaign.id)
        .order_by(OutboundProspect.created_at)  # type: ignore[attr-defined]
    ).all()
    return [_prospect_dict(p) for p in prospects]


def add_prospect(
    session: Session, actor: Member, campaign_id: str, *, name: str, domain: str
) -> dict:
    _require_lead(actor)
    campaign = _get_campaign(session, actor, campaign_id)
    if not (name or "").strip():
        raise HTTPException(status_code=400, detail="prospect name cannot be empty.")
    session.add(
        OutboundProspect(
            tenant_id=actor.tenant_id, campaign_id=campaign.id,
            name=name.strip(), domain=(domain or "").strip(),
        )
    )
    session.commit()
    return {"prospects": list_prospects(session, actor, campaign_id)}


def _get_prospect(session, actor, prospect_id) -> OutboundProspect:
    p = session.get(OutboundProspect, prospect_id)
    if p is None or p.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Prospect not found.")
    return p


def enrich_prospect(session: Session, actor: Member, prospect_id: str) -> dict:
    """Waterfall-enrich, write a per-lead personalized line, and policy-gate it before it
    can ever send (the same PolicyGate as all outbound)."""
    _require_lead(actor)
    p = _get_prospect(session, actor, prospect_id)
    enrichment = enrich_waterfall(p.name, p.domain, create_enrichment_waterfall())
    if enrichment is None:
        p.status = "new"  # no domain → nothing to enrich
    else:
        brand = get_brand(session, actor)
        vp = brand.value_proposition if brand else "ship with confidence"
        line = personalized_line(p.name, enrichment, vp)
        p.company, p.title, p.signal = enrichment.company, enrichment.title, enrichment.signal
        p.personalized_line = line
        blocked = any(i["severity"] == "block" for i in policy_issues(line))
        p.status = "blocked" if blocked else "enriched"
    session.add(p)
    session.commit()
    return {"prospects": list_prospects(session, actor, p.campaign_id)}


def send_outbound(session: Session, actor: Member, prospect_id: str) -> dict:
    """Mock send, gated by the DeliverabilityGuard (daily cap stands in for warmup ramp +
    mailbox rotation + bounce/spam auto-pause)."""
    _require_lead(actor)
    p = _get_prospect(session, actor, prospect_id)
    if p.status != "enriched":
        raise HTTPException(
            status_code=409, detail="Prospect must be enriched + policy-clean before send."
        )
    # Consent gate: never send to a subject that denied/withdrew (composes pre-send).
    if consent_status(session, actor.tenant_id, p.domain or p.name, "outbound_email") in (
        "denied", "withdrawn",
    ):
        p.status = "blocked"
        session.add(p)
        session.commit()
        return {"prospects": list_prospects(session, actor, p.campaign_id)}
    # Egress gate: this send is data leaving the environment (air-gapped blocks it).
    if not create_egress_gate(get_settings().deployment_profile).evaluate(
        p.personalized_line, destination="external"
    ).allow:
        p.status = "blocked"
        session.add(p)
        session.commit()
        return {"prospects": list_prospects(session, actor, p.campaign_id)}
    sent_today = len(
        session.exec(
            select(OutboundProspect).where(
                OutboundProspect.campaign_id == p.campaign_id,
                OutboundProspect.status == "sent",
            )
        ).all()
    )
    ok, reason = create_deliverability_guard().can_send(sent_today)
    if not ok:
        raise HTTPException(status_code=429, detail=reason)
    p.status = "sent"
    session.add(p)
    session.commit()
    return {"prospects": list_prospects(session, actor, p.campaign_id)}


# --- Enterprise onboarding: warm-start from the customer's existing world ---

_IMPORT_CAMPAIGN_NAME = "Imported history"


def _import_campaign(session: Session, actor: Member) -> Campaign:
    existing = session.exec(
        select(Campaign).where(
            Campaign.tenant_id == actor.tenant_id, Campaign.template == "import"
        )
    ).first()
    if existing is not None:
        return existing
    campaign = Campaign(
        tenant_id=actor.tenant_id, name=_IMPORT_CAMPAIGN_NAME, template="import",
        brief={"product_name": "Imported content"},
        created_by=actor.id,
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


def import_historical(session: Session, actor: Member, rows: list[dict]) -> dict:
    """Turn a customer's past content + performance into COMPLETED, MEASURED posts, so the
    existing flywheel (learn_outcomes) and ICP (score_segments) warm-start with real priors
    instead of cold-starting. Lead only."""
    _require_lead(actor)
    campaign = _import_campaign(session, actor)
    posts = create_import_provider().parse_historical(rows or [])
    last = max(
        (t.sequence for t in session.exec(
            select(Task).where(Task.campaign_id == campaign.id)
        ).all()),
        default=0,
    )
    for i, hp in enumerate(posts):
        funnel = _FUNNEL_STAGES[i % len(_FUNNEL_STAGES)]
        task = Task(
            tenant_id=actor.tenant_id, campaign_id=campaign.id, kind=TaskKind.ASSET,
            title=(hp.title[:60] or f"Imported {hp.channel}"),
            status=TaskStatus.DONE, execution_mode=ExecutionMode.HUMAN_ONLY,
            output={
                "asset_type": "post", "channel": hp.channel, "title": hp.title,
                "content": hp.content, "call_to_action": hp.call_to_action, "notes": [],
            },
            params={
                "channel": hp.channel, "segment": hp.segment,
                "funnel_stage": funnel, "provenance": "import",
            },
            sequence=last + 1 + i,
        )
        session.add(task)
        post = Post(
            tenant_id=actor.tenant_id, campaign_id=campaign.id, asset_task_id=task.id,
            platform=hp.channel or "imported", url=f"https://imported/{task.id[:8]}",
            published_at=hp.published_at or task.created_at.date().isoformat(),
            publish_status="published",
        )
        session.add(post)
        session.add(
            MetricSnapshot(
                tenant_id=actor.tenant_id, campaign_id=campaign.id, post_id=post.id,
                source="import", impressions=hp.impressions, clicks=hp.clicks,
                signups=hp.conversions,
            )
        )
    session.commit()
    learn_outcomes(session, actor.tenant_id)  # warm-start the flywheel from history
    return {"imported": len(posts), "insights": get_growth_insights(session, actor)}


def ingest_brand_knowledge(session: Session, actor: Member, *, text: str) -> dict:
    """Extract structured brand knowledge from docs/site text and apply it to the brand
    (voice / value-prop / pillars / tone). Lead only."""
    _require_lead(actor)
    draft = create_import_provider().extract_brand(text or "")
    brand = get_brand(session, actor)
    if brand is None:
        brand = BrandProfile(tenant_id=actor.tenant_id)
        session.add(brand)
    if draft.voice:
        brand.voice = draft.voice
    if draft.tone_rules:
        brand.tone_rules = draft.tone_rules
    if draft.forbidden_words:
        brand.forbidden_words = draft.forbidden_words
    if draft.value_proposition:
        brand.value_proposition = draft.value_proposition
    if draft.messaging_pillars:
        brand.messaging_pillars = draft.messaging_pillars
    session.add(brand)
    session.commit()
    for seg in draft.segments:
        upsert_segment(
            session, actor, name=seg.get("name", ""), description=seg.get("description", ""),
            profile="", platforms=seg.get("platforms", []), pain_points=seg.get("pain_points", []),
            value_props=[], objections=[], reach_tactics=[],
        )
    return {
        "draft": {
            "voice": draft.voice, "value_proposition": draft.value_proposition,
            "messaging_pillars": draft.messaging_pillars, "tone_rules": draft.tone_rules,
        },
        "applied": True,
    }


# --- On-prem deployment posture + privacy gates ---


def consent_status(
    session: Session, tenant_id: str, subject_id: str, purpose: str
) -> str:
    """Latest consent basis for a subject+purpose; no record = legitimate_interest."""
    rec = session.exec(
        select(ConsentRecord)
        .where(
            ConsentRecord.tenant_id == tenant_id,
            ConsentRecord.subject_id == subject_id,
            ConsentRecord.purpose == purpose,
        )
        .order_by(ConsentRecord.created_at.desc())  # type: ignore[attr-defined]
    ).first()
    return rec.status if rec is not None else "legitimate_interest"


def record_consent(
    session: Session, actor: Member, *, subject_id: str, purpose: str = "outbound_email",
    status: str = "granted", legal_basis: str = "consent",
) -> dict:
    _require_lead(actor)
    session.add(
        ConsentRecord(
            tenant_id=actor.tenant_id, subject_id=subject_id, purpose=purpose,
            status=status, legal_basis=legal_basis, source="manual",
        )
    )
    session.commit()
    return {"subject_id": subject_id, "purpose": purpose, "status": status}


def get_deployment_status(session: Session, actor: Member) -> dict:
    """The deployment posture + which providers run local vs cloud + the active gates —
    the 'can it run with nothing leaving our VPC?' answer."""
    s = get_settings()
    profile = s.deployment_profile
    forces_local = profile in ("on_prem", "air_gapped")
    return {
        "profile": profile,
        "providers": {
            "llm": "local" if (forces_local or s.llm_provider == "local") else s.llm_provider,
            "image": "local (ComfyUI/FLUX)" if forces_local else "mock",
            "analytics": "local" if forces_local else "mock",
            "vector": "local (pgvector)" if forces_local else "n/a",
        },
        "gates": {
            "pii_redaction": True,
            "egress": profile,
            "consent": True,
            "policy": True,
        },
        "data_leaves_environment": profile not in ("on_prem", "air_gapped"),
    }
