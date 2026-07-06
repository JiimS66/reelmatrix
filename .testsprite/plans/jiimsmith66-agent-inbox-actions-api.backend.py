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


def test_agent_inbox_actions_api():
    member_id = lead_id()
    headers = {"X-Member-Id": member_id}

    current = requests.get(f"{BASE_URL}/api/v1/team/actions", headers=headers, timeout=20)
    assert current.status_code == 200, current.text
    assert isinstance(current.json(), list), current.text

    planned = requests.post(f"{BASE_URL}/api/v1/team/actions/plan", headers=headers, timeout=30)
    assert planned.status_code == 200, planned.text
    actions = planned.json()
    assert isinstance(actions, list), actions
    for action in actions:
        for key in ("id", "type", "title", "rationale", "priority", "status", "payload"):
            assert key in action, action

    if actions:
        ignored = requests.post(
            f"{BASE_URL}/api/v1/team/actions/{actions[0]['id']}/ignore",
            headers=headers,
            timeout=20,
        )
        assert ignored.status_code == 200, ignored.text
        assert isinstance(ignored.json(), list), ignored.text


test_agent_inbox_actions_api()
