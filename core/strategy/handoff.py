"""Circuit A → B handoff: turn a locked one-page strategy into a campaign brief.

This is the "five-minute hook" — the moment the marketer stops thinking strategy and sees
their first real content. It translates the human's chosen audience + positioning angle out
of the StrategyDraft into the brief that circuit B (campaign instantiation + the agents)
already understands, so the first posts are drafted FROM the strategy, not from a blank form.

Pure + deterministic (no DB, no LLM) so the translation is unit-testable on its own. The
positioning angle and content pillars are folded into `user_prompt` (free text) rather than
added as new brief keys, because the brief is validated as a strict CampaignGenerationRequest
downstream — only its known fields (plus orchestration keys) may pass through."""

from __future__ import annotations

from core.content.platform_specs import spec_for_channel

# How sure the advisor was — used to pick the option the human is most likely to lead with
# when the caller doesn't pick one explicitly.
_CONFIDENCE_RANK = {"confirmed": 0, "likely": 1, "guess": 2}


def best_index(items: list[dict], key: str = "confidence") -> int:
    """The option to default to: highest confidence, earliest on ties."""
    if not items:
        return 0
    return min(
        range(len(items)),
        key=lambda i: _CONFIDENCE_RANK.get(items[i].get(key), 3),
    )


def supported_channels(proposed: list[str] | None) -> list[str]:
    """Keep only channels circuit B can actually render (a real platform spec exists),
    falling back to a sensible default so the hook never produces an empty campaign."""
    kept = [c for c in (proposed or []) if c and spec_for_channel(c) is not None]
    return kept or ["LinkedIn", "Email"]


def brief_from_strategy(
    draft: dict,
    *,
    product_name: str,
    audience_index: int | None = None,
    angle_index: int | None = None,
    channels: list[str] | None = None,
) -> dict:
    """Map a locked StrategyDraft + the chosen audience/angle into a campaign brief.

    `audience_index` / `angle_index` are the human's pick at lock time; when omitted we
    default to the highest-confidence option. Returns a brief carrying ONLY keys circuit B
    understands."""
    audiences = draft.get("audience_candidates") or []
    angles = draft.get("positioning_angles") or []
    if not audiences or not angles:
        raise ValueError("strategy draft has no audience/angle to hand off")

    pillars = [p for p in (draft.get("content_pillars") or []) if p]
    ai = best_index(audiences) if audience_index is None else audience_index
    gi = best_index(angles) if angle_index is None else angle_index
    if not (0 <= ai < len(audiences)) or not (0 <= gi < len(angles)):
        raise ValueError("audience_index / angle_index out of range")
    audience = audiences[ai]
    angle = angles[gi]

    selected = supported_channels(channels or draft.get("channels"))
    measure = (draft.get("measure") or "").strip() or "qualified signups per week"
    pillar_line = "; ".join(pillars) if pillars else "the core value"
    name = (product_name or "").strip() or "Our launch"

    return {
        "product_name": name[:120],
        "product_description": ((draft.get("understanding") or name).strip())[:600],
        "target_audience": (f'{audience["name"]} — {audience["pain"]}').strip()[:300],
        "marketing_goal": (f'Win {audience["name"]}: {measure}').strip()[:300],
        "user_prompt": (
            f'ready for planning: lead with the positioning "{angle["angle"]}" '
            f'({angle.get("rationale", "")}). Speak to {audience["name"]}, whose pain is: '
            f'{audience["pain"]} Build around these content pillars: {pillar_line}.'
        ).strip(),
        "selected_channels": selected,
    }
