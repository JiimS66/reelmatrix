"""Async runner that advances a campaign's task graph.

The runner executes the directly-runnable AI tasks (ideation, planning, and the
per-channel posts) whose dependencies are satisfied, persisting their output, a
UsageEvent, and audit TaskEvents. Completing a planning task fans its plan out
into the downstream claim-check task (posts are rendered by the Copywriter from
the shared content core, not carved from the plan).

Because ``instantiate_campaign`` defaults ideation/planning/posts to ``ai_auto``
(the Task model's own field default is the safer ``ai_draft_human_review``), a run
typically advances through every AI-owned step in one pass; only human-only tasks
(e.g. the claim check) stay in ``todo`` until a human submits them. ``complete_task``
is shared with the review API so approvals re-trigger the same fan-out; both
``complete_task`` and ``fan_out_from_plan`` are idempotent and never overwrite
work a human has already touched.
"""

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Callable, Optional

from sqlmodel import Session, select

from configs.settings import get_settings
from core.agents.employees import agent_for_role
from core.db.models import (
    BrandProfile,
    Campaign,
    ContentAtom,
    EpisodicNote,
    ExecutionMode,
    Member,
    MemberKind,
    MemberRole,
    Post,
    Task,
    TaskEvent,
    TaskEventType,
    TaskKind,
    TaskStatus,
    UsageEvent,
)
from core.content.atoms import atoms_from_asset
from core.content.brand import forbidden_word_issues
from core.content.tracking import utm_url
from core.content.consistency import approved_stat_text, unsourced_stat_issues
from core.content.platform_specs import format_checks, spec_for_channel
from core.llm.base import BaseLLMClient
from core.llm.factory import create_llm_client
from core.media.base import VisionProvider
from core.media.factory import create_vision_provider
from core.schemas.campaign import IdeationResult

ClientForProvider = Callable[[str], BaseLLMClient]
VisionForName = Callable[[str], VisionProvider]

_RUNNABLE_KINDS = (TaskKind.IDEATION, TaskKind.PLANNING, TaskKind.ASSET, TaskKind.VISUAL)
# Fallback agent for each kind when the assigned member declares no explicit role.
_ROLE_BY_KIND = {
    TaskKind.IDEATION: "ideation",
    TaskKind.PLANNING: "planning",
    TaskKind.ASSET: "copywriter",
    TaskKind.VISUAL: "designer",
}


def role_for(task: Task, member: Optional[Member]) -> str:
    """The agent that runs this task: the member's configured role takes precedence,
    so a tenant can point a kind at a custom agent without editing _ROLE_BY_KIND."""
    configured = (member.agent_config or {}).get("role") if member else None
    return configured or _ROLE_BY_KIND[task.kind]


# How many times a failed asset may be re-rendered with its check failures fed back
# before the runner keeps the cleanest draft and moves on (checks stay advisory).
_MAX_ASSET_REVISIONS = 2


def _issue_count(checks: dict) -> int:
    return sum(len(issues) for issues in checks.values())


def _revision_notes(checks: dict) -> list[str]:
    """The check failures, as plain sentences to feed back to the agent."""
    return [issue.get("detail", "") for issues in checks.values() for issue in issues]


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


def _record_usage(session: Session, task: Task, member: Optional[Member]) -> None:
    """Meter one AI call for billing — one row per LLM call, so self-correction
    retries and the auditor are counted too. Attributed to the member that did the
    work (the copywriter for a render, the auditor for an audit)."""
    config = (member.agent_config or {}) if member else {}
    session.add(
        UsageEvent(
            tenant_id=task.tenant_id,
            task_id=task.id,
            member_id=member.id if member else task.assignee_id,
            provider=config.get("provider", "mock"),
            model=config.get("model"),
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


def asset_checks(asset: dict, channel: str, forbidden: list[str], approved_text: str) -> dict:
    """The format/brand/consistency checks recorded on every asset task."""
    return {
        "format": format_checks(asset, channel),
        "brand": forbidden_word_issues(asset, forbidden),
        "consistency": unsourced_stat_issues(asset, approved_text),
    }


def checks_for_output(session: Session, task: Task, output: dict) -> dict:
    """Compute an asset's format/brand/consistency checks for a candidate output.

    Read-only on the session (brand + plan lookups only), so it is safe to call
    inside a gathered render while other tasks' renders are in flight.
    """
    brand = session.exec(
        select(BrandProfile).where(BrandProfile.tenant_id == task.tenant_id)
    ).first()
    forbidden = brand.forbidden_words if brand is not None else []
    planning = session.exec(
        select(Task).where(
            Task.campaign_id == task.campaign_id, Task.kind == TaskKind.PLANNING
        )
    ).first()
    plan = (planning.output if planning is not None else None) or {}
    approved_text = approved_stat_text(plan, brand.proof_points if brand is not None else [])
    return asset_checks(
        output or {}, (task.params or {}).get("channel", ""), forbidden, approved_text
    )


def recompute_asset_checks(session: Session, task: Task) -> dict:
    """Recompute an asset task's checks from its current output (e.g. after a human edit)."""
    return checks_for_output(session, task, task.output or {})


def fan_out_from_plan(session: Session, planning_task: Task) -> None:
    """Seed the downstream claim-check task from a finished plan.

    Asset tasks are no longer carved from the plan here — the Copywriter agent
    renders each one from the shared content core (run by the runner). Idempotent:
    a claim-check that already has output is left untouched.
    """
    plan = planning_task.output or {}
    downstream = session.exec(
        select(Task).where(
            Task.tenant_id == planning_task.tenant_id,
            Task.campaign_id == planning_task.campaign_id,
        )
    ).all()

    for task in downstream:
        if planning_task.id not in (task.depends_on or []):
            continue
        if task.kind == TaskKind.CLAIM_CHECK and task.output is None:
            task.output = {"claim_checks": plan.get("claim_checks") or []}
            task.updated_at = _now()
            _record_event(
                session, task, TaskEventType.SUBMITTED, payload={"source": "planning_fan_out"}
            )
            session.add(task)


def harvest_atoms(session: Session, task: Task) -> None:
    """Harvest reusable atoms from an approved asset into the tenant library.

    Idempotent: identical (kind, text) atoms in the tenant are not duplicated.
    """
    if task.kind != TaskKind.ASSET or not task.output:
        return
    existing = {
        (atom.kind, atom.text)
        for atom in session.exec(
            select(ContentAtom).where(ContentAtom.tenant_id == task.tenant_id)
        ).all()
    }
    channel = (task.params or {}).get("channel")
    tags = [channel] if channel else []
    for kind, text in atoms_from_asset(task.output):
        if (kind, text) in existing:
            continue
        existing.add((kind, text))
        session.add(
            ContentAtom(
                tenant_id=task.tenant_id,
                kind=kind,
                text=text,
                tags=tags,
                source_campaign_id=task.campaign_id,
                source_task_id=task.id,
            )
        )


def _publish_post(session: Session, task: Task) -> None:
    """Record a published Post when an asset is approved (the metrics target)."""
    campaign = session.get(Campaign, task.campaign_id)
    if campaign is None:
        return
    channel = (task.params or {}).get("channel") or "web"
    session.add(
        Post(
            tenant_id=task.tenant_id,
            campaign_id=task.campaign_id,
            asset_task_id=task.id,
            platform=channel,
            url=utm_url(campaign, task),
            published_at=task.due_date or task.updated_at.date().isoformat(),
        )
    )


def complete_task(session: Session, task: Task, *, actor_id: Optional[str] = None) -> None:
    """Mark a task done, audit it, and run kind-specific follow-ups.

    Idempotent and does not commit; the caller owns the transaction.
    """
    if task.status == TaskStatus.DONE:
        return
    task.status = TaskStatus.DONE
    task.updated_at = _now()
    _record_event(session, task, TaskEventType.APPROVED, actor_id=actor_id)
    if task.kind == TaskKind.PLANNING:
        fan_out_from_plan(session, task)
    elif task.kind == TaskKind.ASSET:
        harvest_atoms(session, task)
        _publish_post(session, task)
    session.add(task)


class TaskRunner:
    def __init__(
        self,
        session: Session,
        client_for_provider: Optional[ClientForProvider] = None,
        vision_for_name: Optional[VisionForName] = None,
    ) -> None:
        self._session = session
        self._client_for_provider = client_for_provider or default_client_for_provider
        self._vision_for_name = vision_for_name or create_vision_provider
        # Extra check groups produced during a gathered render (the Auditor's "audit"
        # for posts, the visual critic's "brand_fit" for visuals), handed to the serial
        # _persist which merges them into task.checks. Keyed by task id.
        self._pending_checks: dict[str, dict] = {}

    async def run_ready_tasks(self, campaign_id: str) -> list[str]:
        """Run every currently-ready AI task. Independent tasks (e.g. the per-channel
        posts once the plan's core is locked) render concurrently; persistence stays
        serial on the single session."""
        ran: list[str] = []
        while True:
            ready = self._ready_ai_tasks(campaign_id)
            if not ready:
                break
            rendered = await asyncio.gather(
                *(self._render(task) for task in ready), return_exceptions=True
            )
            for task, result in zip(ready, rendered):
                if isinstance(result, BaseException):
                    self._revert_failed(task, result)
                    self._session.commit()
                    raise result
                if result is not None:
                    self._persist(task, result)
                    ran.append(task.id)
                self._session.commit()
        return ran

    def _campaign_tasks(self, campaign_id: str) -> list[Task]:
        return list(
            self._session.exec(select(Task).where(Task.campaign_id == campaign_id)).all()
        )

    def _ready_ai_tasks(self, campaign_id: str) -> list[Task]:
        tasks = self._campaign_tasks(campaign_id)
        done_ids = {t.id for t in tasks if t.status == TaskStatus.DONE}
        ready: list[Task] = []
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
                ready.append(task)
        return ready

    async def _render(self, task: Task) -> Optional[dict]:
        """Produce a task's output — the only await is the agent's LLM call, so
        gathered renders overlap only there. Returns None when the task is blocked
        (handled in place); raises on agent failure (the caller reverts)."""
        campaign = self._session.get(Campaign, task.campaign_id)
        if campaign is None:
            task.status = TaskStatus.BLOCKED
            _record_event(
                self._session, task, TaskEventType.STATUS_CHANGED,
                payload={"reason": "missing_campaign"},
            )
            self._session.add(task)
            return None

        member = self._session.get(Member, task.assignee_id)
        provider = (member.agent_config or {}).get("provider", "mock") if member else "mock"
        client = self._client_for_provider(provider)
        task.status = TaskStatus.IN_PROGRESS

        role_key = role_for(task, member)
        context = self._build_context(task, campaign)
        if task.kind == TaskKind.PLANNING:
            ideation_result = IdeationResult.model_validate(context["ideation_result"])
            if not ideation_result.is_ready_for_planning:
                task.status = TaskStatus.BLOCKED
                _record_event(
                    self._session, task, TaskEventType.STATUS_CHANGED,
                    payload={"reason": "ideation_not_ready"},
                )
                self._session.add(task)
                return None
        output = await agent_for_role(role_key, client).run(context)
        if task.kind == TaskKind.ASSET:
            output = await self._self_correct(task, member, client, role_key, context, output)
        elif task.kind == TaskKind.VISUAL:
            output = await self._critique_visual(task, member, client, role_key, context, output)
        return output

    async def _self_correct(
        self,
        task: Task,
        member: Optional[Member],
        client: BaseLLMClient,
        role_key: str,
        context: dict,
        output: dict,
    ) -> dict:
        """Re-render an asset whose checks fail, feeding the failures back, and keep
        the cleanest draft. The runner's execution-time half of self-improvement;
        checks stay advisory, so a draft that can't be fixed still goes through.

        Failures come from both the deterministic checks AND the LLM-as-judge Auditor
        (a different model family, when configured); both feed the revision notes."""
        checks = checks_for_output(self._session, task, output)
        audit = await self._run_audit(task, output, context)  # None when no auditor
        best, best_audit = output, audit
        best_issues = _issue_count(checks) + len(audit or [])
        passes = 0
        while best_issues > 0 and passes < _MAX_ASSET_REVISIONS:
            passes += 1
            notes = _revision_notes(checks) + [issue["detail"] for issue in (audit or [])]
            candidate = await agent_for_role(role_key, client).run(
                {**context, "revision_notes": notes}
            )
            _record_usage(self._session, task, member)  # each retry is a metered call
            checks = checks_for_output(self._session, task, candidate)
            audit = await self._run_audit(task, candidate, context)
            issues = _issue_count(checks) + len(audit or [])
            if issues < best_issues:
                best, best_audit, best_issues = candidate, audit, issues
            if best_issues == 0:
                break
        if best_audit is not None:
            self._pending_checks[task.id] = {"audit": best_audit}
        if passes:
            _record_event(
                self._session, task, TaskEventType.SELF_CORRECTED,
                actor_id=task.assignee_id,
                payload={"passes": passes, "remaining_issues": best_issues},
            )
        return best

    async def _critique_visual(
        self,
        task: Task,
        member: Optional[Member],
        client: BaseLLMClient,
        role_key: str,
        context: dict,
        output: dict,
    ) -> dict:
        """Re-render a visual the VisionProvider judges off-brand, feeding the critique
        back, keeping the cleanest. The visual analogue of post self-correction; the
        critique (a VLM-as-judge) is surfaced as the visual's brand_fit check."""
        critique = await self._run_visual_critique(task, output, context)  # None if no ref
        best, best_critique, best_issues = output, critique, len(critique or [])
        passes = 0
        while best_issues > 0 and passes < _MAX_ASSET_REVISIONS:
            passes += 1
            notes = [issue["detail"] for issue in (critique or [])]
            candidate = await agent_for_role(role_key, client).run(
                {**context, "revision_notes": notes}
            )
            _record_usage(self._session, task, member)
            critique = await self._run_visual_critique(task, candidate, context)
            issues = len(critique or [])
            if issues < best_issues:
                best, best_critique, best_issues = candidate, critique, issues
            if best_issues == 0:
                break
        if best_critique is not None:
            self._pending_checks[task.id] = {"brand_fit": best_critique}
        if passes:
            _record_event(
                self._session, task, TaskEventType.SELF_CORRECTED,
                actor_id=task.assignee_id,
                payload={"passes": passes, "remaining_issues": best_issues, "kind": "visual"},
            )
        return best

    async def _run_visual_critique(
        self, task: Task, output: dict, context: dict
    ) -> Optional[list[dict]]:
        """VLM-as-judge on a rendered visual vs the campaign text + brand. Returns
        issues as {code, detail} dicts, or None when there is no image to judge."""
        image_ref = (output or {}).get("image_ref")
        if not image_ref:
            return None
        provider = self._vision_for_name("mock")
        verdict = await provider.critique(
            media_ref=image_ref,
            campaign_text=context.get("core_message", ""),
            brand=context.get("brand", {}),
        )
        return [{"code": "brand_fit", "detail": issue} for issue in verdict.issues]

    def _auditor_member(self, tenant_id: str) -> Optional[Member]:
        """The tenant's configured Auditor (an AI member whose role is 'auditor'),
        or None if the tenant hasn't hired one — in which case audit is skipped."""
        members = self._session.exec(
            select(Member).where(
                Member.tenant_id == tenant_id, Member.kind == MemberKind.AI
            )
        ).all()
        return next(
            (m for m in members if (m.agent_config or {}).get("role") == "auditor"), None
        )

    async def _run_audit(self, task: Task, post: dict, context: dict) -> Optional[list[dict]]:
        """Judge a rendered post with the tenant's Auditor (on its own — ideally
        different-family — provider). Returns issues as {code, detail} dicts, or None
        when no auditor is configured. Read-only on the session apart from metering."""
        auditor = self._auditor_member(task.tenant_id)
        if auditor is None:
            return None
        provider = (auditor.agent_config or {}).get("provider", "mock")
        client = self._client_for_provider(provider)
        verdict = await agent_for_role("auditor", client).run(
            {
                "channel": context.get("channel", ""),
                "core_message": context.get("core_message", ""),
                "approved_claims": context.get("approved_claims", []),
                "brand": context.get("brand", {}),
                "post": post,
            }
        )
        _record_usage(self._session, task, auditor)
        return [
            {"code": issue["dimension"], "detail": issue["detail"]}
            for issue in verdict.get("issues", [])
        ]

    def _persist(self, task: Task, output: dict) -> None:
        """Persist a rendered output (sync — keeps the single session serial)."""
        member = self._session.get(Member, task.assignee_id)
        provider = (member.agent_config or {}).get("provider", "mock") if member else "mock"
        task.ai_draft = output
        task.output = output
        if task.kind == TaskKind.ASSET:
            checks = recompute_asset_checks(self._session, task)
            checks.update(self._pending_checks.pop(task.id, {}))  # + the Auditor's "audit"
            task.checks = checks
        elif task.kind == TaskKind.VISUAL:
            task.checks = self._pending_checks.pop(task.id, {})  # the "brand_fit" critique
        task.updated_at = _now()
        _record_usage(self._session, task, member)
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

    def _revert_failed(self, task: Task, exc: BaseException) -> None:
        task.status = TaskStatus.TODO
        _record_event(
            self._session, task, TaskEventType.STATUS_CHANGED,
            payload={"error": type(exc).__name__},
        )
        self._session.add(task)

    def _build_context(self, task: Task, campaign: Campaign) -> dict:
        """The blackboard slice an agent reads — only its dependencies, nothing more."""
        if task.kind == TaskKind.ASSET:
            return self._copywriter_context(task, campaign)
        if task.kind == TaskKind.VISUAL:
            return self._designer_context(task, campaign)
        payload = dict(campaign.brief)
        payload.setdefault("campaign_template", campaign.template)
        context: dict = {"request": payload}
        if task.kind == TaskKind.PLANNING:
            context["ideation_result"] = self._ideation_output(task)
        return context

    def _copywriter_context(self, task: Task, campaign: Campaign) -> dict:
        """The slice a copywriter reads: shared core + platform spec + brand."""
        planning = (
            self._session.get(Task, task.depends_on[0]) if task.depends_on else None
        )
        plan = (planning.output if planning is not None else None) or {}
        channel = (task.params or {}).get("channel", "")
        spec = spec_for_channel(channel)
        brand = self._session.exec(
            select(BrandProfile).where(BrandProfile.tenant_id == task.tenant_id)
        ).first()
        notes = self._session.exec(
            select(EpisodicNote)
            .where(EpisodicNote.campaign_id == task.campaign_id)
            .order_by(EpisodicNote.created_at.desc())  # type: ignore[attr-defined]
        ).all()
        return {
            "recent_feedback": [note.text for note in notes[:5]],
            "channel": channel,
            "core_message": plan.get("core_message", ""),
            "approved_claims": [
                claim.get("claim", "")
                for claim in (plan.get("claim_checks") or [])
                if claim.get("status") == "source_backed"
            ],
            "product_name": (campaign.brief or {}).get("product_name", ""),
            "platform": asdict(spec) if spec is not None else {},
            "brand": {
                "voice": brand.voice,
                "tone_rules": brand.tone_rules,
                "forbidden_words": brand.forbidden_words,
            }
            if brand is not None
            else {},
        }

    def _designer_context(self, task: Task, campaign: Campaign) -> dict:
        """The slice a Designer reads: shared core + channel + brand identity."""
        planning = (
            self._session.get(Task, task.depends_on[0]) if task.depends_on else None
        )
        plan = (planning.output if planning is not None else None) or {}
        brand = self._session.exec(
            select(BrandProfile).where(BrandProfile.tenant_id == task.tenant_id)
        ).first()
        return {
            "channel": (task.params or {}).get("channel", ""),
            "core_message": plan.get("core_message", ""),
            "product_name": (campaign.brief or {}).get("product_name", ""),
            "brand": {
                "voice": brand.voice,
                "tone_rules": brand.tone_rules,
            }
            if brand is not None
            else {},
        }

    def _ideation_output(self, planning_task: Task) -> dict:
        for dep_id in planning_task.depends_on or []:
            dep = self._session.get(Task, dep_id)
            if dep is not None and dep.kind == TaskKind.IDEATION:
                return dep.output or {}
        for task in self._campaign_tasks(planning_task.campaign_id):
            if task.kind == TaskKind.IDEATION:
                return task.output or {}
        return {}
