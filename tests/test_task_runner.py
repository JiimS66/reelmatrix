import asyncio
import json

import pytest
from sqlmodel import Session, select

from core.db.engine import create_db_engine, init_db
from core.llm.base import BaseLLMClient, LLMProviderError
from core.db.models import (
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
from core.db.seed import seed_testsprite
from core.llm.mock_client import MockLLMClient
from core.media.base import MediaCritique, MediaUnderstanding, VisionProvider
from core.schemas.campaign import AuditDimension, AuditIssue, AuditVerdict
from core.workflows.campaign_instantiation import instantiate_campaign
from core.workflows.task_runner import TaskRunner, fan_out_from_plan, role_for


def _auditor(session: Session) -> Member:
    return next(
        m
        for m in session.exec(select(Member)).all()
        if (m.agent_config or {}).get("role") == "auditor"
    )


class _FailingClient(BaseLLMClient):
    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        raise LLMProviderError("boom")

    async def generate_structured(self, *, system_prompt, user_prompt, response_model):
        raise LLMProviderError("boom")


class _SelfCorrectingClient(BaseLLMClient):
    """Ships a forbidden word on the first draft, then complies once the failure is
    fed back via revision_notes — mimics an agent that fixes its own flagged work."""

    def __init__(self) -> None:
        self._mock = MockLLMClient()

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        return await self._mock.generate_text(
            system_prompt=system_prompt, user_prompt=user_prompt
        )

    async def generate_structured(self, *, system_prompt, user_prompt, response_model):
        asset = await self._mock.generate_structured(
            system_prompt=system_prompt, user_prompt=user_prompt, response_model=response_model
        )
        if response_model.__name__ == "CampaignAsset" and not json.loads(
            user_prompt
        ).get("revision_notes"):
            return asset.model_copy(
                update={"content": f"{asset.content} This launch is basically magic."}
            )
        return asset


class _PersistentlyDirtyClient(BaseLLMClient):
    """Always trips the brand check — self-correction can never clean it."""

    def __init__(self) -> None:
        self._mock = MockLLMClient()

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        return await self._mock.generate_text(
            system_prompt=system_prompt, user_prompt=user_prompt
        )

    async def generate_structured(self, *, system_prompt, user_prompt, response_model):
        asset = await self._mock.generate_structured(
            system_prompt=system_prompt, user_prompt=user_prompt, response_model=response_model
        )
        if response_model.__name__ == "CampaignAsset":
            return asset.model_copy(update={"content": f"{asset.content} Totally bug-free."})
        return asset


class _FlaggingAuditorClient(BaseLLMClient):
    """An auditor that rejects the first draft, then approves — so the AUDITOR alone
    (not the deterministic checks) drives a self-correction pass."""

    def __init__(self) -> None:
        self._mock = MockLLMClient()
        self.audit_calls = 0

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        return await self._mock.generate_text(
            system_prompt=system_prompt, user_prompt=user_prompt
        )

    async def generate_structured(self, *, system_prompt, user_prompt, response_model):
        if response_model.__name__ == "AuditVerdict":
            self.audit_calls += 1
            if self.audit_calls == 1:
                return AuditVerdict(
                    approved=False,
                    issues=[
                        AuditIssue(
                            dimension=AuditDimension.BRAND_TONE,
                            detail="Tone reads too hype for this brand.",
                        )
                    ],
                )
            return AuditVerdict(approved=True, issues=[])
        return await self._mock.generate_structured(
            system_prompt=system_prompt, user_prompt=user_prompt, response_model=response_model
        )

BRIEF = {
    "product_name": "TestSprite",
    "product_description": "An agentic testing platform that verifies AI-generated code.",
    "target_audience": "Engineering leaders and AI-native developers",
    "marketing_goal": "Generate qualified developer signups and API key starts",
    "user_prompt": "ready for planning: launch campaign for TestSprite",
    "selected_channels": ["LinkedIn", "Email"],
}


def _runner(session: Session) -> TaskRunner:
    return TaskRunner(session, client_for_provider=lambda provider: MockLLMClient())


def _setup() -> tuple[Session, str]:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    session = Session(engine)
    tenant = seed_testsprite(session)
    campaign = instantiate_campaign(
        session, tenant_id=tenant.id, name="Launch", brief=BRIEF
    )
    return session, campaign.id


def _task(session: Session, campaign_id: str, kind: TaskKind) -> Task:
    return session.exec(
        select(Task).where(Task.campaign_id == campaign_id, Task.kind == kind)
    ).first()


def test_runner_drafts_ideation_then_waits_for_review() -> None:
    session, campaign_id = _setup()
    lead = session.exec(select(Member).where(Member.role == MemberRole.LEAD)).first()

    # Opt the ideation step into a review gate (default is now ai_auto).
    ideation_task = _task(session, campaign_id, TaskKind.IDEATION)
    ideation_task.execution_mode = ExecutionMode.AI_DRAFT_HUMAN_REVIEW
    session.add(ideation_task)
    session.commit()

    ran = asyncio.run(_runner(session).run_ready_tasks(campaign_id))

    ideation = _task(session, campaign_id, TaskKind.IDEATION)
    planning = _task(session, campaign_id, TaskKind.PLANNING)

    assert ran == [ideation.id]
    # AI drafted ideation; it now waits in the lead's review queue.
    assert ideation.status == TaskStatus.NEEDS_REVIEW
    assert ideation.output is not None
    assert ideation.assignee_id == lead.id
    # Planning stays blocked until ideation is approved.
    assert planning.status == TaskStatus.TODO
    assert len(session.exec(select(UsageEvent)).all()) == 1


def test_runner_auto_completes_the_pipeline_by_default() -> None:
    session, campaign_id = _setup()

    ran = asyncio.run(_runner(session).run_ready_tasks(campaign_id))

    ideation = _task(session, campaign_id, TaskKind.IDEATION)
    planning = _task(session, campaign_id, TaskKind.PLANNING)
    # Default is ai_auto: ideation, planning, and the two per-channel posts all run
    # in one pass — the Copywriter renders each post from the shared content core.
    assert len(ran) == 4
    assert ideation.status == TaskStatus.DONE
    assert planning.status == TaskStatus.DONE

    assets = session.exec(
        select(Task).where(
            Task.campaign_id == campaign_id, Task.kind == TaskKind.ASSET
        )
    ).all()
    # Each post is rendered from the shared core, then auto-completes with checks.
    for asset in assets:
        assert asset.status == TaskStatus.DONE
        assert asset.output is not None
        assert asset.output["channel"] == asset.params["channel"]
        assert "format" in asset.checks
        assert "brand" in asset.checks
        assert "consistency" in asset.checks

    claim_check = _task(session, campaign_id, TaskKind.CLAIM_CHECK)
    assert claim_check.output is not None
    assert "claim_checks" in claim_check.output


def test_posts_render_from_the_shared_core() -> None:
    session, campaign_id = _setup()
    asyncio.run(_runner(session).run_ready_tasks(campaign_id))

    planning = _task(session, campaign_id, TaskKind.PLANNING)
    core = planning.output["core_message"]
    assets = session.exec(
        select(Task).where(
            Task.campaign_id == campaign_id, Task.kind == TaskKind.ASSET
        )
    ).all()
    assert len(assets) == 2
    # Every channel's post carries the same campaign core -> cross-platform consistency.
    for asset in assets:
        assert core and core in asset.output["content"]


def test_run_task_error_reverts_to_todo_and_audits() -> None:
    session, campaign_id = _setup()
    runner = TaskRunner(session, client_for_provider=lambda provider: _FailingClient())

    with pytest.raises(LLMProviderError):
        asyncio.run(runner.run_ready_tasks(campaign_id))

    ideation = _task(session, campaign_id, TaskKind.IDEATION)
    # Reverted so a later run can retry; nothing half-written.
    assert ideation.status == TaskStatus.TODO
    assert ideation.output is None
    events = session.exec(
        select(TaskEvent).where(TaskEvent.task_id == ideation.id)
    ).all()
    assert any(e.payload and "error" in e.payload for e in events)


def test_campaign_template_reaches_the_ideation_agent() -> None:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    session = Session(engine)
    tenant = seed_testsprite(session)
    campaign = instantiate_campaign(
        session, tenant_id=tenant.id, name="Dev launch", brief=BRIEF,
        template="developer_tool",
    )
    asyncio.run(_runner(session).run_ready_tasks(campaign.id))

    ideation = _task(session, campaign.id, TaskKind.IDEATION)
    # The template flows through _build_context -> CampaignGenerationRequest into the
    # agent, so the mock takes its developer_tool branch (not the generic one).
    assert "Developer Trust Launch" in ideation.output["campaign_concept"]


def test_role_for_prefers_the_members_configured_role() -> None:
    asset_task = Task(tenant_id="t", campaign_id="c", kind=TaskKind.ASSET, title="x")
    # No member / no configured role -> the kind's default agent.
    assert role_for(asset_task, None) == "copywriter"
    plain = Member(tenant_id="t", kind=MemberKind.AI, display_name="plain")
    assert role_for(asset_task, plain) == "copywriter"
    # A configured role on the member wins, so a kind can be pointed at a custom agent.
    custom = Member(
        tenant_id="t",
        kind=MemberKind.AI,
        display_name="custom",
        agent_config={"role": "designer", "provider": "mock"},
    )
    assert role_for(asset_task, custom) == "designer"


def test_runner_self_corrects_a_failed_asset_check() -> None:
    session, campaign_id = _setup()
    client = _SelfCorrectingClient()
    runner = TaskRunner(session, client_for_provider=lambda provider: client)
    asyncio.run(runner.run_ready_tasks(campaign_id))

    assets = session.exec(
        select(Task).where(Task.campaign_id == campaign_id, Task.kind == TaskKind.ASSET)
    ).all()
    assert len(assets) == 2
    for asset in assets:
        # The forbidden word from the first draft was corrected out before completing.
        assert asset.status == TaskStatus.DONE
        assert asset.checks["brand"] == []
        assert "magic" not in (asset.output["content"] or "").lower()

    events = session.exec(
        select(TaskEvent).where(TaskEvent.type == TaskEventType.SELF_CORRECTED)
    ).all()
    assert len(events) == 2  # one corrective pass per asset
    assert all(e.payload["passes"] == 1 and e.payload["remaining_issues"] == 0 for e in events)

    # Each retry is a real LLM call, so the writer's calls are metered: first
    # render + one retry (the auditor's calls are metered separately).
    for asset in assets:
        usage = session.exec(
            select(UsageEvent).where(
                UsageEvent.task_id == asset.id,
                UsageEvent.member_id == asset.assignee_id,
            )
        ).all()
        assert len(usage) == 2


def test_self_correction_caps_passes_and_keeps_least_bad() -> None:
    session, campaign_id = _setup()
    runner = TaskRunner(
        session, client_for_provider=lambda provider: _PersistentlyDirtyClient()
    )
    asyncio.run(runner.run_ready_tasks(campaign_id))

    asset = session.exec(
        select(Task).where(Task.campaign_id == campaign_id, Task.kind == TaskKind.ASSET)
    ).first()
    # Checks are advisory: an un-fixable draft still completes, with the issue surfaced.
    assert asset.status == TaskStatus.DONE
    assert any(i["code"] == "forbidden_word" for i in asset.checks["brand"])

    event = session.exec(
        select(TaskEvent).where(
            TaskEvent.task_id == asset.id,
            TaskEvent.type == TaskEventType.SELF_CORRECTED,
        )
    ).first()
    # It tried the capped number of passes, then gave up — no infinite loop.
    assert event.payload["passes"] == 2
    assert event.payload["remaining_issues"] >= 1


def test_auditor_runs_on_every_post_and_is_metered() -> None:
    session, campaign_id = _setup()
    asyncio.run(_runner(session).run_ready_tasks(campaign_id))
    auditor = _auditor(session)

    assets = session.exec(
        select(Task).where(Task.campaign_id == campaign_id, Task.kind == TaskKind.ASSET)
    ).all()
    assert len(assets) == 2
    for asset in assets:
        # The auditor verdict is surfaced alongside the deterministic checks; the
        # mock auditor approves clean content.
        assert asset.checks["audit"] == []
        # The audit call is metered against the auditor member (not the writer).
        audit_usage = session.exec(
            select(UsageEvent).where(
                UsageEvent.task_id == asset.id, UsageEvent.member_id == auditor.id
            )
        ).all()
        assert len(audit_usage) >= 1


def test_auditor_flag_drives_a_self_correction_pass() -> None:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    session = Session(engine)
    tenant = seed_testsprite(session)

    # Point the auditor at its own provider and route only that to the flagging client,
    # so the writer (mock) renders deterministically-clean copy.
    auditor = _auditor(session)
    auditor.agent_config = {**auditor.agent_config, "provider": "audit"}
    session.add(auditor)
    session.commit()

    flagging = _FlaggingAuditorClient()
    runner = TaskRunner(
        session,
        client_for_provider=lambda provider: flagging if provider == "audit" else MockLLMClient(),
    )
    campaign = instantiate_campaign(
        session, tenant_id=tenant.id, name="Solo",
        brief={**BRIEF, "selected_channels": ["LinkedIn"]},
    )
    asyncio.run(runner.run_ready_tasks(campaign.id))

    asset = _task(session, campaign.id, TaskKind.ASSET)
    # Deterministic checks were clean; the auditor's first verdict forced a rewrite,
    # and it approved the second draft.
    assert asset.status == TaskStatus.DONE
    assert asset.checks["brand"] == [] and asset.checks["audit"] == []
    event = session.exec(
        select(TaskEvent).where(
            TaskEvent.task_id == asset.id,
            TaskEvent.type == TaskEventType.SELF_CORRECTED,
        )
    ).first()
    assert event is not None and event.payload["passes"] == 1
    # Cross-model: the auditor billed its own (different) provider.
    audit_usage = session.exec(
        select(UsageEvent).where(
            UsageEvent.task_id == asset.id, UsageEvent.member_id == auditor.id
        )
    ).all()
    assert audit_usage and all(u.provider == "audit" for u in audit_usage)


def test_posts_carry_a_visual_when_enabled() -> None:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    session = Session(engine)
    tenant = seed_testsprite(session)
    campaign = instantiate_campaign(
        session, tenant_id=tenant.id, name="Visual launch", brief=BRIEF, with_visuals=True
    )
    asyncio.run(_runner(session).run_ready_tasks(campaign.id))

    # No separate visual tasks — the visual is part of each post (one deliverable).
    assert (
        session.exec(
            select(Task).where(
                Task.campaign_id == campaign.id, Task.kind == TaskKind.VISUAL
            )
        ).all()
        == []
    )
    assets = session.exec(
        select(Task).where(Task.campaign_id == campaign.id, Task.kind == TaskKind.ASSET)
    ).all()
    assert len(assets) == 2  # LinkedIn, Email
    for asset in assets:
        assert asset.status == TaskStatus.DONE
        visual = asset.output["visual"]
        assert visual["image_ref"].startswith("mock://image/")
        assert visual["prompt"] and visual["alt_text"]
        # The Designer's visual was critiqued; the mock judges it on-brand.
        assert asset.checks["brand_fit"] == []


class _FlaggingVisionProvider(VisionProvider):
    """Judges the first visual off-brand, then on-brand — so the critic drives a
    self-correction pass even though the writer/media are clean."""

    def __init__(self) -> None:
        self.critiques = 0

    async def understand(self, *, media_ref) -> MediaUnderstanding:
        return MediaUnderstanding(summary="mock")

    async def critique(self, *, media_ref, campaign_text, brand=None) -> MediaCritique:
        self.critiques += 1
        if self.critiques == 1:
            return MediaCritique(
                on_brand=False, issues=["Palette reads off-brand; use the brand greens."]
            )
        return MediaCritique(on_brand=True, issues=[])


def test_visual_critique_surfaces_on_the_post() -> None:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    session = Session(engine)
    tenant = seed_testsprite(session)

    vision = _FlaggingVisionProvider()
    runner = TaskRunner(
        session,
        client_for_provider=lambda provider: MockLLMClient(),
        vision_for_name=lambda name: vision,
    )
    campaign = instantiate_campaign(
        session, tenant_id=tenant.id, name="Solo visual",
        brief={**BRIEF, "selected_channels": ["LinkedIn"]}, with_visuals=True,
    )
    asyncio.run(runner.run_ready_tasks(campaign.id))

    asset = _task(session, campaign.id, TaskKind.ASSET)
    # The Designer attached a visual; the VLM-judge flagged it off-brand, surfaced as
    # the post's brand_fit check (advisory — visual gen is decoupled from the copy loop).
    assert asset.output["visual"]["image_ref"]
    assert asset.checks["brand_fit"]
    assert any("off-brand" in i["detail"] for i in asset.checks["brand_fit"])


def test_fan_out_preserves_human_edits_on_replay() -> None:
    session, campaign_id = _setup()
    for kind in (TaskKind.IDEATION, TaskKind.PLANNING):
        task = _task(session, campaign_id, kind)
        task.execution_mode = ExecutionMode.AI_AUTO
        session.add(task)
    session.commit()
    asyncio.run(_runner(session).run_ready_tasks(campaign_id))

    asset = session.exec(
        select(Task).where(
            Task.campaign_id == campaign_id, Task.kind == TaskKind.ASSET
        )
    ).first()
    asset.output = {**asset.output, "title": "HUMAN EDITED"}
    session.add(asset)
    session.commit()

    # Replaying fan-out (e.g. a re-approval) must not clobber the human edit.
    planning = _task(session, campaign_id, TaskKind.PLANNING)
    fan_out_from_plan(session, planning)
    session.commit()

    session.refresh(asset)
    assert asset.output["title"] == "HUMAN EDITED"
