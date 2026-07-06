from sqlmodel import Session, select

from core.db.engine import create_db_engine, init_db
from core.db.models import Milestone, Task, TaskKind
from core.db.seed import seed_testsprite
from core.workflows.campaign_instantiation import instantiate_campaign
from core.workflows.scheduler import generate_schedule

BRIEF = {
    "product_name": "TestSprite",
    "selected_channels": ["LinkedIn", "Email", "Landing Page"],
}


def _session() -> Session:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    return Session(engine)


def test_schedule_backplans_milestones_and_task_due_dates() -> None:
    with _session() as session:
        tenant = seed_testsprite(session)
        campaign = instantiate_campaign(
            session,
            tenant_id=tenant.id,
            name="Launch",
            brief=BRIEF,
            event_name="v2 release",
            event_date="2026-07-31",
        )

        milestones = {
            m.phase: m
            for m in session.exec(
                select(Milestone).where(Milestone.campaign_id == campaign.id)
            ).all()
        }
        assert len(milestones) == 5
        assert milestones["launch"].date == "2026-07-31"
        assert milestones["warmup"].date == "2026-07-10"  # T-21
        assert milestones["followup"].date == "2026-08-03"  # T+3

        by_kind: dict[TaskKind, list[Task]] = {}
        for task in session.exec(
            select(Task).where(Task.campaign_id == campaign.id)
        ).all():
            by_kind.setdefault(task.kind, []).append(task)

        ideation = by_kind[TaskKind.IDEATION][0]
        assert ideation.phase == "prep" and ideation.due_date == "2026-07-03"
        claim = by_kind[TaskKind.CLAIM_CHECK][0]
        assert claim.phase == "prelaunch" and claim.due_date == "2026-07-29"

        assert {t.phase for t in by_kind[TaskKind.ASSET]} == {
            "warmup",
            "buildup",
            "launch",
        }
        for asset in by_kind[TaskKind.ASSET]:
            assert asset.due_date == milestones[asset.phase].date


def test_schedule_is_idempotent_and_skips_without_event() -> None:
    with _session() as session:
        tenant = seed_testsprite(session)

        no_event = instantiate_campaign(
            session, tenant_id=tenant.id, name="No event", brief=BRIEF
        )
        assert generate_schedule(session, no_event) == []
        assert (
            len(
                session.exec(
                    select(Milestone).where(Milestone.campaign_id == no_event.id)
                ).all()
            )
            == 0
        )

        scheduled = instantiate_campaign(
            session,
            tenant_id=tenant.id,
            name="Event",
            brief=BRIEF,
            event_date="2026-07-31",
        )
        again = generate_schedule(session, scheduled)  # already scheduled
        assert len(again) == 5
        session.commit()
        assert (
            len(
                session.exec(
                    select(Milestone).where(Milestone.campaign_id == scheduled.id)
                ).all()
            )
            == 5
        )
