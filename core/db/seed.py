"""Idempotent seed for the TestSprite demo tenant.

Run as a script against the configured database::

    uv run python -m core.db.seed

Re-running is safe: rows are matched by natural keys (tenant name, user email,
member display name) and reused instead of duplicated.
"""

from typing import Optional

from sqlmodel import Session, select

from core.db.engine import get_engine, init_db
from core.db.models import (
    BrandProfile,
    BrandTerm,
    ChannelProfile,
    Member,
    MemberKind,
    MemberRole,
    TaskKind,
    Tenant,
    User,
)

TENANT_NAME = "TestSprite"

BRAND = {
    "voice": "Technical, direct, evidence-led, developer-trust-first",
    "tone_rules": [
        "Lead with the verification gap",
        "Prefer technical proof over hype",
    ],
    "forbidden_words": [
        "bug-free",
        "magic",
        "fully autonomous without review",
        "set and forget",
    ],
    "approved_phrases": ["agentic testing", "verification loop"],
    "proof_points": [
        {
            "claim": "TestSprite announced $6.7M in seed funding",
            "source": "https://www.geekwire.com/",
        }
    ],
    "segments": [
        {
            "name": "Engineering leaders",
            "description": "VPEng/Eng managers adopting coding agents at scale",
            "profile": "B2B · Series-A/B SaaS · 50–250 eng · VP Eng / Eng Manager",
            "platforms": ["LinkedIn", "Email"],
            "pain_points": [
                "AI-generated code ships without a verification gate",
                "No way to prove agent-written changes still work",
            ],
            "value_props": [
                "A verification loop your agents can actually run",
                "Ship AI code with proof, not hope",
            ],
            "objections": ["We already have CI", "Another tool to babysit"],
            "reach_tactics": ["Thought-leadership on code safety", "Outbound to eng leads"],
        },
        {
            "name": "AI-native developers",
            "description": "Builders using Cursor/Claude Code/Codex daily",
            "profile": "IC developers · early adopters · agentic coding workflows",
            "platforms": ["X / Twitter", "Community", "Landing Page"],
            "pain_points": [
                "Unit tests miss real browser/API failures",
                "Regressions slip through agent loops",
            ],
            "value_props": [
                "Catch the failures unit tests can't",
                "A QA loop your coding agent runs itself",
            ],
            "objections": ["I'll just write more tests", "Setup looks heavy"],
            "reach_tactics": ["Technical threads", "Live-demo quickstarts"],
        },
    ],
}

# The default TestSprite org. ``handles_kinds`` is what routes work to each member;
# ``reports_to`` (resolved from display_name below) wires the org chart under the lead.
HUMANS = [
    {
        "email": "adam@testsprite.com",
        "display_name": "Adam (Lead)",
        "role": MemberRole.LEAD,
        "job_description": (
            "Marketing lead — owns strategy, reviews the AI team's work, and runs "
            "the human-only claim check."
        ),
        "handles_kinds": [TaskKind.CLAIM_CHECK],
        "reports_to": None,
    },
    {
        "email": "sam@testsprite.com",
        "display_name": "Sam (Writer)",
        "role": MemberRole.MEMBER,
        "job_description": "Staff writer — drafts posts the lead wants a human to craft.",
        "handles_kinds": [],
        "reports_to": "Adam (Lead)",
    },
]

AI_AGENTS = [
    {
        "display_name": "Ideation bot",
        "agent_kind": "ideation",
        "agent_role": "ideation",
        "job_description": "Sharpens the concept, core message, and creative angles.",
        "handles_kinds": [TaskKind.IDEATION],
        "reports_to": "Adam (Lead)",
    },
    {
        "display_name": "Planning bot",
        "agent_kind": "planning",
        "agent_role": "planning",
        "job_description": "Turns the approved concept into a multi-channel plan.",
        "handles_kinds": [TaskKind.PLANNING],
        "reports_to": "Adam (Lead)",
    },
    {
        "display_name": "Asset writer",
        "agent_kind": "asset",
        "agent_role": "copywriter",
        "job_description": "Renders each platform's post from the shared content core.",
        "handles_kinds": [TaskKind.ASSET],
        "reports_to": "Adam (Lead)",
    },
    {
        # Invoked by the runner on each rendered post (not task-assigned), so it owns
        # no task kinds. Production should point this at a DIFFERENT model family than
        # the writer so their errors decorrelate; the demo uses the mock provider.
        "display_name": "Content auditor",
        "agent_kind": "auditor",
        "agent_role": "auditor",
        "job_description": "Independently judges each AI-drafted post (LLM-as-judge).",
        "handles_kinds": [],
        "reports_to": "Adam (Lead)",
    },
    {
        # Service member (not task-assigned): the runner invokes the Designer to
        # attach a visual to each post during the asset render.
        "display_name": "Designer",
        "agent_kind": "visual",
        "agent_role": "designer",
        "job_description": "Attaches each post's visual from the copy + brand (image model).",
        "handles_kinds": [],
        "reports_to": "Adam (Lead)",
    },
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
    job_description: str = "",
    reports_to: Optional[str] = None,
    handles_kinds: Optional[list[str]] = None,
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
        job_description=job_description,
        reports_to=reports_to,
        handles_kinds=handles_kinds or [],
        user_id=user_id,
        agent_config=agent_config,
    )
    session.add(member)
    return member


# The platforms this tenant actually operates — grounds per-platform task
# splitting. Inactive rows document a channel exists but keep the AI off it.
CHANNELS = [
    {
        "platform": "LinkedIn",
        "handle": "linkedin.com/company/testsprite",
        "audience_note": "Eng leaders + founders; responds to evidence-led narrative posts",
        "cadence": "2x/week",
        "active": True,
    },
    {
        "platform": "X / Twitter",
        "handle": "@testsprite",
        "audience_note": "AI-native devs; threads with runnable examples do best",
        "cadence": "3x/week",
        "active": True,
    },
    {
        "platform": "Email",
        "handle": "changelog@testsprite.com",
        "audience_note": "Signed-up developers + trial leads; plain-text tone",
        "cadence": "1x/week",
        "active": True,
    },
    {
        "platform": "Blog",
        "handle": "testsprite.com/blog",
        "audience_note": "SEO + deep-dive readers; technical launch posts",
        "cadence": "2x/month",
        "active": True,
    },
    {
        "platform": "Community",
        "handle": "discord.gg/testsprite",
        "audience_note": "Power users; launch notes and honest changelogs",
        "cadence": "as it ships",
        "active": True,
    },
    {
        "platform": "GitHub / CLI",
        "handle": "github.com/testsprite",
        "audience_note": "CLI users; quickstart copy, zero marketing tone",
        "cadence": "per release",
        "active": True,
    },
    {
        "platform": "Landing Page",
        "handle": "testsprite.com",
        "audience_note": "Hero + section copy; coordinate with the web team",
        "cadence": "per launch",
        "active": True,
    },
]


def _get_or_create_channels(session: Session, tenant_id: str) -> None:
    existing = {
        profile.platform
        for profile in session.exec(
            select(ChannelProfile).where(ChannelProfile.tenant_id == tenant_id)
        ).all()
    }
    for spec in CHANNELS:
        if spec["platform"] in existing:
            continue
        session.add(ChannelProfile(tenant_id=tenant_id, **spec))


# Typed terminology (richer than forbidden_words): avoid terms carry a preferred swap.
TERMS = [
    {"term": "utilize", "term_type": "avoid", "replacement": "use"},
    {"term": "leverage", "term_type": "avoid", "replacement": "use"},
    {"term": "synergy", "term_type": "avoid", "replacement": None},
    {"term": "guarantee", "term_type": "use_carefully", "replacement": None},
    {"term": "agentic testing", "term_type": "approved", "replacement": None},
]


def _get_or_create_brand_terms(session: Session, tenant_id: str) -> None:
    existing = {
        term.term
        for term in session.exec(
            select(BrandTerm).where(BrandTerm.tenant_id == tenant_id)
        ).all()
    }
    for spec in TERMS:
        if spec["term"] in existing:
            continue
        session.add(
            BrandTerm(
                tenant_id=tenant_id,
                term=spec["term"],
                term_type=spec["term_type"],
                replacement=spec["replacement"],
            )
        )


def _get_or_create_brand_profile(session: Session, tenant_id: str) -> BrandProfile:
    existing = session.exec(
        select(BrandProfile).where(BrandProfile.tenant_id == tenant_id)
    ).first()
    if existing is not None:
        return existing
    profile = BrandProfile(
        tenant_id=tenant_id,
        voice=BRAND["voice"],
        tone_rules=BRAND["tone_rules"],
        forbidden_words=BRAND["forbidden_words"],
        approved_phrases=BRAND["approved_phrases"],
        proof_points=BRAND["proof_points"],
        segments=BRAND["segments"],
    )
    session.add(profile)
    return profile


def seed_testsprite(session: Session) -> Tenant:
    """Create (or reuse) the TestSprite tenant, its humans, AI agents, and brand."""
    tenant = _get_or_create_tenant(session, TENANT_NAME)

    # display_name -> member id, so reports_to (configured by name above) can be wired
    # once the manager exists. The lead has no manager and is created first.
    by_name: dict[str, str] = {}

    def _kinds(spec: dict) -> list[str]:
        return [kind.value for kind in spec.get("handles_kinds", [])]

    for human in HUMANS:
        user = _get_or_create_user(session, human["email"], human["display_name"])
        session.flush()  # ensure user.id is available for the member FK
        member = _get_or_create_member(
            session,
            tenant_id=tenant.id,
            kind=MemberKind.HUMAN,
            role=human["role"],
            display_name=human["display_name"],
            job_description=human["job_description"],
            reports_to=by_name.get(human["reports_to"]) if human["reports_to"] else None,
            handles_kinds=_kinds(human),
            user_id=user.id,
        )
        by_name[member.display_name] = member.id

    # Cross-model audit needs the judge on a DIFFERENT family than the writer.
    # When a SiliconFlow-slot key is configured (SiliconFlow itself, or Bailian's
    # OpenAI-compatible DeepSeek endpoint via SILICONFLOW_BASE_URL), the seeded
    # Auditor is pinned to it automatically — otherwise every fresh reseed would
    # silently drop the decorrelation until someone remembered the Team tab.
    from configs.settings import get_settings

    auditor_provider = (
        "siliconflow" if (get_settings().siliconflow_api_key or "").strip() else None
    )

    for agent in AI_AGENTS:
        config = {
            "agent_kind": agent["agent_kind"],
            "role": agent["agent_role"],
        }
        # Other AI employees follow the deployment's LLM_PROVIDER unless the org
        # explicitly reconfigures them (Team tab).
        if agent["agent_role"] == "auditor" and auditor_provider:
            config["provider"] = auditor_provider
        member = _get_or_create_member(
            session,
            tenant_id=tenant.id,
            kind=MemberKind.AI,
            role=MemberRole.MEMBER,
            display_name=agent["display_name"],
            job_description=agent["job_description"],
            reports_to=by_name.get(agent["reports_to"]) if agent["reports_to"] else None,
            handles_kinds=_kinds(agent),
            agent_config=config,
        )
        by_name[member.display_name] = member.id

    session.flush()  # tenant.id is set, but ensure rows exist before the brand FK
    _get_or_create_brand_profile(session, tenant.id)
    _get_or_create_brand_terms(session, tenant.id)
    _get_or_create_channels(session, tenant.id)

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
