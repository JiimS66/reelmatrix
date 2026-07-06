"""Trend-source factory — the single swap point for the hot-topic feed.

Real backends (Reddit, Hacker News, GitHub Trending, RSS) register here; callers ask
for a source by name and never import a concrete feed.
"""

from core.trends.base import TrendSource
from core.trends.hackernews import HackerNewsTrendSource
from core.trends.mock import MockTrendSource


def create_trend_source(name: str = "mock") -> TrendSource:
    if name == "mock":
        return MockTrendSource()
    if name == "hackernews":
        return HackerNewsTrendSource()
    raise ValueError(
        f"Unsupported trend source '{name}'. Available: mock, hackernews "
        "(reddit/github/rss plug in here)."
    )
