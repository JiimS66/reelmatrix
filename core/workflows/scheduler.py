"""Event-driven scheduler: back-plan a campaign from its event date.

Given an anchor event (e.g. a release on 2026-07-31), generate dated milestones
(warm-up -> build-up -> pre-launch -> launch -> follow-up) and assign due dates
to the campaign's tasks. Idempotent and does not commit — the caller owns the
transaction.
"""

from datetime import date, timedelta

from sqlmodel import Session, select

from core.db.models import Campaign, Milestone, Task, TaskKind

# (phase, name, offset_days_from_event, objective)
CADENCE: list[tuple[str, str, int, str]] = [
    ("warmup", "Warm-up", -21, "Spark curiosity without revealing everything"),
    ("buildup", "Build-up", -7, "Explain the value and start the countdown"),
    ("prelaunch", "Pre-launch", -1, "Final reminder and readiness check"),
    ("launch", "Launch", 0, "Announce and drive the primary action"),
    ("followup", "Follow-up", 3, "Recap, share proof, and convert stragglers"),
]

# Channel assets are spread across these phases, in order.
ASSET_PHASES = ["warmup", "buildup", "launch"]


def _date(iso: str) -> date:
    return date.fromisoformat(iso)


def generate_schedule(session: Session, campaign: Campaign) -> list[Milestone]:
    """Create milestones and assign task due dates from the campaign event date.

    Returns the milestones (existing ones if already scheduled). No-op without an
    event date.
    """
    if not campaign.event_date:
        return []

    existing = list(
        session.exec(
            select(Milestone).where(Milestone.campaign_id == campaign.id)
        ).all()
    )
    if existing:
        return existing

    event = _date(campaign.event_date)
    phase_date: dict[str, str] = {}
    milestones: list[Milestone] = []
    for phase, name, offset, objective in CADENCE:
        iso = (event + timedelta(days=offset)).isoformat()
        phase_date[phase] = iso
        milestone = Milestone(
            tenant_id=campaign.tenant_id,
            campaign_id=campaign.id,
            phase=phase,
            name=name,
            date=iso,
            offset_days=offset,
            objective=objective,
        )
        session.add(milestone)
        milestones.append(milestone)

    tasks = list(
        session.exec(
            select(Task).where(Task.campaign_id == campaign.id).order_by(Task.sequence)
        ).all()
    )
    asset_index = 0
    for task in tasks:
        if task.kind == TaskKind.IDEATION:
            task.phase = "prep"
            task.due_date = (event + timedelta(days=-28)).isoformat()
        elif task.kind == TaskKind.PLANNING:
            task.phase = "prep"
            task.due_date = (event + timedelta(days=-25)).isoformat()
        elif task.kind == TaskKind.ASSET:
            phase = ASSET_PHASES[asset_index % len(ASSET_PHASES)]
            asset_index += 1
            task.phase = phase
            task.due_date = phase_date[phase]
        elif task.kind == TaskKind.CLAIM_CHECK:
            task.phase = "prelaunch"
            task.due_date = (event + timedelta(days=-2)).isoformat()
        session.add(task)

    return milestones
