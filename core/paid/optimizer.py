"""Phase 16 — global budget optimization across channels by MARGINAL ROI (the equimarginal
principle: shift budget until the next dollar returns the same everywhere). Mock Hill-
saturation response curves now; real MMM curves (PyMC-Marketing / Meridian) swap in behind
ChannelCurve later. Pure Python — a greedy marginal allocator, no scipy dependency."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChannelCurve:
    channel: str
    v_max: float  # saturation asymptote (max achievable response)
    k: float  # half-saturation spend


def _response(curve: ChannelCurve, spend: float) -> float:
    """Hill saturation (diminishing returns): v_max * spend / (k + spend)."""
    denom = curve.k + spend
    return (curve.v_max * spend / denom) if denom else 0.0


def _marginal(curve: ChannelCurve, spend: float, step: float) -> float:
    return (_response(curve, spend + step) - _response(curve, spend)) / step


def optimize_budget(curves: list[ChannelCurve], total: float, step: float = 50.0) -> dict:
    """Greedy equimarginal allocation: hand each increment to the channel with the highest
    marginal response, until the budget is spent. Returns per-channel allocation + the
    predicted response + the marginal ROI at that spend."""
    alloc = {c.channel: 0.0 for c in curves}
    spent = 0.0
    while spent + step <= total and curves:
        best = max(curves, key=lambda c: _marginal(c, alloc[c.channel], step))
        alloc[best.channel] += step
        spent += step
    rows = [
        {
            "channel": c.channel,
            "allocated": round(alloc[c.channel], 2),
            "predicted_response": round(_response(c, alloc[c.channel]), 1),
            "marginal_roi": round(_marginal(c, alloc[c.channel], step), 4),
        }
        for c in curves
    ]
    rows.sort(key=lambda r: -r["allocated"])
    return {"total_budget": total, "allocation": rows}
