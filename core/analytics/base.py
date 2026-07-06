"""Pluggable conversion-attribution source, behind one interface.

The valuable, controllable signal is conversions on owned destinations attributed by
UTM (GA4 / Plausible / Fathom). An ``AnalyticsSource`` returns conversions grouped by
the UTM tags ReelMatrix already mints (``utm_campaign`` = the event slug,
``utm_content`` = the asset task id prefix), so rows join straight back to ``Post``.
Native social reach/impressions are the fragmented, app-review-gated part and stay out
of this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AttributionRow:
    utm_campaign: str
    utm_content: Optional[str]  # == Post.asset_task_id[:8], the join key
    utm_source: str = ""
    utm_medium: str = ""
    sessions: int = 0
    clicks: int = 0
    conversions: int = 0  # signups (top of the product funnel)
    activations: int = 0  # product-qualified: API key created / first run
    paid: int = 0  # paid conversions
    revenue: float = 0.0


class AnalyticsSource(ABC):
    @abstractmethod
    async def fetch_attribution(
        self,
        *,
        property_ref: str,
        utm_campaign: str,
        content_ids: list[str],
        start_date: str = "",
        end_date: str = "",
    ) -> list[AttributionRow]:
        """Conversions grouped by UTM for one campaign, restricted to ``content_ids``
        (a real source queries by ``utm_campaign`` and filters to these)."""
        raise NotImplementedError
