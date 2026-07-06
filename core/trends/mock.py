"""Deterministic mock trend source for dev and tests.

Echoes the query into stable, source-tagged items so the trend → angle flow is
exercisable before real feeds are wired in.
"""

from core.trends.base import TrendItem, TrendSource


class MockTrendSource(TrendSource):
    async def fetch(self, *, query: str, limit: int = 5) -> list[TrendItem]:
        topic = (query or "").strip() or "your market"
        seeds = [
            ("hackernews", f"Show HN: a faster way to {topic}", "https://news.ycombinator.com/"),
            ("reddit", f"r/startups is debating {topic} this week", "https://reddit.com/r/startups"),
            ("github", f"A trending repo tackles {topic}", "https://github.com/trending"),
            ("rss", f"Newsletter: why {topic} is having a moment", "https://example.com/feed"),
        ]
        return [
            TrendItem(title=title, source=source, url=url, score=100 - i * 7)
            for i, (source, title, url) in enumerate(seeds)
        ][:limit]
