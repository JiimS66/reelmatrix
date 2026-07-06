# Auto-injected credentials — do not modify
__AUTH_CREDENTIAL__ = ""
__AUTH_TYPE__ = "public"
__AUTH_HEADERS__ = {}
import os

import requests


BASE_URL = os.environ.get("BASE_URL", "http://121.43.99.199:8000").rstrip("/")


def lead_id():
    response = requests.get(f"{BASE_URL}/api/v1/team/members", timeout=20)
    assert response.status_code == 200, response.text
    members = response.json()
    lead = next((m for m in members if m.get("display_name") == "Adam (Lead)"), None)
    assert lead, members
    return lead["id"]


def test_strategy_session_handoff():
    member_id = lead_id()
    headers = {"X-Member-Id": member_id, "Content-Type": "application/json"}

    started = requests.post(
        f"{BASE_URL}/api/v1/team/strategy/sessions",
        headers=headers,
        json={
            "inputs": [
                {
                    "type": "idea",
                    "value": "I built an AI tool that verifies AI-generated code before teams ship it.",
                }
            ]
        },
        timeout=60,
    )
    assert started.status_code == 200, started.text
    session = started.json()
    assert session.get("id"), session
    assert session.get("draft"), session
    draft = session["draft"]
    assert draft.get("audience_candidates"), draft
    assert draft.get("positioning_angles"), draft

    advanced = requests.post(
        f"{BASE_URL}/api/v1/team/strategy/sessions/{session['id']}/advance",
        headers=headers,
        json={
            "feedback": (
                "Focus on engineering managers who need confidence before merging "
                "AI-authored code."
            )
        },
        timeout=60,
    )
    assert advanced.status_code == 200, advanced.text
    next_session = advanced.json()
    assert next_session.get("turn_count", 0) >= session.get("turn_count", 0), next_session

    handoff = requests.post(
        f"{BASE_URL}/api/v1/team/strategy/sessions/{session['id']}/handoff",
        headers=headers,
        json={},
        timeout=90,
    )
    assert handoff.status_code == 200, handoff.text
    board = handoff.json()
    assert board.get("campaign"), board
    tasks = board.get("tasks")
    assert isinstance(tasks, list) and tasks, board
    kinds = {task.get("kind") for task in tasks}
    assert "ideation" in kinds, kinds
    assert "planning" in kinds, kinds
    assert any(kind in kinds for kind in ("asset", "visual", "claim_check")), kinds
    valid_statuses = {"todo", "in_progress", "needs_review", "done", "blocked"}
    assert all(task.get("status") in valid_statuses for task in tasks), tasks


test_strategy_session_handoff()