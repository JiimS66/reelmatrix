"""Idempotent seed for the TestSprite demo tenant.

Run as a script against the configured database::

    uv run python -m core.db.seed

Re-running is safe: rows are matched by natural keys (tenant name, user email,
member display name) and reused instead of duplicated.
"""

from typing import Optional

from sqlmodel import Session, select

from core.db.engine import get_engine, init_db
from core.db.models import Member, MemberKind, MemberRole, Tenant, User

TENANT_NAME = "TestSprite"

HUMANS = [
    {"email": "mia@testsprite.com", "display_name": "Mia (Lead)", "role": MemberRole.LEAD},
    {"email": "sam@testsprite.com", "display_name": "Sam (Writer)", "role": MemberRole.MEMBER},
]

AI_AGENTS = [
    {"display_name": "Ideation bot", "agent_kind": "ideation"},
    {"display_name": "Planning bot", "agent_kind": "planning"},
    {"display_name": "Asset writer", "agent_kind": "asset"},
]


def _get_or_create_tenant(session: Session, name: str) -> Tenant:
    existing = session.exec(select(Tenant).where(Tenant.name == name)).first()
    if existing is not None:
        return existing
    tenant = Tenant(name=name)
    session.add(tenant)
    return tenant


def _get_or_create_user(session: Session, email: str, display_name: str) -> User:
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        return existing
    user = User(email=email, display_name=display_name)
    session.add(user)
    return user


def _get_or_create_member(
    session: Session,
    *,
    tenant_id: str,
    kind: MemberKind,
    role: MemberRole,
    display_name: str,
    user_id: Optional[str] = None,
    agent_config: Optional[dict] = None,
) -> Member:
    existing = session.exec(
        select(Member).where(
            Member.tenant_id == tenant_id,
            Member.display_name == display_name,
        )
    ).first()
    if existing is not None:
        return existing
    member = Member(
        tenant_id=tenant_id,
        kind=kind,
        role=role,
        display_name=display_name,
        user_id=user_id,
        agent_config=agent_config,
    )
    session.add(member)
    return member


def seed_testsprite(session: Session) -> Tenant:
    """Create (or reuse) the TestSprite tenant, its humans, and its AI agents."""
    tenant = _get_or_create_tenant(session, TENANT_NAME)

    for human in HUMANS:
        user = _get_or_create_user(session, human["email"], human["display_name"])
        session.flush()  # ensure user.id is available for the member FK
        _get_or_create_member(
            session,
            tenant_id=tenant.id,
            kind=MemberKind.HUMAN,
            role=human["role"],
            display_name=human["display_name"],
            user_id=user.id,
        )

    for agent in AI_AGENTS:
        _get_or_create_member(
            session,
            tenant_id=tenant.id,
            kind=MemberKind.AI,
            role=MemberRole.MEMBER,
            display_name=agent["display_name"],
            agent_config={"agent_kind": agent["agent_kind"], "provider": "mock"},
        )

    session.commit()
    return tenant


def main() -> None:
    init_db()
    with Session(get_engine()) as session:
        tenant = seed_testsprite(session)
        members = session.exec(
            select(Member).where(Member.tenant_id == tenant.id)
        ).all()
        print(f"Seeded tenant {tenant.name} ({tenant.id}) with {len(members)} members:")
        for member in members:
            print(f"  - {member.display_name} [{member.kind.value}/{member.role.value}]")


if __name__ == "__main__":
    main()
