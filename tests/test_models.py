from sqlmodel import Session, select

from core.db.engine import create_db_engine, init_db
from core.db.models import (
    Campaign,
    Comment,
    ExecutionMode,
    Member,
    MemberKind,
    MemberRole,
    Task,
    TaskEvent,
    TaskEventType,
    TaskKind,
    TaskStatus,
    Tenant,
    UsageEvent,
    User,
)


def _session() -> Session:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    return Session(engine)


def test_all_tables_create_and_round_trip() -> None:
    with _session() as session:
        tenant = Tenant(name="TestSprite")
        session.add(tenant)
        session.commit()

        user = User(email="lead@testsprite.com", display_name="Lead")
        session.add(user)
        session.commit()

        lead = Member(
            tenant_id=tenant.id,
            kind=MemberKind.HUMAN,
            role=MemberRole.LEAD,
            display_name="Lead",
            user_id=user.id,
        )
        ai = Member(
            tenant_id=tenant.id,
            kind=MemberKind.AI,
            display_name="Ideation bot",
            agent_config={"agent_kind": "ideation", "provider": "mock"},
        )
        session.add(lead)
        session.add(ai)
        session.commit()

        campaign = Campaign(
            tenant_id=tenant.id,
            name="Launch",
            template="developer_tool",
            brief={"product_name": "TestSprite", "user_prompt": "go"},
            created_by=lead.id,
        )
        session.add(campaign)
        session.commit()

        ideation_task = Task(
            tenant_id=tenant.id,
            campaign_id=campaign.id,
            kind=TaskKind.IDEATION,
            title="Ideation",
            assignee_id=ai.id,
        )
        session.add(ideation_task)
        session.commit()

        asset_task = Task(
            tenant_id=tenant.id,
            campaign_id=campaign.id,
            kind=TaskKind.ASSET,
            title="LinkedIn post",
            execution_mode=ExecutionMode.HUMAN_ONLY,
            assignee_id=lead.id,
            depends_on=[ideation_task.id],
            sequence=2,
        )
        session.add(asset_task)
        session.commit()

        session.add(
            Comment(
                tenant_id=tenant.id,
                task_id=asset_task.id,
                author_id=lead.id,
                body="Tighten the hook.",
            )
        )
        session.add(
            TaskEvent(
                tenant_id=tenant.id,
                task_id=ideation_task.id,
                actor_id=ai.id,
                type=TaskEventType.AI_RUN,
                payload={"provider": "mock"},
            )
        )
        session.add(
            UsageEvent(
                tenant_id=tenant.id,
                task_id=ideation_task.id,
                member_id=ai.id,
                provider="mock",
                model="deterministic-mock",
                tokens=0,
            )
        )
        session.commit()

        # Enum round-trip.
        stored_ai = session.get(Member, ai.id)
        assert stored_ai is not None
        assert stored_ai.kind == MemberKind.AI
        assert stored_ai.role == MemberRole.MEMBER
        # JSON dict round-trip.
        assert stored_ai.agent_config == {"agent_kind": "ideation", "provider": "mock"}

        stored_task = session.get(Task, asset_task.id)
        assert stored_task is not None
        assert stored_task.status == TaskStatus.TODO
        assert stored_task.execution_mode == ExecutionMode.HUMAN_ONLY
        # JSON list round-trip.
        assert stored_task.depends_on == [ideation_task.id]

        # Tenant scoping query works.
        tasks = session.exec(
            select(Task).where(Task.tenant_id == tenant.id)
        ).all()
        assert {t.kind for t in tasks} == {TaskKind.IDEATION, TaskKind.ASSET}
