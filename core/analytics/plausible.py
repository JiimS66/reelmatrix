"""Plausible-backed attribution source — the first REAL conversion feed.

Chosen over GA4 for the first real connector because Plausible is
self-hostable: analytics data can stay inside the customer's environment,
matching the on-prem/open-model posture. Uses the Stats API v1 breakdown by
``visit:utm_content`` — one call for traffic, one goal-filtered call for
signup conversions — and joins rows back to posts by the utm_content tag
ReelMatrix mints.

Configuration::

    ANALYTICS_SOURCE=plausible
    PLAUSIBLE_BASE_URL=https://plausible.example.com   # self-hosted, or plausible.io
    PLAUSIBLE_SITE_ID=testsprite.com
    PLAUSIBLE_API_KEY=...
    PLAUSIBLE_SIGNUP_GOAL=Signup

Activation/paid stages intentionally stay 0 here — those are product events
and arrive through the first-party S2S endpoint, not web analytics.
"""

import httpx

from configs.settings import get_settings
from core.analytics.base import AnalyticsSource, AttributionRow

_TIMEOUT_SECONDS = 10.0


class PlausibleSource(AnalyticsSource):
    async def fetch_attribution(
        self, *, property_ref, utm_campaign, content_ids, start_date="", end_date=""
    ) -> list[AttributionRow]:
        settings = get_settings()
        site_id = (property_ref or settings.plausible_site_id or "").strip()
        api_key = (settings.plausible_api_key or "").strip()
        if not site_id or not api_key:
            raise RuntimeError(
                "PLAUSIBLE_SITE_ID and PLAUSIBLE_API_KEY are required for the "
                "plausible analytics source."
            )
        base = settings.plausible_base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {
            "site_id": site_id,
            "property": "visit:utm_content",
            "metrics": "visitors",
            "filters": f"visit:utm_campaign=={utm_campaign}",
            "limit": 200,
        }
        if start_date and end_date:
            params.update({"period": "custom", "date": f"{start_date},{end_date}"})
        else:
            params["period"] = "30d"

        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            traffic_response = await client.get(
                f"{base}/api/v1/stats/breakdown", params=params, headers=headers
            )
            traffic_response.raise_for_status()
            goal_response = await client.get(
                f"{base}/api/v1/stats/breakdown",
                params={
                    **params,
                    "filters": (
                        f"visit:utm_campaign=={utm_campaign};"
                        f"event:goal=={settings.plausible_signup_goal}"
                    ),
                },
                headers=headers,
            )
            goal_response.raise_for_status()

        def _by_content(payload: dict) -> dict[str, int]:
            return {
                str(row.get("utm_content", "")): int(row.get("visitors", 0))
                for row in payload.get("results", [])
            }

        traffic = _by_content(traffic_response.json())
        conversions = _by_content(goal_response.json())
        wanted = set(content_ids)
        rows: list[AttributionRow] = []
        for content_id in wanted & (set(traffic) | set(conversions)):
            visitors = traffic.get(content_id, 0)
            rows.append(
                AttributionRow(
                    utm_campaign=utm_campaign,
                    utm_content=content_id,
                    utm_source="plausible",
                    sessions=visitors,
                    clicks=visitors,
                    conversions=conversions.get(content_id, 0),
                )
            )
        return rows
