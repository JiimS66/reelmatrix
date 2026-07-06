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


def assert_bad_request(response, expected):
    assert response.status_code == 400, response.text
    detail = response.json().get("detail", "")
    assert expected.lower() in str(detail).lower(), detail


def test_integrations_dispatch_guards():
    member_id = lead_id()
    headers = {"X-Member-Id": member_id, "Content-Type": "application/json"}

    missing_url = requests.post(
        f"{BASE_URL}/api/v1/team/integrations/dispatch",
        headers=headers,
        json={"target": "webhook", "title": "probe"},
        timeout=20,
    )
    assert_bad_request(missing_url, "url")

    private_url = requests.post(
        f"{BASE_URL}/api/v1/team/integrations/dispatch",
        headers=headers,
        json={
            "target": "webhook",
            "title": "probe",
            "url": "http://127.0.0.1:9000/internal",
        },
        timeout=20,
    )
    assert private_url.status_code == 400, private_url.text
    private_detail = private_url.json().get("detail", "")
    assert any(
        token in str(private_detail).lower()
        for token in ("private", "internal", "127.0.0.1", "localhost")
    ), private_detail

    missing_key = requests.post(
        f"{BASE_URL}/api/v1/team/integrations/dispatch",
        headers=headers,
        json={"target": "linear", "title": "probe"},
        timeout=20,
    )
    assert_bad_request(missing_key, "api_key")


test_integrations_dispatch_guards()
