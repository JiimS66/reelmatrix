"""Async runner that advances a campaign's task graph.

The runner executes the directly-runnable AI tasks (ideation, planning) whose
dependencies are satisfied, persisting their output, a UsageEvent, and audit
TaskEvents. Completing a planning task fans its plan out into the downstream
asset and claim-check tasks.

Because the default execution mode is ``ai_draft_human_review``, a fresh run
typically advances only one step (ideation) and then stops, waiting for a human
to approve before the next AI task becomes ready. ``complete_task`` is shared
with the review API so approvals re-trigger the same fan-out; both
``complete_task`` and ``fan_out_from_plan`` are idempotent and never overwrite
work a human has already touched.
"""

from datetime import datetime, timezone
from typing import Callable, Optional

from sqlmodel import Session, select

from configs.settings import get_settings
from core.agents.ideation_bot import IdeationBot
from core.agents.planning_bot import PlanningBot
from core.db.models import (
    BrandProfile,
    Campaign,
    ExecutionMode,
    Member,
    MemberKind,
    MemberRole,
    Task,
    TaskEvent,
    TaskEventType,
    TaskKind,
    TaskStatus,
    UsageEvent,
)
from core.content.brand import forbidden_word_issues
from core.content.consistency import approved_stat_text, unsourced_stat_issues
from core.content.platform_specs import format_checks
from core.llm.base import BaseLLMClient
from core.llm.factory import create_llm_client
from core.schemas.campaign import CampaignGenerationRequest, IdeationResult

ClientForProvider = Callable[[str], BaseLLMClient]

_RUNNABLE_KINDS = (TaskKind.IDEATION, TaskKind.PLANNING)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def default_client_for_provider(provider: str) -> BaseLLMClient:
    settings = get_settings().model_copy(update={"llm_provider": provider})
    return create_llm_client(settings)


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


def _campaign_lead_id(session: Session, tenant_id: str) -> Optional[str]:
    lead = session.exec(
        select(Member)
        .where(
            Member.tenant_id == tenant_id,
            Member.kind == MemberKind.HUMAN,
            Member.role == MemberRole.LEAD,
        )
        .order_by(Member.created_at)
    ).first()
    return lead.id if lead is not None else None


def fan_out_from_plan(session: Session, planning_task: Task) -> None:
    """Populate downstream asset and claim-check tasks from a finished plan.

    Idempotent: only untouched (still-TODO / unseeded) downstream tasks are
    written, so re-running after a human edit never clobbers their work.
    """
    plan = planning_task.output or {}
    by_channel = {
        (asset.get("channel") or "").lower(): asset
        for asset in (plan.get("draft_assets") or [])
    }
    lead_id = _campaign_lead_id(session, planning_task.tenant_id)
    brand = session.exec(
        select(BrandProfile).where(BrandProfile.tenant_id == planning_task.tenant_id)
    ).first()
    forbidden = brand.forbidden_words if brand is not None else []
    approved_text = approved_stat_text(plan, brand.proof_points if brand is not None else [])
    downstream = session.exec(
        select(Task).where(
            Task.tenant_id == planning_task.tenant_id,
            Task.campaign_id == planning_task.campaign_id,
        )
    ).all()

    for task in downstream:
        if planning_task.id not in (task.depends_on or []):
            continue

        if task.kind == TaskKind.ASSET and task.execution_mode != ExecutionMode.HUMAN_ONLY:
            if task.status != TaskStatus.TODO or (task.params or {}).get("ai_draft_skipped"):
                continue
            asset = by_channel.get((task.params or {}).get("channel", "").lower())
            if asset is None:
                # No AI draft for this channel: hand it to the lead to write.
                task.params = {**(task.params or {}), "ai_draft_skipped": True}
                task.assignee_id = lead_id or task.assignee_id
                task.updated_at = _now()
                _record_event(
                    session, task, TaskEventType.STATUS_CHANGED,
                    payload={"reason": "no_ai_draft_for_channel"},
                )
                session.add(task)
                continue
            task.ai_draft = asset
            task.output = asset
            task.checks = {
                "format": format_checks(asset, (task.params or {}).get("channel", "")),
                "brand": forbidden_word_issues(asset, forbidden),
                "consistency": unsourced_stat_issues(asset, approved_text),
            }
            task.updated_at = _now()
            if task.execution_mode == ExecutionMode.AI_AUTO:
                task.status = TaskStatus.DONE
            else:
                task.status = TaskStatus.NEEDS_REVIEW
                task.assignee_id = lead_id or task.assignee_id
            _record_event(
                session, task, TaskEventType.SUBMITTED, payload={"source": "planning_fan_out"}
            )
            session.add(task)
        elif task.kind == TaskKind.CLAIM_CHECK:
            if task.output is not None:
                continue  # already seeded
            task.output = {"claim_checks": plan.get("claim_checks") or []}
            task.updated_at = _now()
            _record_event(
                session, task, TaskEventType.SUBMITTED, payload={"source": "planning_fan_out"}
            )
            session.add(task)


def complete_task(session: Session, task: Task, *, actor_id: Optional[str] = None) -> None:
    """Mark a task done, audit it, and fan out if it is the planning task.

    Idempotent and does not commit; the caller owns the transaction.
    """
    if task.status == TaskStatus.DONE:
        return
    task.status = TaskStatus.DONE
    task.updated_at = _now()
    _record_event(session, task, TaskEventType.APPROVED, actor_id=actor_id)
    if task.kind == TaskKind.PLANNING:
        fan_out_from_plan(session, task)
    session.add(task)


class TaskRunner:
    def __init__(
        self,
        session: Session,
        client_for_provider: Optional[ClientForProvider] = None,
    ) -> None:
        self._session = session
        self._client_for_provider = client_for_provider or default_client_for_provider

    async def run_ready_tasks(self, campaign_id: str) -> list[str]:
        """Run every currently-ready AI task, returning the ids that ran."""
        ran: list[str] = []
        while True:
            task = self._next_ready_ai_task(campaign_id)
            if task is None:
                break
            await self._run_task(task)
            self._session.commit()
            ran.append(task.id)
        return ran

    def _campaign_tasks(self, campaign_id: str) -> list[Task]:
        return list(
            self._session.exec(select(Task).where(Task.campaign_id == campaign_id)).all()
        )

    def _next_ready_ai_task(self, campaign_id: str) -> Optional[Task]:
        tasks = self._campaign_tasks(campaign_id)
        done_ids = {t.id for t in tasks if t.status == TaskStatus.DONE}
        for task in sorted(tasks, key=lambda t: t.sequence):
            if task.kind not in _RUNNABLE_KINDS:
                continue
            if task.status != TaskStatus.TODO:
                continue
            if task.execution_mode == ExecutionMode.HUMAN_ONLY or not task.assignee_id:
                continue
            member = self._session.get(Member, task.assignee_id)
            if member is None or member.kind != MemberKind.AI:
                continue
            if all(dep in done_ids for dep in (task.depends_on or [])):
                return task
        return None

    async def _run_task(self, task: Task) -> None:
        campaign = self._session.get(Campaign, task.campaign_id)
        if campaign is None:
            task.status = TaskStatus.BLOCKED
            _record_event(
                self._session, task, TaskEventType.STATUS_CHANGED,
                payload={"reason": "missing_campaign"},
            )
            self._session.add(task)
            return

        member = self._session.get(Member, task.assignee_id)
        provider = (member.agent_config or {}).get("provider", "mock") if member else "mock"
        client = self._client_for_provider(provider)

        task.status = TaskStatus.IN_PROGRESS
        try:
            request = CampaignGenerationRequest.model_validate(campaign.brief)
            if task.kind == TaskKind.IDEATION:
                result = await IdeationBot(client).run(request)
                output = result.model_dump(mode="json")
            else:  # PLANNING
                ideation_result = IdeationResult.model_validate(self._ideation_output(task))
                if not ideation_result.is_ready_for_planning:
                    task.status = TaskStatus.BLOCKED
                    _record_event(
                        self._session, task, TaskEventType.STATUS_CHANGED,
                        payload={"reason": "ideation_not_ready"},
                    )
                    self._session.add(task)
                    return
                plan = await PlanningBot(client).run(request, ideation_result)
                output = plan.model_dump(mode="json")
        except Exception as exc:
            # Revert so a later run can retry, and leave an audit trail.
            task.status = TaskStatus.TODO
            _record_event(
                self._session, task, TaskEventType.STATUS_CHANGED,
                payload={"error": type(exc).__name__},
            )
            self._session.add(task)
            self._session.commit()
            raise

        task.ai_draft = output
        task.output = output
        task.updated_at = _now()
        self._session.add(
            UsageEvent(
                tenant_id=task.tenant_id,
                task_id=task.id,
                member_id=task.assignee_id,
                provider=provider,
                model=(member.agent_config or {}).get("model") if member else None,
            )
        )
        _record_event(
            self._session, task, TaskEventType.AI_RUN, actor_id=task.assignee_id,
            payload={"provider": provider},
        )

        if task.execution_mode == ExecutionMode.AI_AUTO:
            complete_task(self._session, task, actor_id=task.assignee_id)
        else:
            task.status = TaskStatus.NEEDS_REVIEW
            task.assignee_id = _campaign_lead_id(self._session, task.tenant_id) or task.assignee_id
            _record_event(
                self._session, task, TaskEventType.SUBMITTED,
                actor_id=member.id if member else None,
            )
            self._session.add(task)

    def _ideation_output(self, planning_task: Task) -> dict:
        for dep_id in planning_task.depends_on or []:
            dep = self._session.get(Task, dep_id)
            if dep is not None and dep.kind == TaskKind.IDEATION:
                return dep.output or {}
        for task in self._campaign_tasks(planning_task.campaign_id):
            if task.kind == TaskKind.IDEATION:
                return task.output or {}
        return {}
