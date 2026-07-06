"""Sync a campaign's real conversions from an AnalyticsSource into MetricSnapshots.

Pulls UTM-attributed conversions for the campaign, joins each row back to its Post by
``utm_content == Post.asset_task_id[:8]`` (the tag ReelMatrix already mints), and writes
a ``source="ga4"`` MetricSnapshot. The performance view already prefers the latest
snapshot over the mock, so a connected source lights it up with no read-side change.
"""

from typing import Optional

from sqlmodel import Session, select

from core.analytics.base import AnalyticsSource
from core.analytics.factory import create_analytics_source
from core.content.tracking import _slug
from core.db.models import Campaign, MetricSnapshot, Post


async def sync_campaign_analytics(
    session: Session,
    campaign: Campaign,
    *,
    source: Optional[AnalyticsSource] = None,
    property_ref: str = "",
) -> int:
    """Fetch + join + upsert conversions; returns the number of posts updated."""
    if source is None:
        from configs.settings import get_settings

        source = create_analytics_source(get_settings().analytics_source)
    posts = list(
        session.exec(select(Post).where(Post.campaign_id == campaign.id)).all()
    )
    by_content = {post.asset_task_id[:8]: post for post in posts}
    if not by_content:
        return 0

    rows = await source.fetch_attribution(
        property_ref=property_ref,
        utm_campaign=_slug(campaign.event_name or campaign.name),
        content_ids=list(by_content),
    )
    # Replace prior synced snapshots so repeated syncs stay idempotent (manual
    # snapshots are kept). The perf view takes the latest snapshot per post.
    for old in session.exec(
        select(MetricSnapshot).where(
            MetricSnapshot.campaign_id == campaign.id, MetricSnapshot.source == "ga4"
        )
    ).all():
        session.delete(old)
    updated = 0
    for row in rows:
        post = by_content.get(row.utm_content or "")
        if post is None:
            continue
        session.add(
            MetricSnapshot(
                tenant_id=campaign.tenant_id,
                campaign_id=campaign.id,
                post_id=post.id,
                source="ga4",
                impressions=row.sessions,
                clicks=row.clicks,
                signups=row.conversions,
                activations=row.activations,
                paid=row.paid,
            )
        )
        updated += 1
    session.commit()
    return updated
