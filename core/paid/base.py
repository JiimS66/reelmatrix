"""Contracts for paid-creative scoring and budget allocation."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CreativeScoreProvider(ABC):
    @abstractmethod
    def score(self, *, headline: str, angle: str, channel: str) -> tuple[int, float]:
        """Pre-spend prediction: (creative_score 0–100, predicted_ctr %). AdCreative.ai
        scores creatives BEFORE spend; we extend our existing 0–100 content signal."""


class BudgetAllocator(ABC):
    @abstractmethod
    def allocate(self, scores: list[int], total: float) -> list[float]:
        """Split a total budget across variants (Advantage+/PMax reallocate to winners)."""
