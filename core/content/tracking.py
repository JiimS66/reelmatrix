"""UTM link generation and (mock) performance metrics for published assets.

The valuable, controllable signal is conversions on owned destinations (website
analytics + signup attribution via UTMs); social organic reach is the hard,
fragmented part. Until a real source is connected, metrics are deterministic
mocks so the performance view is demoable — a connector or a manual entry
(MetricSnapshot) overrides them.
"""

from hashlib import sha256
from urllib.parse import urlencode

from core.db.models import Campaign, Task

LANDING_BASE = "https://testsprite.com"

_CHANNEL_MEDIUM = {
    "linkedin": "social",
    "x / twitter": "social",
    "email": "email",
    "blog": "content",
    "github / cli": "referral",
    "landing page": "direct",
    "community": "community",
}


def _slug(value: str) -> str:
    return "-".join(value.lower().split())


def utm_url(campaign: Campaign, task: Task) -> str:
    """A UTM-tagged destination link encoding campaign, channel, and asset."""
    channel = ((task.params or {}).get("channel") or "").strip()
    source = _slug(channel.replace("/", " ")) or "campaign"
    medium = _CHANNEL_MEDIUM.get(channel.lower(), "referral")
    name = campaign.event_name or campaign.name
    query = urlencode(
        {
            "utm_source": source,
            "utm_medium": medium,
            "utm_campaign": _slug(name),
            "utm_content": task.id[:8],
        }
    )
    return f"{LANDING_BASE}/?{query}"


def mock_metrics(seed_id: str) -> dict:
    """Deterministic placeholder metrics derived from a stable id (e.g. post id).

    Funnel-shaped for a B2B dev tool: impressions → clicks → signups →
    activations (API key created / first run) → paid.
    """
    digest = int(sha256(seed_id.encode()).hexdigest(), 16)
    impressions = 1200 + digest % 6000
    clicks = round(impressions * (0.02 + (digest % 50) / 1000.0))  # ~2-7% CTR
    signups = round(clicks * (0.04 + (digest % 30) / 1000.0))  # ~4-7% conversion
    activations = round(signups * (0.35 + (digest % 20) / 100.0))  # ~35-55% activate
    paid = round(activations * (0.10 + (digest % 10) / 100.0))  # ~10-20% go paid
    return {
        "impressions": impressions,
        "clicks": clicks,
        "signups": signups,
        "activations": activations,
        "paid": paid,
        "source": "mock",
    }
