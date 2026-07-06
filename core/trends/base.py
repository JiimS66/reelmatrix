"""Pluggable hot-topic sources, behind one interface so business code never depends
on a specific feed.

Free sources first (Reddit hot/rising, Hacker News, GitHub Trending, RSS/news);
grayer optional plugins (Google Trends via pytrends, X via nitter/snscrape) and
relationship-based signals (the audience social graph) isolate behind the same
``TrendSource``. The campaign layer filters the items by brand/ICP and turns the
survivors into ``timely_angles`` that nudge the schedule.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TrendItem:
    title: str
    source: str  # reddit | hackernews | github | rss | ...
    url: str
    score: int = 0


class TrendSource(ABC):
    @abstractmethod
    async def fetch(self, *, query: str, limit: int = 5) -> list[TrendItem]:
        """Return the current hot items relevant to ``query`` (highest score first)."""
        raise NotImplementedError
