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


def _task(board: dict, kind: str) -> dict:
    return next(t for t in board["tasks"] if t["kind"] == kind)


def _create(app, lead) -> dict:
    return _req(app, "POST", "/api/v1/team/campaigns", lead,
                json={"name": "Launch", "brief": BRIEF}).json()


def _run_campaign(app, lead) -> tuple[str, dict]:
    """Create then run a campaign; with the ai_auto default this yields a full draft."""
    created = _create(app, lead)
    cid = created["campaign"]["id"]
    board = _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead).json()
    return cid, board


def test_run_auto_completes_the_ai_pipeline() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]

    created = _create(app, lead)
    # ideation + planning + 3 channel assets + claim check, all unstarted.
    assert len(created["tasks"]) == 6
    assert all(t["status"] == "todo" for t in created["tasks"])

    cid = created["campaign"]["id"]
    board = _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead).json()

    # AI runs the whole pipeline; only the human-owned claim check is left.
    assert _task(board, "ideation")["status"] == "done"
    assert _task(board, "planning")["status"] == "done"
    assets = [t for t in board["tasks"] if t["kind"] == "asset"]
    assert assets and all(a["status"] == "done" and a["output"] for a in assets)
    assert all("format" in a["checks"] for a in assets)
    claim = _task(board, "claim_check")
    assert claim["status"] == "todo"
    assert claim["output"] and "claim_checks" in claim["output"]


def test_human_can_insert_a_review_gate() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    created = _create(app, lead)
    cid = created["campaign"]["id"]
    ideation = _task(created, "ideation")

    # Opt this stage into a review gate before running.
    _req(app, "POST", f"/api/v1/team/tasks/{ideation['id']}/assign", lead,
         json={"execution_mode": "ai_draft_human_review"})
    board = _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead).json()
    assert _task(board, "ideation")["status"] == "needs_review"
    assert _task(board, "planning")["status"] == "todo"

    # Approving resumes the auto pipeline.
    board = _req(app, "POST", f"/api/v1/team/tasks/{ideation['id']}/review", lead,
                 json={"action": "approve"}).json()
    assert _task(board, "ideation")["status"] == "done"
    assert _task(board, "planning")["status"] == "done"


def test_human_edits_an_auto_completed_asset() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    _cid, board = _run_campaign(app, lead)
    asset = next(t for t in board["tasks"] if t["kind"] == "asset")  # already done

    edited = {**asset["output"], "content": "This release is bug-free and basically magic."}
    response = _req(app, "POST", f"/api/v1/team/tasks/{asset['id']}/edit", lead,
                    json={"output": edited})
    assert response.status_code == 200
    body = response.json()
    assert "bug-free" in body["output"]["content"]
    assert any(i["code"] == "forbidden_word" for i in body["checks"]["brand"])


def test_run_harvests_atoms_from_auto_completed_assets() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    _run_campaign(app, lead)

    atoms = _req(app, "GET", "/api/v1/team/atoms", lead).json()
    kinds = {a["kind"] for a in atoms}
    assert "headline" in kinds and "cta" in kinds
    ctas = _req(app, "GET", "/api/v1/team/atoms?kind=cta", lead).json()
    assert ctas and all(a["kind"] == "cta" for a in ctas)


def test_human_member_completes_a_reassigned_task() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    sam = members["Sam (Writer)"]
    _cid, board = _run_campaign(app, lead)
    claim = _task(board, "claim_check")  # human-owned, still todo

    assigned = _req(app, "POST", f"/api/v1/team/tasks/{claim['id']}/assign", lead,
                    json={"member_id": sam})
    assert assigned.status_code == 200 and assigned.json()["assignee_id"] == sam

    inbox = _req(app, "GET", "/api/v1/team/inbox", sam).json()
    assert any(t["id"] == claim["id"] for t in inbox)

    submitted = _req(app, "POST", f"/api/v1/team/tasks/{claim['id']}/submit", sam,
                     json={"output": {"claim_checks": []}})
    assert submitted.status_code == 200 and submitted.json()["status"] == "done"


EVENT = {"event_name": "v2 release", "event_date": "2026-07-31"}


def _create_with_event(app, lead) -> dict:
    return _req(app, "POST", "/api/v1/team/campaigns", lead,
                json={"name": "Launch", "brief": BRIEF, **EVENT}).json()


def test_schedule_backplans_calendar_and_timely_angles() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    board = _create_with_event(app, lead)
    cid = board["campaign"]["id"]
    assert board["campaign"]["event_date"] == "2026-07-31"

    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead)  # plan -> timely angles
    sched = _req(app, "GET", f"/api/v1/team/campaigns/{cid}/schedule", lead).json()

    phases = {m["phase"]: m["date"] for m in sched["milestones"]}
    assert len(sched["milestones"]) == 5
    assert phases["launch"] == "2026-07-31"
    assert phases["warmup"] == "2026-07-10"
    assert sched["timely_angles"]  # AI suggested timely hooks
    assert any(t["due_date"] for t in sched["tasks"])


def test_todo_lists_scheduled_not_done_tasks() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    board = _create_with_event(app, lead)
    cid = board["campaign"]["id"]
    _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead)

    todo = _req(app, "GET", "/api/v1/team/todo", lead).json()
    # After the AI auto-runs, the human claim check is the open dated task.
    assert any(item["task"]["kind"] == "claim_check" for item in todo)
    assert all(item["task"]["due_date"] for item in todo)


def test_create_rejects_a_bad_event_date() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    bad = _req(app, "POST", "/api/v1/team/campaigns", lead,
               json={"name": "x", "brief": BRIEF, "event_date": "July 31"})
    assert bad.status_code == 422


def test_lists_tenant_campaigns_newest_first() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    _create(app, lead)
    _create(app, lead)
    campaigns = _req(app, "GET", "/api/v1/team/campaigns", lead).json()
    assert len(campaigns) == 2


def test_members_bootstrap_lists_the_team() -> None:
    app, _members = _build()
    listed = _req(app, "GET", "/api/v1/team/members").json()
    assert len(listed) == 7
    assert any(m["role"] == "lead" for m in listed)


def test_review_assets_leaves_drafts_for_review() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    created = _req(
        app, "POST", "/api/v1/team/campaigns", lead,
        json={"name": "Launch", "brief": BRIEF, "review_assets": True},
    ).json()
    cid = created["campaign"]["id"]
    board = _req(app, "POST", f"/api/v1/team/campaigns/{cid}/run", lead).json()
    assets = [t for t in board["tasks"] if t["kind"] == "asset"]
    assert assets and all(t["status"] == "needs_review" for t in assets)


def test_performance_groups_published_posts_by_platform() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    cid, _board = _run_campaign(app, lead)  # ai_auto -> assets done -> posts published
    perf = _req(app, "GET", f"/api/v1/team/campaigns/{cid}/performance", lead).json()
    assert len(perf["platforms"]) >= 1
    plat = perf["platforms"][0]
    post = plat["posts"][0]
    assert "utm_source=" in post["url"]
    assert post["impressions"] >= post["clicks"] >= post["signups"] >= 0
    assert plat["signups"] == sum(p["signups"] for p in plat["posts"])
    assert perf["totals"]["signups"] == sum(pl["signups"] for pl in perf["platforms"])


def test_record_metrics_overrides_a_post_mock() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    cid, _board = _run_campaign(app, lead)
    perf = _req(app, "GET", f"/api/v1/team/campaigns/{cid}/performance", lead).json()
    post = perf["platforms"][0]["posts"][0]
    updated = _req(
        app, "POST", f"/api/v1/team/posts/{post['post_id']}/metrics", lead,
        json={"impressions": 9999, "clicks": 321, "signups": 42},
    ).json()
    rows = [p for pl in updated["platforms"] for p in pl["posts"]]
    row = next(p for p in rows if p["post_id"] == post["post_id"])
    assert row["impressions"] == 9999
    assert row["signups"] == 42
    assert row["source"] == "manual"


def test_permissions_and_auth() -> None:
    app, members = _build()
    sam = members["Sam (Writer)"]

    assert _req(app, "GET", "/api/v1/team/inbox").status_code == 422
    assert _req(app, "GET", "/api/v1/team/inbox", "no-such-member").status_code == 401
    forbidden = _req(app, "POST", "/api/v1/team/campaigns", sam,
                     json={"name": "x", "brief": BRIEF})
    assert forbidden.status_code == 403


def test_assign_rejects_ai_agent_on_human_only_task() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    ai_agent = members["Ideation bot"]
    _cid, board = _run_campaign(app, lead)
    claim = _task(board, "claim_check")  # human_only

    rejected = _req(app, "POST", f"/api/v1/team/tasks/{claim['id']}/assign", lead,
                    json={"member_id": ai_agent})
    assert rejected.status_code == 400


def test_submit_rejects_task_not_in_submittable_state() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    _cid, board = _run_campaign(app, lead)
    claim = _task(board, "claim_check")

    # First submit completes it; a second submit is rejected (not submittable).
    assert _req(app, "POST", f"/api/v1/team/tasks/{claim['id']}/submit", lead,
                json={}).status_code == 200
    rejected = _req(app, "POST", f"/api/v1/team/tasks/{claim['id']}/submit", lead, json={})
    assert rejected.status_code == 409


def test_non_lead_non_assignee_cannot_edit() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    sam = members["Sam (Writer)"]
    _cid, board = _run_campaign(app, lead)
    asset = next(t for t in board["tasks"] if t["kind"] == "asset")  # assigned to the AI agent

    rejected = _req(app, "POST", f"/api/v1/team/tasks/{asset['id']}/edit", sam,
                    json={"output": {"x": 1}})
    assert rejected.status_code == 403


def test_task_detail_exposes_available_actions() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    _cid, board = _run_campaign(app, lead)
    claim = _task(board, "claim_check")  # todo, assigned to the lead

    detail = _req(app, "GET", f"/api/v1/team/tasks/{claim['id']}", lead).json()
    assert {"edit", "assign", "submit", "comment"} <= set(detail["available_actions"])


def _org(app, member) -> dict:
    return _req(app, "GET", "/api/v1/team/org", member).json()


def test_org_returns_the_roster_and_config_catalogs() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    org = _org(app, lead)

    assert len(org["members"]) == 7
    by_name = {m["display_name"]: m for m in org["members"]}
    assert by_name["Adam (Lead)"]["reports_to"] is None
    asset_writer = by_name["Asset writer"]
    assert asset_writer["handles_kinds"] == ["asset"]
    assert asset_writer["agent_role"] == "copywriter"
    # The Auditor owns no task kinds; the Designer owns visuals.
    assert by_name["Content auditor"]["agent_role"] == "auditor"
    assert by_name["Content auditor"]["handles_kinds"] == []
    assert by_name["Designer"]["handles_kinds"] == ["visual"]
    assert {"auditor", "designer"} <= {r["key"] for r in org["agent_roles"]}
    assert asset_writer["reports_to"] == lead
    # Catalogs the team UI offers when configuring an employee.
    assert "asset" in org["task_kinds"]
    assert any(r["key"] == "copywriter" for r in org["agent_roles"])


def test_lead_adds_a_digital_employee_and_work_routes_to_it() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]

    # Hand asset work off the seeded writer, then hire a fresh AI copywriter for it.
    asset_writer = next(
        m for m in _org(app, lead)["members"] if m["display_name"] == "Asset writer"
    )
    _req(app, "POST", f"/api/v1/team/org/members/{asset_writer['id']}", lead,
         json={"handles_kinds": []})
    hired = _req(app, "POST", "/api/v1/team/org/members", lead, json={
        "display_name": "Social copywriter",
        "role": "copywriter",
        "job_description": "Punchy social posts.",
        "handles_kinds": ["asset"],
        "reports_to": lead,
    })
    assert hired.status_code == 200
    new_id = hired.json()["id"]
    assert hired.json()["kind"] == "ai"

    # A new campaign routes — and runs — its posts through the new employee.
    cid, board = _run_campaign(app, lead)
    assets = [t for t in board["tasks"] if t["kind"] == "asset"]
    assert assets and all(a["assignee_id"] == new_id for a in assets)
    assert all(a["status"] == "done" and a["output"] for a in assets)


def test_update_org_member_reprovisions_and_reroutes() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    ideation_bot = next(
        m for m in _org(app, lead)["members"] if m["display_name"] == "Ideation bot"
    )
    updated = _req(app, "POST", f"/api/v1/team/org/members/{ideation_bot['id']}", lead,
                   json={"provider": "openai", "model": "gpt-x", "job_description": "New job."})
    assert updated.status_code == 200
    body = updated.json()
    assert body["provider"] == "openai" and body["model"] == "gpt-x"
    assert body["job_description"] == "New job."
    # Untouched fields are preserved.
    assert body["agent_role"] == "ideation"
    assert body["handles_kinds"] == ["ideation"]


def test_org_config_is_lead_only() -> None:
    app, members = _build()
    sam = members["Sam (Writer)"]
    create = _req(app, "POST", "/api/v1/team/org/members", sam,
                  json={"display_name": "X", "role": "copywriter"})
    assert create.status_code == 403
    update = _req(app, "POST", f"/api/v1/team/org/members/{sam}", sam,
                  json={"job_description": "self-promotion"})
    assert update.status_code == 403


def test_org_create_rejects_bad_inputs() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    base = {"display_name": "Bot", "role": "copywriter"}

    assert _req(app, "POST", "/api/v1/team/org/members", lead,
                json={**base, "role": "nonexistent"}).status_code == 400
    assert _req(app, "POST", "/api/v1/team/org/members", lead,
                json={**base, "handles_kinds": ["asset", "bogus"]}).status_code == 400
    assert _req(app, "POST", "/api/v1/team/org/members", lead,
                json={**base, "reports_to": "no-such-member"}).status_code == 400
    # An empty display name fails validation (422).
    assert _req(app, "POST", "/api/v1/team/org/members", lead,
                json={"display_name": "  ", "role": "copywriter"}).status_code == 422


def test_update_rejects_agent_fields_on_a_human() -> None:
    app, members = _build()
    lead = members["Adam (Lead)"]
    rejected = _req(app, "POST", f"/api/v1/team/org/members/{lead}", lead,
                    json={"provider": "openai"})
    assert rejected.status_code == 400
