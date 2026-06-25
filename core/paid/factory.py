"""Factories for the paid-media providers (mock-first, config-swappable)."""

from __future__ import annotations

from core.paid.base import BudgetAllocator, CreativeScoreProvider
from core.paid.mock import MockCreativeScoreProvider, ProportionalBudgetAllocator


def create_creative_scorer(name: str = "mock") -> CreativeScoreProvider:
    return MockCreativeScoreProvider()


def create_budget_allocator(name: str = "proportional") -> BudgetAllocator:
    return ProportionalBudgetAllocator()
