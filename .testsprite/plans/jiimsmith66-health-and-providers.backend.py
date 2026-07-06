import os

import requests


BASE_URL = os.environ.get("BASE_URL", "http://121.43.99.199:8000").rstrip("/")


def test_health_and_providers():
    health = requests.get(f"{BASE_URL}/health", timeout=20)
    assert health.status_code == 200, health.text
    body = health.json()
    assert body.get("status") == "ok", body
    assert isinstance(body.get("commit"), str) and body["commit"].strip(), body

    catalog = requests.get(f"{BASE_URL}/api/v1/llm/providers", timeout=20)
    assert catalog.status_code == 200, catalog.text
    data = catalog.json()
    providers = data.get("providers") if isinstance(data, dict) else data
    assert isinstance(providers, list) and providers, data
    defaults = []
    for provider in providers:
        for key in ("provider_id", "display_name", "model_name", "configured", "is_default"):
            assert key in provider, provider
        if provider["is_default"] is True:
            defaults.append(provider)
    assert len(defaults) == 1, providers


test_health_and_providers()
