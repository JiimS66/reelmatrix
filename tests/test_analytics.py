import asyncio

import pytest
from sqlmodel import Session, select

from core.analytics.factory import create_analytics_source
from core.analytics.sync import sync_campaign_analytics
from core.db.engine import create_db_engine, init_db
from core.db.models import MetricSnapshot, Post
from core.db.seed import seed_testsprite
from core.llm.mock_client import MockLLMClient
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


def test_mock_ga4_source_returns_a_row_per_content_id() -> None:
    rows = asyncio.run(
        create_analytics_source("mock").fetch_attribution(
            property_ref="", utm_campaign="launch", content_ids=["abc123", "def456"]
        )
    )
    assert {r.utm_content for r in rows} == {"abc123", "def456"}
    assert all(r.conversions >= 0 and r.clicks >= r.conversions for r in rows)


def test_factory_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="Unsupported analytics source"):
        create_analytics_source("nope")


def test_sync_writes_ga4_snapshots_joined_by_utm() -> None:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    session = Session(engine)
    tenant = seed_testsprite(session)
    campaign = instantiate_campaign(session, tenant_id=tenant.id, name="Launch", brief=BRIEF)
    # ai_auto assets auto-complete -> Posts are published.
    asyncio.run(
        TaskRunner(session, client_for_provider=lambda p: MockLLMClient()).run_ready_tasks(
            campaign.id
        )
    )
    posts = session.exec(select(Post).where(Post.campaign_id == campaign.id)).all()
    assert posts

    updated = asyncio.run(sync_campaign_analytics(session, campaign))
    assert updated == len(posts)

    snapshots = session.exec(
        select(MetricSnapshot).where(MetricSnapshot.campaign_id == campaign.id)
    ).all()
    assert snapshots and all(s.source == "ga4" for s in snapshots)
    # Joined by utm_content == asset_task_id[:8], so every snapshot maps to a post.
    assert {s.post_id for s in snapshots} == {p.id for p in posts}
