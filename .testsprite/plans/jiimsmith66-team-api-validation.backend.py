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


def assert_clean_4xx(response):
    assert 400 <= response.status_code < 500, response.text
    try:
        body = response.json()
    except Exception as exc:
        raise AssertionError(response.text) from exc
    assert "detail" in body, body


def test_team_api_validation():
    member_id = lead_id()
    headers = {"X-Member-Id": member_id, "Content-Type": "application/json"}

    invalid_session = requests.post(
        f"{BASE_URL}/api/v1/team/strategy/sessions",
        headers=headers,
        json={"inputs": "not-a-list"},
        timeout=20,
    )
    assert_clean_4xx(invalid_session)

    missing_campaign = requests.get(
        f"{BASE_URL}/api/v1/team/campaigns/not-a-real-campaign-id/board",
        headers={"X-Member-Id": member_id},
        timeout=20,
    )
    assert_clean_4xx(missing_campaign)

    missing_task = requests.get(
        f"{BASE_URL}/api/v1/team/tasks/not-a-real-task-id",
        headers={"X-Member-Id": member_id},
        timeout=20,
    )
    assert_clean_4xx(missing_task)


test_team_api_validation()
