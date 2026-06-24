from sqlmodel import Session, select

from core.db.engine import create_db_engine, init_db
from core.db.models import (
    BrandProfile,
    Member,
    MemberKind,
    MemberRole,
    TaskKind,
    Tenant,
    User,
)
from core.db.seed import seed_testsprite


def _session() -> Session:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    return Session(engine)


def test_seed_creates_expected_team() -> None:
    with _session() as session:
        tenant = seed_testsprite(session)

        members = session.exec(
            select(Member).where(Member.tenant_id == tenant.id)
        ).all()
        humans = [m for m in members if m.kind == MemberKind.HUMAN]
        ai_agents = [m for m in members if m.kind == MemberKind.AI]

        assert len(members) == 5
        assert len(humans) == 2
        assert len(ai_agents) == 3
        assert any(m.role == MemberRole.LEAD for m in humans)
        assert all(m.agent_config and m.agent_config["agent_kind"] for m in ai_agents)


def test_seed_wires_the_org_config() -> None:
    with _session() as session:
        tenant = seed_testsprite(session)
        by_name = {
            m.display_name: m
            for m in session.exec(
                select(Member).where(Member.tenant_id == tenant.id)
            ).all()
        }

        lead = by_name["Adam (Lead)"]
        # handles_kinds is what routes work; each AI agent owns one kind, the lead
        # owns the human-only claim check.
        assert lead.handles_kinds == [TaskKind.CLAIM_CHECK.value]
        assert by_name["Ideation bot"].handles_kinds == [TaskKind.IDEATION.value]
        assert by_name["Planning bot"].handles_kinds == [TaskKind.PLANNING.value]
        assert by_name["Asset writer"].handles_kinds == [TaskKind.ASSET.value]

        # AI members name the agent that runs their work; the org reports to the lead.
        assert by_name["Asset writer"].agent_config["role"] == "copywriter"
        assert lead.reports_to is None
        for name in ("Sam (Writer)", "Ideation bot", "Asset writer"):
            assert by_name[name].reports_to == lead.id
            assert by_name[name].job_description


def test_seed_creates_brand_profile() -> None:
    with _session() as session:
        tenant = seed_testsprite(session)
        profile = session.exec(
            select(BrandProfile).where(BrandProfile.tenant_id == tenant.id)
        ).first()
        assert profile is not None
        assert "bug-free" in profile.forbidden_words
        assert profile.voice


def test_seed_is_idempotent() -> None:
    with _session() as session:
        seed_testsprite(session)
        seed_testsprite(session)

        assert len(session.exec(select(Tenant)).all()) == 1
        assert len(session.exec(select(User)).all()) == 2
        assert len(session.exec(select(Member)).all()) == 5
        assert len(session.exec(select(BrandProfile)).all()) == 1
