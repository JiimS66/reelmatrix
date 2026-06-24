from core.content.consistency import (
    approved_stat_text,
    campaign_content_core,
    unsourced_stat_issues,
)

PLAN = {
    "core_message": "Give teams a verification loop.",
    "content_pillars": ["trust", "speed"],
    "claim_checks": [
        {"claim": "TestSprite raised $6.7M in seed", "status": "source_backed"},
        {"claim": "users grew to 35,000", "status": "needs_validation"},
    ],
}


def test_content_core_keeps_only_source_backed_claims() -> None:
    core = campaign_content_core(PLAN)
    assert core["core_message"].startswith("Give teams")
    assert core["content_pillars"] == ["trust", "speed"]
    assert core["approved_claims"] == ["TestSprite raised $6.7M in seed"]


def test_unsourced_stat_is_flagged_but_approved_stat_is_not() -> None:
    approved = approved_stat_text(PLAN, [])  # contains $6.7M (source_backed), not 35,000
    asset = {"content": "We raised $6.7M and grew to 35,000 users.", "call_to_action": "x"}
    flagged = " ".join(i["detail"] for i in unsourced_stat_issues(asset, approved))
    assert "35,000" in flagged
    assert "$6.7M" not in flagged


def test_thread_position_markers_are_not_treated_as_stats() -> None:
    asset = {"content": "1/ first\n2/ second\n3/ third", "call_to_action": "x"}
    assert unsourced_stat_issues(asset, "") == []
