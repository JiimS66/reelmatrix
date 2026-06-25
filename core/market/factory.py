"""Factory for the market-intelligence provider (env/config-swappable, mock-first)."""

from __future__ import annotations

from core.market.base import MarketIntelProvider
from core.market.mock import MockMarketIntelProvider


def create_market_provider(name: str = "mock") -> MarketIntelProvider:
    # Only the mock today; a real crawler/listening provider swaps in here.
    return MockMarketIntelProvider()
