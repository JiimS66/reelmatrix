"""Service layer for the human-AI team workspace.

Holds the DB operations and permission checks behind the team API. Every query
is scoped to the acting member's tenant. The runner (AI execution) is invoked
from the route layer because it is async; this module stays synchronous.
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from core.db.models import (
    Annotation,
    BrandProfile,
    BrandTerm,
    Campaign,
    Comment,
    ContentAtom,
    ContentVersion,
    DirectMessage,
    EpisodicNote,
    ExecutionMode,
    Member,
    MemberKind,
    MemberRole,
    MetricSnapshot,
    Milestone,
    Post,
    Task,
    TaskEvent,
    TaskEventType,
    TaskKind,
    TaskStatus,
    UsageEvent,
)
from core.agents.roles import ROLES
from core.content.scoring import content_score
from core.content.tracking import mock_metrics
from core.llm.base import BaseLLMClient
from core.workflows.campaign_instantiation import instantiate_campaign
from core.workflows.task_runner import (
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
    session.add(
        DirectMessage(
            tenant_id=actor.tenant_id, member_id=member_id, sender="lead",
            kind=kind, title=title, body=body.strip(),
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
