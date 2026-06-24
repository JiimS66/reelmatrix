import asyncio

import pytest
from sqlmodel import Session, select

from core.db.engine import create_db_engine, init_db
from core.llm.base import BaseLLMClient, LLMProviderError
from core.db.models import (
    ExecutionMode,
    Member,
    MemberRole,
    Task,
    TaskEvent,
    TaskKind,
    TaskStatus,
    UsageEvent,
)
from core.db.seed import seed_testsprite
from core.llm.mock_client import MockLLMClient
from core.workflows.campaign_instantiation import instantiate_campaign
from core.workflows.task_runner import TaskRunner, fan_out_from_plan


class _FailingClient(BaseLLMClient):
    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        raise LLMProviderError("boom")

    async def generate_structured(self, *, system_prompt, user_prompt, response_model):
        raise LLMProviderError("boom")

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
    # Default is ai_auto: ideation and planning both run to done in one pass.
    assert len(ran) == 2
    assert ideation.status == TaskStatus.DONE
    assert planning.status == TaskStatus.DONE

    assets = session.exec(
        select(Task).where(
            Task.campaign_id == campaign_id, Task.kind == TaskKind.ASSET
        )
    ).all()
    # Planning fanned out into the asset tasks, which auto-complete with checks.
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
