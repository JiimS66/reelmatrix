from sqlmodel import Session, select

from core.db.engine import create_db_engine, init_db
from core.db.models import (
    ExecutionMode,
    Member,
    MemberKind,
    MemberRole,
    Task,
    TaskKind,
)
from core.db.seed import seed_testsprite
from core.workflows.campaign_instantiation import instantiate_campaign


def _seeded_session() -> Session:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    return Session(engine)


def test_instantiate_creates_expected_task_graph() -> None:
    with _seeded_session() as session:
        tenant = seed_testsprite(session)
        members = {
            m.display_name: m
            for m in session.exec(
                select(Member).where(Member.tenant_id == tenant.id)
            ).all()
        }

        campaign = instantiate_campaign(
            session,
            tenant_id=tenant.id,
            name="Launch",
            brief={"product_name": "TestSprite", "selected_channels": ["LinkedIn", "Blog"]},
            template="developer_tool",
        )

        tasks = session.exec(
            select(Task).where(Task.campaign_id == campaign.id)
        ).all()
        by_kind = {}
        for task in tasks:
            by_kind.setdefault(task.kind, []).append(task)

        # 1 ideation + 1 planning + 2 assets + 1 claim check = 5 tasks.
        assert len(tasks) == 5
        assert len(by_kind[TaskKind.ASSET]) == 2
        assert len(by_kind[TaskKind.IDEATION]) == 1

        ideation = by_kind[TaskKind.IDEATION][0]
        planning = by_kind[TaskKind.PLANNING][0]
        assert ideation.depends_on == []
        assert planning.depends_on == [ideation.id]

        # Assets depend on planning and carry their channel.
        channels = {t.params["channel"] for t in by_kind[TaskKind.ASSET]}
        assert channels == {"LinkedIn", "Blog"}
        for asset in by_kind[TaskKind.ASSET]:
            assert asset.depends_on == [planning.id]

        # Default assignees: AI agents on AI tasks, lead human on claim check.
        assert ideation.assignee_id == members["Ideation bot"].id
        assert planning.assignee_id == members["Planning bot"].id
        for asset in by_kind[TaskKind.ASSET]:
            assert asset.assignee_id == members["Asset writer"].id

        claim_check = by_kind[TaskKind.CLAIM_CHECK][0]
        assert claim_check.execution_mode == ExecutionMode.HUMAN_ONLY
        lead = members["Mia (Lead)"]
        assert lead.kind == MemberKind.HUMAN and lead.role == MemberRole.LEAD
        assert claim_check.assignee_id == lead.id


def test_instantiate_falls_back_to_default_channels() -> None:
    with _seeded_session() as session:
        tenant = seed_testsprite(session)
        campaign = instantiate_campaign(
            session,
            tenant_id=tenant.id,
            name="No channels",
            brief={"product_name": "TestSprite"},
        )
        assets = session.exec(
            select(Task).where(
                Task.campaign_id == campaign.id, Task.kind == TaskKind.ASSET
            )
        ).all()
        assert len(assets) == 3  # DEFAULT_CHANNELS
