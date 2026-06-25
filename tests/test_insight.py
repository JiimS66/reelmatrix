from core.content.insight import predicted_performance


def test_a_post_gets_a_bounded_score_with_factors() -> None:
    out = {
        "content": "A punchy hook.\n\nClear value and proof for the reader.",
        "call_to_action": "Start now.",
    }
    pred = predicted_performance(out, "LinkedIn")
    assert pred and 0 <= pred["overall"] <= 100
    assert set(pred["factors"]) == {"hook", "cta", "length_fit", "clarity"}
    assert "directional" in pred["note"]  # honest-limits framing


def test_missing_cta_lowers_the_cta_factor() -> None:
    with_cta = predicted_performance(
        {"content": "Hook.\n\nValue.", "call_to_action": "Go."}, "LinkedIn"
    )
    without = predicted_performance(
        {"content": "Hook.\n\nValue.", "call_to_action": ""}, "LinkedIn"
    )
    assert with_cta["factors"]["cta"] > without["factors"]["cta"]


def test_none_for_empty_output() -> None:
    assert predicted_performance(None, "LinkedIn") is None
    assert predicted_performance({}, "LinkedIn") is None
