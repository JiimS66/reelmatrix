"""Instantiate a campaign brief into a fixed task template.

This is the task-based successor to ``CampaignWorkflow``: instead of running
ideation then planning synchronously, it persists a campaign and a small graph
of tasks (ideation -> planning -> assets + claim check) that humans and AI
members work through asynchronously. The old single-shot workflow is kept for
the existing /generate endpoint.
"""

from typing import Optional

from sqlmodel import Session, select

from core.db.models import (
    AttributeOutcome,
    BrandProfile,
    Campaign,
    ChannelProfile,
    ExecutionMode,
    Member,
    MemberKind,
    MemberRole,
    Task,
    TaskKind,
)
from core.workflows.scheduler import generate_schedule

DEFAULT_CHANNELS = ["LinkedIn", "Email", "Blog"]


def active_channels(
    session: Session, tenant_id: str, requested: list[str]
) -> list[str]:
    """Filter requested channels to the tenant's ACTIVE ChannelProfiles.

    This grounds per-platform task splitting in the platforms the tenant
    actually operates. A tenant with no channel registry keeps the requested
    list (backwards compatible); a registry with no overlap falls back to every
    active platform rather than producing an empty campaign.
    """
    profiles = session.exec(
        select(ChannelProfile).where(ChannelProfile.tenant_id == tenant_id)
    ).all()
    if not profiles:
        return requested
    active = [p.platform for p in profiles if p.active]
    by_name = {p.lower(): p for p in active}
    kept = [by_name[c.strip().lower()] for c in requested if c.strip().lower() in by_name]
    return kept or active


def _seg_params(seg: dict, idx: int) -> dict:
    """{segment, pain_point} for a post, rotating the pain point by post index so
    different posts for a segment lead with different pains (not always the first)."""
    if not seg:
        return {}
    pains = seg.get("pain_points") or []
    return {
        "segment": seg.get("name", ""),
        "pain_point": pains[idx % len(pains)] if pains else "",
    }


def _pick_segment(channel: str, segments: list[dict]) -> dict:
    """The targeted segment whose platforms include this channel (else the first)."""
    if not segments:
        return {}
    ch = (channel or "").strip().lower()
    return next(
        (
            s
            for s in segments
            if any(ch == str(p).strip().lower() for p in (s.get("platforms") or []))
        ),
        segments[0],
    )


_FUNNEL_STAGES = ("TOFU", "MOFU", "BOFU")
_FUNNEL_ACTION = {
    "TOFU": "build awareness — earn a click/follow",
    "MOFU": "earn consideration — drive a signup/trial",
    "BOFU": "drive conversion — get a paid start",
}


def assign_segment(channel: str, segments: list[dict], idx: int = 0) -> dict:
    """Reach mode: route a channel-post to one segment (by platform match) with a
    rotated pain point. Returns {} when the brand has no segments."""
    return _seg_params(_pick_segment(channel, segments), idx)


def targeted_segments(session: Session, tenant_id: str, brief: dict) -> list[dict]:
    """The brand's ICP segments this campaign targets (brief['target_segments']),
    or all of them when the brief doesn't narrow it."""
    brand = session.exec(
        select(BrandProfile).where(BrandProfile.tenant_id == tenant_id)
    ).first()
    segments = (brand.segments if brand is not None else []) or []
    names = brief.get("target_segments") or []
    return [s for s in segments if s.get("name") in names] or segments


# A channel earns a bonus post only on real evidence: at least this many
# measured posts, and a conversion rate ≥1.5× the cross-channel average.
_BOOST_MIN_POSTS = 3
_BOOST_MIN_RATIO = 1.5


def flywheel_channel_boost(
    session: Session, tenant_id: str, channels: list[str]
) -> Optional[tuple[str, str]]:
    """(channel, reason) for the campaign's proven-best channel, or None.

    This is where the learning loop first REALLOCATES work instead of just
    reporting: a channel the flywheel has proven out gets one extra post, and
    the reason rides on the task so the human sees why."""
    rows = session.exec(
        select(AttributeOutcome).where(
            AttributeOutcome.tenant_id == tenant_id,
            AttributeOutcome.segment == "",
            AttributeOutcome.channel != "",
        )
    ).all()
    stats: dict[str, dict[str, int]] = {}
    for row in rows:
        if row.channel not in channels:
            continue
        agg = stats.setdefault(row.channel, {"impressions": 0, "conversions": 0, "n": 0})
        agg["impressions"] += row.impressions
        agg["conversions"] += row.conversions
        agg["n"] = max(agg["n"], row.n_posts)
    measured = {
        ch: agg["conversions"] / agg["impressions"]
        for ch, agg in stats.items()
        if agg["impressions"] > 0 and agg["n"] >= _BOOST_MIN_POSTS
    }
    if len(measured) < 2:
        return None
    best_channel = max(measured, key=lambda ch: measured[ch])
    others = [cvr for ch, cvr in measured.items() if ch != best_channel]
    average = sum(others) / len(others)
    if average <= 0 or measured[best_channel] / average < _BOOST_MIN_RATIO:
        return None
    return (
        best_channel,
        f"Flywheel: {best_channel} converts at {measured[best_channel]:.1%} vs "
        f"{average:.1%} elsewhere (n≥{_BOOST_MIN_POSTS} posts) — one extra post allocated.",
    )


def route_assignees(session: Session, tenant_id: str) -> dict[str, Optional[str]]:
    """Map each task kind to the member configured to own it (``handles_kinds``).

    This is the per-tenant org routing: whoever declares a kind handles it, so a
    tenant reconfigures who does what without touching this code. When two members
    declare the same kind the earliest-created wins (a stable default). The claim
    check falls back to the lead so fact-checking always reaches a human even in an
    under-configured org.
    """
    members = list(
        session.exec(
            select(Member)
            .where(Member.tenant_id == tenant_id)
            .order_by(Member.created_at)
        ).all()
    )
    routes: dict[str, Optional[str]] = {}
    for member in members:
        for kind in member.handles_kinds or []:
            routes.setdefault(kind, member.id)

    if routes.get(TaskKind.CLAIM_CHECK.value) is None:
        lead = next(
            (
                m
                for m in members
                if m.kind == MemberKind.HUMAN and m.role == MemberRole.LEAD
            ),
            None,
        )
        if lead is not None:
            routes[TaskKind.CLAIM_CHECK.value] = lead.id
    return routes


def instantiate_campaign(
    session: Session,
    *,
    tenant_id: str,
    name: str,
    brief: dict,
    template: str = "general",
    created_by: Optional[str] = None,
    event_name: Optional[str] = None,
    event_date: Optional[str] = None,
    asset_mode: ExecutionMode = ExecutionMode.AI_AUTO,
    with_visuals: bool = False,
) -> Campaign:
    """Create a campaign plus its fixed task graph, returning the campaign.

    Tasks are created but not run; a task runner executes AI tasks once their
    dependencies are satisfied.
    """
    # Persist whether posts carry a visual on the brief, so the runner's Designer
    # sub-step (visual is now part of the post, not a separate task) can read it.
    brief = {**brief, "with_visuals": with_visuals}
    campaign = Campaign(
        tenant_id=tenant_id,
        name=name,
        template=template,
        brief=brief,
        created_by=created_by,
        event_name=event_name,
        event_date=event_date,
    )
    session.add(campaign)

    routes = route_assignees(session, tenant_id)

    ideation = Task(
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        kind=TaskKind.IDEATION,
        title="Ideation",
        execution_mode=ExecutionMode.AI_AUTO,
        assignee_id=routes.get(TaskKind.IDEATION.value),
        sequence=1,
    )
    session.add(ideation)

    planning = Task(
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        kind=TaskKind.PLANNING,
        title="Campaign plan",
        execution_mode=ExecutionMode.AI_AUTO,
        depends_on=[ideation.id],
        assignee_id=routes.get(TaskKind.PLANNING.value),
        sequence=2,
    )
    session.add(planning)

    channels = active_channels(
        session, tenant_id, brief.get("selected_channels") or DEFAULT_CHANNELS
    )
    segments = targeted_segments(session, tenant_id, brief)
    # Reach mode (default): one post per channel, routed to one segment.
    # Tailored mode (brief["tailored"]): fan out one post per (channel × segment) so
    # every targeted segment gets its own tailored post (Tofu-style personalization).
    tailored = bool(brief.get("tailored")) and bool(segments)
    post_specs: list[tuple[str, dict]] = []
    if tailored:
        idx = 0
        for channel in channels:
            for seg in segments:
                post_specs.append((channel, _seg_params(seg, idx)))
                idx += 1
    else:
        post_specs = [
            (channel, assign_segment(channel, segments, i))
            for i, channel in enumerate(channels)
        ]

    # Evidence-based reallocation: the flywheel's proven-best channel earns one
    # extra post, with the reason attached so the human sees why.
    boost = flywheel_channel_boost(session, tenant_id, channels)
    if boost is not None:
        boost_channel, boost_reason = boost
        post_specs.append(
            (
                boost_channel,
                {
                    **assign_segment(boost_channel, segments, len(post_specs)),
                    "flywheel_boost": boost_reason,
                },
            )
        )

    sequence = 3
    for i, (channel, seg_params) in enumerate(post_specs):
        seg_name = seg_params.get("segment", "")
        funnel = _FUNNEL_STAGES[i % len(_FUNNEL_STAGES)]  # spread coverage across the funnel
        session.add(
            Task(
                tenant_id=tenant_id,
                campaign_id=campaign.id,
                kind=TaskKind.ASSET,
                title=f"{channel} post" + (f" — {seg_name}" if tailored and seg_name else ""),
                execution_mode=asset_mode,
                depends_on=[planning.id],
                assignee_id=routes.get(TaskKind.ASSET.value),
                params={
                    "channel": channel,
                    "funnel_stage": funnel,
                    "desired_action": _FUNNEL_ACTION[funnel],
                    **seg_params,
                },
                sequence=sequence,
            )
        )
        sequence += 1

    # Visuals are no longer separate tasks — the Designer attaches one to each post
    # during the asset render (see TaskRunner._attach_visual), so a post is one
    # deliverable carrying both copy and image/video.

    # Fact-checking is a human-only task; route_assignees guarantees a lead fallback.
    session.add(
        Task(
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            kind=TaskKind.CLAIM_CHECK,
            title="Claim check",
            depends_on=[planning.id],
            execution_mode=ExecutionMode.HUMAN_ONLY,
            assignee_id=routes.get(TaskKind.CLAIM_CHECK.value),
            sequence=sequence,
        )
    )

    generate_schedule(session, campaign)
    session.commit()
    return campaign
