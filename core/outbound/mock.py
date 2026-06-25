"""Deterministic mock enrichment + per-lead personalization."""

from __future__ import annotations

from core.outbound.base import Enrichment, EnrichmentProvider


class MockEnrichmentProvider(EnrichmentProvider):
    """Stands in for one rung of a Clay-style waterfall. Returns None without a domain so
    the waterfall can fall through to the next provider."""

    def __init__(self, source: str = "mock-enrich") -> None:
        self.source = source

    def enrich(self, *, name: str, domain: str) -> Enrichment | None:
        if not domain:
            return None
        company = domain.split(".")[0].replace("-", " ").title()
        return Enrichment(
            source=self.source,
            company=company,
            title="Head of Engineering",
            signal=f"{company} is hiring AI engineers and shipping fast",
        )


def personalized_line(name: str, enrichment: Enrichment, value_prop: str) -> str:
    """A per-lead first line (the AI-research step, mock). A real impl prompts an LLM on
    the enrichment; here it's a deterministic template that reads naturally."""
    vp = (value_prop or "ship with confidence").rstrip(".")
    first = (name or "there").split()[0]
    return (
        f"Hi {first} — saw {enrichment.signal.lower()}. Teams like {enrichment.company} "
        f"use us to {vp.lower()}."
    )
