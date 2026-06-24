"""Publish a campaign's drafted Posts through a PublishProvider.

Each approved asset already creates a draft ``Post`` (with its UTM link). This walks
the campaign's un-published posts, sends each to the provider (mock until a real one is
connected), and records the result — status, provider post id, and the public permalink
once live. ``human_final`` mode leaves posts as drafts for a person to ship in-tool.
"""

from typing import Optional

from sqlmodel import Session, select

from core.db.models import Campaign, Post, Task
from core.publish.base import PublishMode, PublishProvider, PublishRequest, PublishStatus
from core.publish.factory import create_publish_provider


async def publish_campaign_posts(
    session: Session,
    campaign: Campaign,
    *,
    provider: Optional[PublishProvider] = None,
    mode: PublishMode = PublishMode.AUTO,
) -> int:
    """Publish (or schedule/stage) every draft post; returns how many went live."""
    provider = provider or create_publish_provider("mock")
    posts = list(
        session.exec(
            select(Post).where(
                Post.campaign_id == campaign.id,
                Post.publish_status == PublishStatus.DRAFT.value,
            )
        ).all()
    )
    live = 0
    for post in posts:
        task = session.get(Task, post.asset_task_id)
        output = (task.output if task is not None else None) or {}
        result = await provider.publish(
            request=PublishRequest(
                channel=post.platform,
                text=str(output.get("content") or output.get("title") or ""),
                link=post.url,
            ),
            mode=mode,
        )
        post.publish_provider = result.provider
        post.publish_status = result.status.value
        post.external_id = result.external_id
        post.permalink = result.permalink
        post.publish_error = result.error
        session.add(post)
        if result.status in (PublishStatus.PUBLISHED, PublishStatus.SCHEDULED):
            live += 1
    session.commit()
    return live
