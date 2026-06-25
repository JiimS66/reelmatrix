"""Deterministic mock market intelligence — structured, plausible signal so the brief's
market-context block and the UI are demoable with zero external calls. A real provider
(crawler + listening + PAA) swaps in behind the same MarketIntelProvider interface."""

from __future__ import annotations

from core.market.base import CompetitorCard, MarketIntel, MarketIntelProvider


class MockMarketIntelProvider(MarketIntelProvider):
    def intel(self, *, brand_keywords: list[str]) -> MarketIntel:
        kw = (brand_keywords[0] if brand_keywords else "the category").strip()
        competitors = [
            CompetitorCard(
                name="Rival A",
                positioning=f"Positions as the enterprise-grade option for {kw}.",
                recent_change="Headline shifted from 'fastest' to 'most trusted' last week.",
            ),
            CompetitorCard(
                name="Rival B",
                positioning=f"Targets indie developers doing {kw} on a budget.",
                recent_change="Launched a free tier; now leads with 'start in minutes'.",
            ),
        ]
        questions = [
            f"Is {kw} actually reliable enough to trust in production?",
            f"How is {kw} different from just writing tests myself?",
            f"What does {kw} cost for a small team?",
        ]
        sov = {"This brand": 22.0, "Rival A": 41.0, "Rival B": 37.0}
        whitespace = [
            f"No competitor speaks to the verification/trust anxiety around {kw} — own it.",
            "Nobody addresses the migration cost for teams switching tools.",
        ]
        return MarketIntel(
            competitors=competitors,
            audience_questions=questions,
            share_of_voice=sov,
            whitespace=whitespace,
        )
