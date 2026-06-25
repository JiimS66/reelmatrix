"""Pluggable statistics for the experiment ledger. Default is Bayesian "chance to beat
control" — PostHog and GrowthBook both default to Bayesian because it answers "is the
variant better?" directly and is safe to peek at any time (no fixed-sample penalty),
which fits a low-traffic, human-in-the-loop tool. A frequentist provider can swap in
behind the same interface later.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Protocol


class _Arm(Protocol):
    impressions: int
    conversions: int


def _beta_mean_var(alpha: float, beta: float) -> tuple[float, float]:
    total = alpha + beta
    mean = alpha / total
    var = (alpha * beta) / (total * total * (total + 1.0))
    return mean, var


def _phi(z: float) -> float:
    """Standard-normal CDF."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


class StatsProvider(ABC):
    @abstractmethod
    def chance_to_beat_control(self, control: _Arm, variant: _Arm) -> float:
        """P(variant conversion-rate > control conversion-rate), in [0, 1]."""


class BayesianStatsProvider(StatsProvider):
    """Normal approximation to the difference of two Beta(1+conv, 1+imp-conv) posteriors.
    Deterministic (no sampling), so results are reproducible in tests; for the sample
    sizes a marketing team actually has this is indistinguishable from Monte-Carlo."""

    def chance_to_beat_control(self, control: _Arm, variant: _Arm) -> float:
        ac, bc = 1.0 + control.conversions, 1.0 + max(0, control.impressions - control.conversions)
        av, bv = 1.0 + variant.conversions, 1.0 + max(0, variant.impressions - variant.conversions)
        mc, vc = _beta_mean_var(ac, bc)
        mv, vv = _beta_mean_var(av, bv)
        sd = math.sqrt(vv + vc) or 1e-9
        return _phi((mv - mc) / sd)


def create_stats_provider(name: str = "bayesian") -> StatsProvider:
    # Only Bayesian today; the factory keeps the call site swappable.
    return BayesianStatsProvider()
