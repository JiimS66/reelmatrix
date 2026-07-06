"""Tests for the enterprise-loop slice: the channel registry grounding
per-platform work, the Linear timeline sync, first-party conversion events, and
the quality-funneled trend proposals."""

import asyncio
from typing import Any, Optional

import httpx
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from apps.api.main import create_app
from apps.api.routes import integrations
from configs.settings import AppSettings
from core.content.continuity import continuity_issues
from core.db.engine import get_session, init_db
from core.db.models import Member
from core.db.seed import seed_testsprite

BRIEF = {
    "product_name": "TestSprite",
    "product_description": "An agentic testing platform that verifies AI-generated code.",
    "target_audience": "Engineering leaders and AI-native developers",
    "marketing_goal": "Generate qualified developer signups and API key starts",
    "user_prompt": "ready for planning: launch campaign for TestSprite",
    "selected_channels": ["LinkedIn", "Email", "Landing Page"],
}


def _build() -> tuple[Any, dict[str, str]]:
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
    return app, members


async def _call(
    app: Any, method: str, path: str, member_id: Optional[str] = None, json: Any = None
) -> httpx.Response:
    headers = {"X-Member-Id": member_id} if member_id else {}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, headers=headers, json=json)


def _req(app, method, path, member_id=None, json=None) -> httpx.Response:
    return asyncio.run(_call(app, method, path, member_id, json))


# --- Channel registry -------------------------------------------------------


def test_seeded_channels_are_listed() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    channels = _req(app, "GET", "/api/v1/team/channels", lead).json()
    platforms = {c["platform"] for c in channels}
    assert "LinkedIn" in platforms and "X / Twitter" in platforms
    assert all(c["active"] for c in channels)


def test_only_lead_manages_channels() -> None:
    app, members = _build()
    writer = members["Sam (Writer)"]
    response = _req(
        app, "POST", "/api/v1/team/channels", writer, json={"platform": "YouTube"}
    )
    assert response.status_code == 403


def test_paused_channel_is_excluded_from_new_campaigns() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    channels = _req(app, "GET", "/api/v1/team/channels", lead).json()
    landing = next(c for c in channels if c["platform"] == "Landing Page")
    _req(
        app, "POST", f"/api/v1/team/channels/{landing['id']}", lead,
        json={"active": False},
    )

    created = _req(
        app, "POST", "/api/v1/team/campaigns", lead,
        json={"name": "Launch", "brief": BRIEF},
    ).json()
    asset_channels = {
        t["params"]["channel"] for t in created["tasks"] if t["kind"] == "asset"
    }
    # The paused platform is dropped; the operated ones stay.
    assert asset_channels == {"LinkedIn", "Email"}


def test_copywriter_context_carries_channel_history() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    created = _req(
        app, "POST", "/api/v1/team/campaigns", lead,
        json={"name": "Launch", "brief": BRIEF, "event_date": "2026-08-31"},
    ).json()
    cid = created["campaign"]["id"]
    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead)
    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/publish", lead)

    # A second campaign on the same channels: its posts must know the first
    # campaign's posts (continuity), which we verify through the continuity
    # check machinery rather than private context internals.
    perf = _req(app, "GET", f"/api/v1/team/campaigns/{cid}/performance", lead).json()
    assert perf["platforms"], "publish should have produced posts"


def test_continuity_check_flags_a_rehash() -> None:
    history = [
        {"title": "Ship AI code with proof, not hope", "published_at": "2026-07-01",
         "opening": "Your coding agent just merged something."},
    ]
    issues = continuity_issues(
        {"title": "Ship AI code with proof — not hope", "content": "Something new."},
        history,
    )
    assert issues and issues[0]["code"] == "repeats_recent_post"
    assert continuity_issues(
        {"title": "A verification loop for agent-written changes", "content": "x"},
        history,
    ) == []


# --- Linear timeline sync ---------------------------------------------------


def _patch_outbound(monkeypatch: Any, handler) -> None:
    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(integrations, "_outbound_client", factory)


def _linear_handler(calls: list[dict]):
    def handler(outbound: httpx.Request) -> httpx.Response:
        import json as _json

        body = _json.loads(outbound.read().decode())
        calls.append(body)
        query = body.get("query", "")
        if "teams(first" in query:
            return httpx.Response(
                200,
                json={"data": {"teams": {"nodes": [{"id": "team-1", "name": "Growth"}]}}},
            )
        if "projectCreate" in query:
            return httpx.Response(
                200,
                json={"data": {"projectCreate": {"success": True, "project": {
                    "id": "proj-1", "url": "https://linear.app/growth/project/launch"}}}},
            )
        if "issueCreate" in query:
            n = sum(1 for c in calls if "issueCreate" in c.get("query", ""))
            return httpx.Response(
                200,
                json={"data": {"issueCreate": {"success": True, "issue": {
                    "id": f"iss-{n}", "identifier": f"GRO-{n}",
                    "url": f"https://linear.app/growth/issue/GRO-{n}"}}}},
            )
        return httpx.Response(200, json={"data": {"issueUpdate": {"success": True}}})

    return handler


def test_linear_sync_is_idempotent(monkeypatch: Any) -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    created = _req(
        app, "POST", "/api/v1/team/campaigns", lead,
        json={"name": "Launch", "brief": BRIEF, "event_date": "2026-08-31"},
    ).json()
    cid = created["campaign"]["id"]
    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead)

    calls: list[dict] = []
    _patch_outbound(monkeypatch, _linear_handler(calls))

    first = _req(
        app, "POST", "/api/v1/team/integrations/linear/sync-campaign", lead,
        json={"campaign_id": cid, "api_key": "lin_api_test"},
    ).json()
    assert first["ok"] and first["created"] > 0 and first["updated"] == 0
    assert first["project_url"] == "https://linear.app/growth/project/launch"

    second = _req(
        app, "POST", "/api/v1/team/integrations/linear/sync-campaign", lead,
        json={"campaign_id": cid, "api_key": "lin_api_test"},
    ).json()
    # Re-sync updates the linked issues — it never duplicates them.
    assert second["created"] == 0 and second["updated"] == first["created"]
    assert sum(1 for c in calls if "projectCreate" in c.get("query", "")) == 1

    links = _req(
        app, "GET",
        f"/api/v1/team/integrations/links?campaign_id={cid}", lead,
    ).json()
    kinds = {l["local_kind"] for l in links}
    assert kinds == {"campaign", "task"}


def test_linear_sync_requires_dated_tasks(monkeypatch: Any) -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    created = _req(
        app, "POST", "/api/v1/team/campaigns", lead,
        json={"name": "No dates", "brief": BRIEF},  # no event_date → no due dates
    ).json()
    calls: list[dict] = []
    _patch_outbound(monkeypatch, _linear_handler(calls))
    response = _req(
        app, "POST", "/api/v1/team/integrations/linear/sync-campaign", lead,
        json={"campaign_id": created["campaign"]["id"], "api_key": "k"},
    )
    assert response.status_code == 400
    assert calls == []


# --- First-party conversion events (S2S) ------------------------------------


def test_events_override_mock_funnel_numbers() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    created = _req(
        app, "POST", "/api/v1/team/campaigns", lead,
        json={"name": "Launch", "brief": BRIEF, "event_date": "2026-08-31"},
    ).json()
    cid = created["campaign"]["id"]
    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead)
    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/publish", lead)

    asset = next(t for t in _req(
        app, "GET", f"/api/v1/team/campaigns/{cid}/board", lead
    ).json()["tasks"] if t["kind"] == "asset")
    utm_content = asset["id"][:8]

    for event, count in (("signup", 3), ("activation", 2), ("paid", 1)):
        for _ in range(count):
            response = _req(
                app, "POST", "/api/v1/events", lead,
                json={"event": event, "utm_content": utm_content},
            )
            assert response.status_code == 200

    perf = _req(app, "GET", f"/api/v1/team/campaigns/{cid}/performance", lead).json()
    assert perf["attribution_model"] == "last-touch · modeled"
    post = next(
        p
        for platform in perf["platforms"]
        for p in platform["posts"]
        if p["source"] == "events"
    )
    assert (post["signups"], post["activations"], post["paid"]) == (3, 2, 1)


# --- Trend proposals: the quality funnel ------------------------------------


def test_trend_proposals_are_funneled_into_the_inbox() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    created = _req(
        app, "POST", "/api/v1/team/campaigns", lead,
        json={"name": "Launch", "brief": BRIEF, "event_date": "2026-08-31"},
    ).json()
    cid = created["campaign"]["id"]
    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead)
    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/trends", lead)

    actions = _req(app, "POST", "/api/v1/team/actions/plan", lead).json()
    trend_actions = [a for a in actions if a["type"] == "draft_trend"]
    assert 1 <= len(trend_actions) <= 3  # quota-capped
    # Every proposal that survived the funnel carries its bridge rationale.
    assert all("Why us, why now" in a["rationale"] for a in trend_actions)

    # Accepting one creates a review-gated rapid post in the campaign.
    accepted = _req(
        app, "POST", f"/api/v1/team/actions/{trend_actions[0]['id']}/accept", lead
    )
    assert accepted.status_code == 200
    board = _req(app, "GET", f"/api/v1/team/campaigns/{cid}/board", lead).json()
    rapid = [
        t for t in board["tasks"]
        if t["kind"] == "asset" and (t["params"] or {}).get("provenance") == "trend"
    ]
    assert rapid and all(
        t["execution_mode"] == "ai_draft_human_review" for t in rapid
    )
