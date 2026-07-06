"""Hacker News trend source via the free Algolia search API (no key, no scraping).

The first REAL feed behind the ``TrendSource`` ABC — the mock stays the default
for dev/tests. Network failures degrade to an empty list so a dead feed never
breaks planning; the caller keeps whatever angles it already had.
"""

import httpx

from core.trends.base import TrendItem, TrendSource

_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
_TIMEOUT_SECONDS = 6.0


class HackerNewsTrendSource(TrendSource):
    async def fetch(self, *, query: str, limit: int = 5) -> list[TrendItem]:
        params = {
            "query": (query or "").strip(),
            "tags": "story",
            "hitsPerPage": max(1, min(limit, 20)),
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(_SEARCH_URL, params=params)
                response.raise_for_status()
                hits = response.json().get("hits", [])
        except (httpx.HTTPError, ValueError):
            return []
        items = [
            TrendItem(
                title=str(hit.get("title") or "").strip(),
                source="hackernews",
                url=str(
                    hit.get("url")
                    or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                ),
                score=int(hit.get("points") or 0),
            )
            for hit in hits
            if hit.get("title")
        ]
        return sorted(items, key=lambda item: item.score, reverse=True)[:limit]
