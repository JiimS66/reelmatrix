"""Circuit A (strategy co-creation) — the A→B handoff translation."""

import pytest

from core.strategy.handoff import (
    best_index,
    brand_updates_from_strategy,
    brief_from_strategy,
    supported_channels,
)

DRAFT = {
    "understanding": "You want to take an AI proofreader to market.",
    "audience_candidates": [
        {"name": "Skeptics", "why": "big but slow", "pain": "burned before", "confidence": "guess"},
        {"name": "Practitioners", "why": "feel it daily", "pain": "wasting time", "confidence": "confirmed"},
    ],
    "positioning_angles": [
        {"angle": "Proof over promises", "rationale": "counters skeptics", "confidence": "guess"},
        {"angle": "Fastest path to value", "rationale": "busy buyers", "confidence": "likely"},
    ],
    "content_pillars": ["Cost of the status quo", "How it works"],
    "channels": ["LinkedIn", "Email", "Community"],
    "measure": "qualified signups per week",
}


def test_best_index_prefers_highest_confidence_earliest_on_ties() -> None:
    assert best_index(DRAFT["audience_candidates"]) == 1  # confirmed beats guess
    assert best_index(DRAFT["positioning_angles"]) == 1  # likely beats guess
    assert best_index([]) == 0


def test_supported_channels_drops_unknown_and_never_empties() -> None:
    assert "TikTok" not in supported_channels(["LinkedIn", "TikTok"])  # no spec for TikTok
    assert supported_channels(["TikTok"]) == ["LinkedIn", "Email"]  # fallback
    assert supported_channels(None) == ["LinkedIn", "Email"]


def test_brief_defaults_to_the_confident_audience_and_angle() -> None:
    brief = brief_from_strategy(DRAFT, product_name="Lexi")
    # Defaults to the confirmed audience + the likely angle.
    assert "Practitioners" in brief["target_audience"]
    assert "wasting time" in brief["target_audience"]
    assert "Fastest path to value" in brief["user_prompt"]
    # The pillars steer planning via free text, not via extra brief keys.
    assert "Cost of the status quo" in brief["user_prompt"]
    assert brief["user_prompt"].startswith("ready for planning:")  # ideation proceeds
    # All three proposed channels have specs, so all survive.
    assert brief["selected_channels"] == ["LinkedIn", "Email", "Community"]
    # The campaign targets the promoted segment (the chosen audience), so it wins over any
    # pre-existing brand segments instead of falling back to all of them.
    assert brief["target_segments"] == ["Practitioners"]
    # Only keys circuit B understands — nothing that would break the strict agent schema.
    assert set(brief) == {
        "product_name", "product_description", "target_audience", "marketing_goal",
        "user_prompt", "selected_channels", "target_segments",
    }


def test_brand_updates_promote_audience_angle_and_pillars() -> None:
    u = brand_updates_from_strategy(DRAFT)
    seg = u["segment"]
    assert seg["name"] == "Practitioners"  # the confirmed audience
    assert seg["pain_points"] == ["wasting time"]
    assert seg["value_props"] == ["Fastest path to value"]  # the likely angle
    assert "LinkedIn" in seg["platforms"]
    assert u["value_proposition"].startswith("Fastest path to value")
    assert [p["name"] for p in u["messaging_pillars"]] == [
        "Cost of the status quo",
        "How it works",
    ]


def test_brief_honors_an_explicit_pick() -> None:
    brief = brief_from_strategy(DRAFT, product_name="Lexi", audience_index=0, angle_index=0)
    assert "Skeptics" in brief["target_audience"]
    assert "Proof over promises" in brief["user_prompt"]


def test_brief_rejects_an_out_of_range_pick() -> None:
    with pytest.raises(ValueError):
        brief_from_strategy(DRAFT, product_name="Lexi", audience_index=9)


def test_brief_needs_an_audience_and_angle() -> None:
    with pytest.raises(ValueError):
        brief_from_strategy({"audience_candidates": [], "positioning_angles": []}, product_name="X")
