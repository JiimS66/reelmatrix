"""Analytics-source factory — the single swap point for the conversion feed.

Real backends (GA4 Data API, Plausible, Fathom) register here; the only thing GA4
needs is a service-account JSON + a property id, so it is buildable without
app-review — callers ask for a source by name and never import a concrete client.
"""

from core.analytics.base import AnalyticsSource
from core.analytics.mock import MockGA4Source


def create_analytics_source(name: str = "mock") -> AnalyticsSource:
    if name == "mock":
        return MockGA4Source()
    if name == "plausible":
        from core.analytics.plausible import PlausibleSource

        return PlausibleSource()
    raise ValueError(
        f"Unsupported analytics source '{name}'. Available: mock, plausible "
        "(ga4 / fathom plug in here — GA4 needs a service account + property id)."
    )
