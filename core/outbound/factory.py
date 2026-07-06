"""Factories for outbound providers (mock waterfall + deliverability guard)."""

from __future__ import annotations

from core.outbound.base import DeliverabilityGuard, EnrichmentProvider
from core.outbound.mock import MockEnrichmentProvider


def create_enrichment_waterfall() -> list[EnrichmentProvider]:
    # A→B→C; a real waterfall mixes providers (Clearbit, Apollo, ZoomInfo, …).
    return [MockEnrichmentProvider("clearbit-mock"), MockEnrichmentProvider("apollo-mock")]


def create_deliverability_guard() -> DeliverabilityGuard:
    return DeliverabilityGuard()
