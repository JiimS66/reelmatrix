from core.content.scoring import content_score


def _issue() -> dict:
    return {"code": "x", "detail": "y"}


def test_clean_content_scores_100() -> None:
    score = content_score({"format": [], "brand": [], "consistency": [], "audit": []})
    assert score["overall"] == 100
    assert all(v == 100 for v in score["dimensions"].values())


def test_a_heavier_dimension_hurts_more() -> None:
    brand_hit = content_score(
        {"format": [], "brand": [_issue()], "consistency": [], "audit": []}
    )
    format_hit = content_score(
        {"format": [_issue()], "brand": [], "consistency": [], "audit": []}
    )
    # A brand issue drops its dimension further than a format issue, and (being
    # weighted higher) drags the overall down more.
    assert brand_hit["dimensions"]["brand"] < format_hit["dimensions"]["format"]
    assert brand_hit["overall"] < format_hit["overall"] < 100


def test_visual_brand_fit_is_scored() -> None:
    score = content_score({"brand_fit": [_issue()]})
    assert score["overall"] < 100
    assert "brand_fit" in score["dimensions"]


def test_non_scoreable_checks_return_none() -> None:
    assert content_score({}) is None
    assert content_score({"claim_checks": []}) is None
