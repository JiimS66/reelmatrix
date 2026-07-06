"""Deterministic mock GA4 source — GA4-shaped conversion rows from the campaign slug
and the post content ids, reusing the same deterministic mock metrics, so the real
performance view runs end-to-end before GA4 credentials are connected.
"""

from core.analytics.base import AnalyticsSource, AttributionRow
from core.content.tracking import mock_metrics


class MockGA4Source(AnalyticsSource):
    async def fetch_attribution(
        self, *, property_ref, utm_campaign, content_ids, start_date="", end_date=""
    ) -> list[AttributionRow]:
        rows: list[AttributionRow] = []
        for content_id in content_ids:
            metrics = mock_metrics(f"{utm_campaign}:{content_id}")
            rows.append(
                AttributionRow(
                    utm_campaign=utm_campaign,
                    utm_content=content_id,
                    utm_source="owned",
                    utm_medium="social",
                    sessions=metrics["clicks"],
                    clicks=metrics["clicks"],
                    conversions=metrics["signups"],
                    activations=metrics["activations"],
                    paid=metrics["paid"],
                    revenue=metrics["signups"] * 49.0,
                )
            )
        return rows
