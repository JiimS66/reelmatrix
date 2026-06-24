"""Service layer for the human-AI team workspace.

Holds the DB operations and permission checks behind the team API. Every query
is scoped to the acting member's tenant. The runner (AI execution) is invoked
from the route layer because it is async; this module stays synchronous.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from core.db.models import (
    Campaign,
    Comment,
    ContentAtom,
    ExecutionMode,
    Member,
    MemberKind,
    MemberRole,
    Task,
    TaskEvent,
    TaskEventType,
    TaskStatus,
)
from core.workflows.campaign_instantiation import instantiate_campaign
from core.workflows.task_runner import complete_task


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


def create_campaign(
    session: Session, actor: Member, *, name: str, brief: dict, template: str
) -> Campaign:
    _require_lead(actor)
    return instantiate_campaign(
        session,
        tenant_id=actor.tenant_id,
        name=name,
        brief=brief,
        template=template,
        created_by=actor.id,
    )


def list_tenant_members(session: Session, tenant_id: str) -> list[Member]:
    return list(
        session.exec(select(Member).where(Member.tenant_id == tenant_id)).all()
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
    if output is not None:
        task.output = output
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

    if action == "approve":
        if output is not None:
            task.output = output
            _record_event(session, task, TaskEventType.EDITED, actor_id=actor.id)
        complete_task(session, task, actor_id=actor.id)
    else:  # request_changes
        task.status = TaskStatus.IN_PROGRESS
        _record_event(
            session, task, TaskEventType.CHANGES_REQUESTED, actor_id=actor.id,
            payload={"note": note},
        )
        session.add(task)
    session.commit()
    return task


def add_comment(session: Session, actor: Member, task_id: str, *, body: str) -> Comment:
    task = _get_task(session, actor, task_id)
    comment = Comment(
        tenant_id=task.tenant_id, task_id=task.id, author_id=actor.id, body=body
    )
    session.add(comment)
    _record_event(session, task, TaskEventType.COMMENTED, actor_id=actor.id)
    session.commit()
    return comment


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
