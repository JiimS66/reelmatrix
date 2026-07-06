"""Contracts for outbound enrichment + deliverability."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Enrichment:
    source: str
    company: str
    title: str
    signal: str  # the timely reason-to-reach-out


class EnrichmentProvider(ABC):
    @abstractmethod
    def enrich(self, *, name: str, domain: str) -> Enrichment | None:
        """Enrich a prospect, or None to fall through to the next provider (waterfall)."""


def enrich_waterfall(
    name: str, domain: str, providers: list[EnrichmentProvider]
) -> Enrichment | None:
    """Try providers A→B→C until one returns a hit (Clay-style waterfall)."""
    for provider in providers:
        hit = provider.enrich(name=name, domain=domain)
        if hit is not None:
            return hit
    return None


class DeliverabilityGuard:
    """Protect sender reputation: a per-day cap stands in for warmup ramp + mailbox
    rotation + bounce/spam auto-pause (Instantly/Smartlead)."""

    DAILY_CAP = 30

    def can_send(self, sent_today: int) -> tuple[bool, str]:
        if sent_today >= self.DAILY_CAP:
            return False, f"daily send cap reached ({self.DAILY_CAP}) — protect deliverability"
        return True, "ok"
