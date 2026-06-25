"""The MarketIntelProvider contract. Real providers (page-diff crawlers à la Crayon,
social listening à la Brandwatch, People-Also-Ask miners) swap in behind this; the
business code only sees MarketIntel."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CompetitorCard:
    name: str
    positioning: str
    recent_change: str  # the latest messaging diff, Crayon-style


@dataclass
class MarketIntel:
    competitors: list[CompetitorCard] = field(default_factory=list)
    audience_questions: list[str] = field(default_factory=list)  # PAA / autocomplete
    share_of_voice: dict[str, float] = field(default_factory=dict)  # name -> % of mentions
    whitespace: list[str] = field(default_factory=list)  # angles no competitor addresses


class MarketIntelProvider(ABC):
    @abstractmethod
    def intel(self, *, brand_keywords: list[str]) -> MarketIntel:
        """Current competitive + audience signal for a brand."""
