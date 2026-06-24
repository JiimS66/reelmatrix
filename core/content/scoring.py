"""A 0–100 content score derived from the per-task checks.

Turns the existing check groups (format/brand/consistency/audit for posts,
brand_fit for visuals) into a legible, sellable number — the visible face of the
deterministic checks + the cross-model Auditor. Modeled on the established pattern
(e.g. Acrolinx): a per-dimension score that decays with issue count, then a weighted
average across dimensions. See https://support.acrolinx.com/hc/en-us/articles/10210995244178-The-Acrolinx-Score-Explained
"""

from typing import Optional

# Per-dimension tolerance (lower = each issue hurts more) and weight in the overall.
# Truth/brand dimensions matter more than format.
_BASE = {"format": 5, "brand": 2, "consistency": 2, "audit": 3, "brand_fit": 3}
_WEIGHT = {"format": 1, "brand": 2, "consistency": 2, "audit": 2, "brand_fit": 2}


def _dimension_score(dimension: str, issue_count: int) -> int:
    base = _BASE.get(dimension, 4)
    return round(100 * base / (base + issue_count))


def content_score(checks: dict) -> Optional[dict]:
    """{"overall": int, "dimensions": {name: int}} from a task's checks, or None when
    the task has no scoreable checks (ideation/planning/claim-check)."""
    scoreable = {
        name: issues for name, issues in (checks or {}).items() if name in _BASE
    }
    if not scoreable:
        return None
    dimensions = {
        name: _dimension_score(name, len(issues or [])) for name, issues in scoreable.items()
    }
    total_weight = sum(_WEIGHT[name] for name in dimensions)
    overall = round(
        sum(dimensions[name] * _WEIGHT[name] for name in dimensions) / total_weight
    )
    return {"overall": overall, "dimensions": dimensions}
