"""Refresh a campaign's ``timely_angles`` from a TrendSource.

This is the async orchestration (the source fetch is I/O): pull the current hot
items for the campaign's topic, keep the ones relevant to the brand/ICP, turn them
into angle strings, and persist them onto the planning task's output (where the
schedule/calendar already reads ``timely_angles``).
"""

from typing import Optional

from sqlmodel import Session, select

from core.db.models import BrandProfile, Campaign, Task, TaskKind
from core.trends.base import TrendSource
from core.trends.factory import create_trend_source


def _keywords(campaign: Campaign, brand: Optional[BrandProfile]) -> list[str]:
    brief = campaign.brief or {}
    text = " ".join(
        str(brief.get(field, ""))
        for field in ("product_name", "target_audience", "marketing_goal")
    )
    if brand is not None:
        text += " " + " ".join(brand.approved_phrases or [])
    return [word for word in text.lower().split() if len(word) > 3]


def _trend_query(campaign: Campaign) -> str:
    brief = campaign.brief or {}
    parts = [str(brief.get("product_name", "")), str(brief.get("target_audience", ""))]
    return " ".join(p for p in parts if p).strip() or campaign.name


async def refresh_campaign_trends(
    session: Session,
    campaign: Campaign,
    *,
    source: Optional[TrendSource] = None,
    limit: int = 5,
) -> list[str]:
    """Fetch + brand-filter trends, write them to the plan's timely_angles, and
    return them. Falls back to the unfiltered items if nothing matches the brand."""
    source = source or create_trend_source("mock")
    brand = session.exec(
        select(BrandProfile).where(BrandProfile.tenant_id == campaign.tenant_id)
    ).first()
    keywords = _keywords(campaign, brand)

    items = await source.fetch(query=_trend_query(campaign), limit=limit)
    relevant = [
        item
        for item in items
        if any(word in item.title.lower() for word in keywords)
    ] or items
    angles = [f"{item.title} — via {item.source}" for item in relevant]

    planning = session.exec(
        select(Task).where(
            Task.campaign_id == campaign.id, Task.kind == TaskKind.PLANNING
        )
    ).first()
    if planning is not None and planning.output is not None:
        planning.output = {**planning.output, "timely_angles": angles}
        session.add(planning)
        session.commit()
    return angles
