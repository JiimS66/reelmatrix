"""The ImportProvider contract + the structured records onboarding produces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class HistoricalPost:
    """One past piece of content + its measured outcome — the warm-start fuel."""

    title: str
    content: str
    call_to_action: str
    channel: str
    segment: str = ""
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    published_at: str = ""  # ISO date


@dataclass
class BrandDraft:
    """Structured brand knowledge extracted from docs/URL — a DRAFT the lead confirms
    before it commits to the live BrandProfile (Jasper's confirm-the-excerpt pattern)."""

    voice: str = ""
    tone_rules: list[str] = field(default_factory=list)
    forbidden_words: list[str] = field(default_factory=list)
    value_proposition: str = ""
    messaging_pillars: list[dict] = field(default_factory=list)
    segments: list[dict] = field(default_factory=list)


class ImportProvider(ABC):
    @abstractmethod
    def parse_historical(self, rows: list[dict]) -> list[HistoricalPost]:
        """Normalize raw imported rows (CSV/CRM/GA4 export) into HistoricalPosts."""

    @abstractmethod
    def extract_brand(self, text: str) -> BrandDraft:
        """Extract structured brand knowledge from unstructured docs/site text."""
