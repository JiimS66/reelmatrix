import asyncio

import pytest
from sqlmodel import Session, select

from core.db.engine import create_db_engine, init_db
from core.db.models import Post
from core.db.seed import seed_testsprite
from core.llm.mock_client import MockLLMClient
from core.publish.base import PublishMode, PublishRequest, PublishStatus
from core.publish.factory import create_publish_provider
from core.publish.publish import publish_campaign_posts
from core.workflows.campaign_instantiation import instantiate_campaign
from core.workflows.task_runner import TaskRunner

BRIEF = {
    "product_name": "TestSprite",
    "product_description": "An agentic testing platform that verifies AI-generated code.",
    "target_audience": "Engineering leaders",
    "marketing_goal": "Generate developer signups",
    "user_prompt": "ready for planning: launch",
    "selected_channels": ["LinkedIn", "Email"],
}


def test_mock_publisher_modes_and_constraints() -> None:
    provider = create_publish_provider("mock")
    req = PublishRequest(channel="LinkedIn", text="hello world")
    auto = asyncio.run(provider.publish(request=req, mode=PublishMode.AUTO))
    assert auto.status == PublishStatus.PUBLISHED and auto.permalink.startswith("mock://")
    staged = asyncio.run(provider.publish(request=req, mode=PublishMode.HUMAN_FINAL))
    assert staged.status == PublishStatus.DRAFT and staged.permalink is None
    assert provider.constraints("x / twitter").max_chars == 280


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported publish provider"):
        create_publish_provider("nope")


def test_publish_campaign_posts_marks_posts_published_and_is_idempotent() -> None:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    session = Session(engine)
    tenant = seed_testsprite(session)
    campaign = instantiate_campaign(session, tenant_id=tenant.id, name="Launch", brief=BRIEF)
    asyncio.run(
        TaskRunner(session, client_for_provider=lambda p: MockLLMClient()).run_ready_tasks(
            campaign.id
        )
    )
    posts = session.exec(select(Post).where(Post.campaign_id == campaign.id)).all()
    assert posts and all(p.publish_status == "draft" for p in posts)

    live = asyncio.run(publish_campaign_posts(session, campaign))
    assert live == len(posts)
    for post in posts:
        session.refresh(post)
        assert post.publish_status == "published"
        assert post.permalink and post.permalink.startswith("mock://")

    # No drafts left → a re-publish is a no-op.
    assert asyncio.run(publish_campaign_posts(session, campaign)) == 0
