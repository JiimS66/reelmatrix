"""Tests for the quality/ops slice: draft fan-out selection, flywheel channel
boost, structured-output self-repair, review notifications, copy pack, usage
summary, and the Plausible attribution source."""

import asyncio
import io
import zipfile
from typing import Any, Optional

import httpx
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from apps.api.main import create_app
from configs.settings import AppSettings, get_settings
from core.analytics.plausible import PlausibleSource
from core.db.engine import get_session, init_db
from core.db.models import AttributeOutcome, Member
from core.db.seed import seed_testsprite
from core.llm.base import LLMResponseValidationError
from core.llm.openai_compatible_client import OpenAICompatibleLLMClient, _strip_fences
from core.schemas.campaign import IdeationResult
from core.workflows.campaign_instantiation import flywheel_channel_boost

BRIEF = {
    "product_name": "TestSprite",
    "product_description": "An agentic testing platform that verifies AI-generated code.",
    "target_audience": "Engineering leaders and AI-native developers",
    "marketing_goal": "Generate qualified developer signups",
    "user_prompt": "ready for planning: launch campaign for TestSprite",
    "selected_channels": ["LinkedIn", "Email"],
}


def _build() -> tuple[Any, dict[str, str], Any]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    with Session(engine) as session:
        seed_testsprite(session)
        members = {m.display_name: m.id for m in session.exec(select(Member)).all()}

    app = create_app(AppSettings(_env_file=None, app_env="test", llm_provider="mock"))

    def _override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    return app, members, engine


async def _call(
    app: Any, method: str, path: str, member_id: Optional[str] = None, json: Any = None
) -> httpx.Response:
    headers = {"X-Member-Id": member_id} if member_id else {}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, headers=headers, json=json)


def _req(app, method, path, member_id=None, json=None) -> httpx.Response:
    return asyncio.run(_call(app, method, path, member_id, json))


def _run_campaign(app, lead) -> str:
    created = _req(
        app, "POST", "/api/v1/team/campaigns", lead,
        json={"name": "Launch", "brief": BRIEF, "event_date": "2026-08-31"},
    ).json()
    cid = created["campaign"]["id"]
    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead)
    return cid


# --- Structured-output hardening ---------------------------------------------


def test_strip_fences_unwraps_markdown_json() -> None:
    fenced = "```json\n{\"a\": 1}\n```"
    assert _strip_fences(fenced) == '{"a": 1}'
    assert _strip_fences('{"a": 1}') == '{"a": 1}'


def test_generate_structured_self_repairs_once() -> None:
    client = OpenAICompatibleLLMClient(
        base_url="http://localhost:1/v1", model="m", api_key="k",
        timeout_seconds=5, provider_name="Test",
    )
    responses = iter([
        "not json at all",
        '{"campaign_concept": "x", "core_message": "y",'
        ' "target_audience_insight": "z", "recommended_angles": ["a"],'
        ' "risks_or_assumptions": [], "follow_up_questions": [],'
        ' "is_ready_for_planning": true}',
    ])

    async def fake_complete(*, system_prompt: str, user_prompt: str) -> str:
        return next(responses)

    client._complete = fake_complete  # type: ignore[method-assign]
    result = asyncio.run(
        client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=IdeationResult
        )
    )
    assert result.core_message == "y"


def test_generate_structured_surfaces_double_failure() -> None:
    client = OpenAICompatibleLLMClient(
        base_url="http://localhost:1/v1", model="m", api_key="k",
        timeout_seconds=5, provider_name="Test",
    )

    async def fake_complete(*, system_prompt: str, user_prompt: str) -> str:
        return "still not json"

    client._complete = fake_complete  # type: ignore[method-assign]
    try:
        asyncio.run(
            client.generate_structured(
                system_prompt="s", user_prompt="u", response_model=IdeationResult
            )
        )
        raise AssertionError("expected validation error")
    except LLMResponseValidationError:
        pass


# --- Flywheel channel boost ---------------------------------------------------


def test_flywheel_boost_requires_evidence() -> None:
    _, _, engine = _build()
    with Session(engine) as session:
        tenant_id = session.exec(select(Member)).first().tenant_id
        # No outcomes at all → no boost.
        assert flywheel_channel_boost(session, tenant_id, ["LinkedIn", "Email"]) is None

        # A clearly better channel with enough posts → boosted, with a reason.
        session.add(AttributeOutcome(
            tenant_id=tenant_id, attribute_type="hook_type", attribute_value="question",
            channel="LinkedIn", segment="", impressions=1000, conversions=100, n_posts=4,
        ))
        session.add(AttributeOutcome(
            tenant_id=tenant_id, attribute_type="hook_type", attribute_value="stat",
            channel="Email", segment="", impressions=1000, conversions=20, n_posts=4,
        ))
        session.commit()
        boost = flywheel_channel_boost(session, tenant_id, ["LinkedIn", "Email"])
        assert boost is not None
        channel, reason = boost
        assert channel == "LinkedIn" and "Flywheel" in reason


def test_campaign_gets_flywheel_bonus_post() -> None:
    app, members, engine = _build()
    lead = members["Adam (Lead)"]
    with Session(engine) as session:
        tenant_id = session.exec(select(Member)).first().tenant_id
        session.add(AttributeOutcome(
            tenant_id=tenant_id, attribute_type="hook_type", attribute_value="question",
            channel="LinkedIn", segment="", impressions=1000, conversions=100, n_posts=4,
        ))
        session.add(AttributeOutcome(
            tenant_id=tenant_id, attribute_type="hook_type", attribute_value="stat",
            channel="Email", segment="", impressions=1000, conversions=20, n_posts=4,
        ))
        session.commit()

    created = _req(
        app, "POST", "/api/v1/team/campaigns", lead,
        json={"name": "Boosted", "brief": BRIEF},
    ).json()
    assets = [t for t in created["tasks"] if t["kind"] == "asset"]
    linkedin = [t for t in assets if t["params"]["channel"] == "LinkedIn"]
    assert len(assets) == 3 and len(linkedin) == 2  # 2 channels + 1 bonus
    assert any("Flywheel" in str(t["params"].get("flywheel_boost", "")) for t in linkedin)


# --- Review notification webhook ----------------------------------------------


def test_review_notification_fires_when_configured(monkeypatch: Any) -> None:
    from core import notify

    sent: list[dict] = []
    monkeypatch.setattr(
        notify.httpx, "post",
        lambda url, json, timeout: sent.append({"url": url, "json": json}),
    )
    get_settings.cache_clear()
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://hooks.example.com/x")
    try:
        app, members, _ = _build()
        lead = members["Adam (Lead)"]
        created = _req(
            app, "POST", "/api/v1/team/campaigns", lead,
            json={"name": "Gated", "brief": BRIEF, "review_assets": True},
        ).json()
        _req(app, "POST", f"/api/v1/team/campaigns/{created['campaign']['id']}/run", lead)
    finally:
        get_settings.cache_clear()
    assert sent and sent[0]["url"] == "https://hooks.example.com/x"
    assert sent[0]["json"]["event"] == "needs_review"


# --- Copy pack ------------------------------------------------------------------


def test_copy_pack_zips_approved_posts() -> None:
    app, members, _ = _build()
    lead = members["Adam (Lead)"]
    cid = _run_campaign(app, lead)

    response = _req(app, "GET", f"/api/v1/team/campaigns/{cid}/copy-pack", lead)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as pack:
        names = pack.namelist()
        assert "README.md" in names
        assert any(n.startswith("LinkedIn/") for n in names)
        first_post = next(n for n in names if n != "README.md")
        body = pack.read(first_post).decode("utf-8")
        assert "utm_content=" in body and "## Call to action" in body


# --- Usage summary ----------------------------------------------------------------


def test_usage_summary_counts_runs() -> None:
    app, members, _ = _build()
    lead = members["Adam (Lead)"]
    _run_campaign(app, lead)
    usage = _req(app, "GET", "/api/v1/team/usage", lead).json()
    assert usage["total_runs"] > 0
    assert any(row["runs"] > 0 for row in usage["rows"])


# --- Plausible source ----------------------------------------------------------


def test_plausible_source_joins_by_utm_content(monkeypatch: Any) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("PLAUSIBLE_SITE_ID", "example.com")
    monkeypatch.setenv("PLAUSIBLE_API_KEY", "key")

    def handler(request: httpx.Request) -> httpx.Response:
        # filters arrive URL-encoded, so match on the goal name itself.
        if "goal" in str(request.url):
            return httpx.Response(
                200, json={"results": [{"utm_content": "abc12345", "visitors": 7}]}
            )
        return httpx.Response(
            200, json={"results": [{"utm_content": "abc12345", "visitors": 90}]}
        )

    original_client = httpx.AsyncClient

    def patched_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)
    try:
        rows = asyncio.run(
            PlausibleSource().fetch_attribution(
                property_ref="", utm_campaign="launch", content_ids=["abc12345", "zzz"]
            )
        )
    finally:
        get_settings.cache_clear()
    assert len(rows) == 1
    assert rows[0].utm_content == "abc12345"
    assert rows[0].sessions == 90 and rows[0].conversions == 7
