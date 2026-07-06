"""Tests for one-URL onboarding: page parsing, channel detection, and the
apply flow that prefills the channel registry + brand draft."""

import asyncio
from typing import Any, Optional

import httpx
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from apps.api.main import create_app
from configs.settings import AppSettings
from core.db.engine import get_session, init_db
from core.db.models import Member
from core.db.seed import seed_testsprite
from core.ingest import web as ingest_web

_SITE_HTML = """
<html>
  <head>
    <title>Acme DevTools</title>
    <meta name="description" content="Acme verifies AI-generated code. Technical teams ship faster.">
    <style>body { color: red }</style>
  </head>
  <body>
    <script>var hidden = "should not appear";</script>
    <h1>Ship AI code with proof</h1>
    <p>Acme is a concise, developer-first Testing platform for Engineering teams.</p>
    <a href="https://www.linkedin.com/company/acme">LinkedIn</a>
    <a href="https://x.com/acmedev">X</a>
    <a href="https://github.com/acme">GitHub</a>
    <a href="https://discord.gg/acme">Discord</a>
    <a href="/blog">Blog</a>
    <a href="mailto:hello@acme.dev">Contact</a>
  </body>
</html>
"""


def _patch_fetch(monkeypatch: Any, html: str = _SITE_HTML) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    monkeypatch.setattr(
        ingest_web,
        "_client_factory",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    # DNS may not resolve for the fake domain in CI — the SSRF guard is
    # unit-tested separately below.
    monkeypatch.setattr(ingest_web, "assert_public_http_url", lambda url: url)


def test_fetch_site_extracts_text_and_channels(monkeypatch: Any) -> None:
    _patch_fetch(monkeypatch)
    text, channels = ingest_web.fetch_site("https://acme.dev")
    assert "Ship AI code with proof" in text
    assert "should not appear" not in text  # script content dropped
    assert "verifies AI-generated code" in text  # meta description kept
    platforms = {c.platform: c.handle for c in channels}
    assert platforms.keys() == {
        "LinkedIn", "X / Twitter", "GitHub / CLI", "Community", "Blog", "Email",
    }
    assert platforms["Email"] == "hello@acme.dev"  # mailto: prefix stripped
    assert platforms["Blog"] == "https://acme.dev/blog"  # relative href resolved


def test_ssrf_guard_refuses_private_hosts() -> None:
    try:
        ingest_web.assert_public_http_url("http://127.0.0.1/internal")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "private" in str(exc)
    try:
        ingest_web.assert_public_http_url("ftp://example.com")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


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


def _req(app, method, path, member_id: Optional[str] = None, json: Any = None):
    async def _call() -> httpx.Response:
        headers = {"X-Member-Id": member_id} if member_id else {}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path, headers=headers, json=json)

    return asyncio.run(_call())


def test_onboard_from_url_prefills_channels_and_brand(monkeypatch: Any) -> None:
    _patch_fetch(monkeypatch)
    app, members = _build()
    lead = members["Adam (Lead)"]

    result = _req(
        app, "POST", "/api/v1/team/brand/onboard-from-url", lead,
        json={"url": "acme.dev"},  # scheme auto-added by the schema
    ).json()
    assert result["applied"] is True
    assert {c["platform"] for c in result["channels"]} >= {"LinkedIn", "GitHub / CLI"}
    assert result["draft"]["value_proposition"]

    channels = _req(app, "GET", "/api/v1/team/channels", lead).json()
    by_platform = {c["platform"]: c for c in channels}
    # Detected handle lands on the (seeded) registry entry.
    assert by_platform["LinkedIn"]["handle"] == "https://www.linkedin.com/company/acme"
    # New platform from the page joins the registry.
    assert "YouTube" not in by_platform  # not on the page → not invented

    brand = _req(app, "GET", "/api/v1/team/brand", lead).json()
    assert brand is not None


def test_onboard_from_url_is_lead_only(monkeypatch: Any) -> None:
    _patch_fetch(monkeypatch)
    app, members = _build()
    writer = members["Sam (Writer)"]
    response = _req(
        app, "POST", "/api/v1/team/brand/onboard-from-url", writer,
        json={"url": "https://acme.dev"},
    )
    assert response.status_code == 403
