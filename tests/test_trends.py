import asyncio

from sqlmodel import Session, select

from core.db.engine import create_db_engine, init_db
from core.db.models import Task, TaskKind
from core.db.seed import seed_testsprite
from core.trends.base import TrendItem
from core.trends.factory import create_trend_source
from core.trends.refresh import refresh_campaign_trends
from core.workflows.campaign_instantiation import instantiate_campaign

BRIEF = {
    "product_name": "TestSprite",
    "product_description": "An agentic testing platform that verifies AI-generated code.",
    "target_audience": "Engineering leaders and AI-native developers",
    "marketing_goal": "Generate qualified developer signups",
    "user_prompt": "ready for planning: launch",
    "selected_channels": ["LinkedIn"],
}


def test_mock_trend_source_echoes_query_highest_first() -> None:
    items = asyncio.run(create_trend_source("mock").fetch(query="agentic testing", limit=3))
    assert len(items) == 3
    assert all(isinstance(i, TrendItem) for i in items)
    assert any("agentic testing" in i.title for i in items)
    assert {i.source for i in items} <= {"hackernews", "reddit", "github", "rss"}
    assert items[0].score >= items[-1].score


def test_refresh_writes_brand_filtered_angles_to_the_plan() -> None:
    engine = create_db_engine("sqlite://")
    init_db(engine)
    session = Session(engine)
    tenant = seed_testsprite(session)
    campaign = instantiate_campaign(session, tenant_id=tenant.id, name="Launch", brief=BRIEF)

    planning = session.exec(
        select(Task).where(
            Task.campaign_id == campaign.id, Task.kind == TaskKind.PLANNING
        )
    ).first()
    planning.output = {"core_message": "x", "timely_angles": ["stale"]}
    session.add(planning)
    session.commit()

    angles = asyncio.run(refresh_campaign_trends(session, campaign))
    assert angles and all(isinstance(a, str) for a in angles)
    assert angles != ["stale"]

    session.refresh(planning)
    assert planning.output["timely_angles"] == angles
