"""Deterministic mock paid-creative scoring + proportional budget allocation."""

from __future__ import annotations

from core.paid.base import BudgetAllocator, CreativeScoreProvider


class MockCreativeScoreProvider(CreativeScoreProvider):
    def score(self, *, headline: str, angle: str, channel: str) -> tuple[int, float]:
        h = headline or ""
        s = 50
        if "?" in h:
            s += 10
        if any(c.isdigit() for c in h) or "%" in h:
            s += 15
        wc = len(h.split())
        if wc <= 8:
            s += 10
        elif wc > 16:
            s -= 10
        s = max(0, min(100, s))
        ctr = round(0.5 + s / 100 * 3.5, 2)  # 0.5–4.0% predicted CTR
        return s, ctr


class ProportionalBudgetAllocator(BudgetAllocator):
    def allocate(self, scores: list[int], total: float) -> list[float]:
        denom = sum(scores) or 1
        return [round(total * s / denom, 2) for s in scores]
