"""Phase 11 — causal de-biasing of the flywheel.

The flywheel accumulates "this attribute co-occurred with conversions" = CORRELATION.
Causation needs a counterfactual: what would have happened anyway. An IncrementalityTest
(mock GeoHoldout — synthetic control on fabricated geo/time series) measures the truly
INCREMENTAL share of an attribute's naive conversions and returns a multiplier that scales
its "win" pseudo-count in the Beta update. A bold_claim hook may have a high naive CVR but
low incrementality (it just grabbed people who'd convert anyway) → multiplier < 1 → its
posterior is shrunk back toward baseline. Real GeoLift/CausalImpact swap in behind this.
"""

from __future__ import annotations

# Synthetic "fraction of naive credit that is truly incremental" per attribute value — the
# mock market. Values < 1 mean the attribute over-claims (correlation > causation).
_SYNTHETIC_LIFT = {
    "question": 0.95,
    "stat": 0.90,
    "statement": 1.05,
    "bold_claim": 0.55,  # eye-catching but largely captures already-converting intent
    "how_to": 1.00,
    "direct": 0.85,
    "curiosity": 1.10,
    "soft": 1.00,
    "short": 1.00,
    "medium": 1.00,
    "long": 0.95,
}


def measure_lift(attribute_value: str, naive_conversions: int) -> dict:
    """Mock GeoHoldout readout for one attribute. Returns the incremental conversions, the
    de-bias multiplier, and the lift %. Deterministic — no randomness."""
    frac = _SYNTHETIC_LIFT.get(attribute_value, 1.0)
    incremental = round(naive_conversions * frac)
    multiplier = (incremental / naive_conversions) if naive_conversions else 1.0
    return {
        "incremental_conversions": incremental,
        "multiplier": round(multiplier, 3),
        "lift_pct": round((frac - 1.0) * 100, 1),
    }
