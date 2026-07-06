from core.content.terminology import term_issues


def test_avoid_terms_flag_with_a_replacement_suggestion() -> None:
    asset = {"title": "x", "content": "We utilize synergy here.", "call_to_action": "go"}
    terms = [
        {"term": "utilize", "term_type": "avoid", "replacement": "use"},
        {"term": "synergy", "term_type": "avoid", "replacement": None},
    ]
    issues = term_issues(asset, terms)
    assert {i["code"] for i in issues} == {"avoid_term"}
    assert len(issues) == 2
    assert any('use "use"' in i["detail"] for i in issues)


def test_use_carefully_flags_softly() -> None:
    issues = term_issues(
        {"content": "we guarantee results"},
        [{"term": "guarantee", "term_type": "use_carefully"}],
    )
    assert issues and issues[0]["code"] == "use_carefully"


def test_approved_and_absent_terms_are_not_flagged() -> None:
    terms = [
        {"term": "agentic testing", "term_type": "approved"},
        {"term": "utilize", "term_type": "avoid"},
    ]
    assert term_issues({"content": "clean copy about agentic testing"}, terms) == []


def test_case_sensitivity_is_respected() -> None:
    terms = [{"term": "AI", "term_type": "avoid", "case_sensitive": True}]
    assert term_issues({"content": "plain ai text"}, terms) == []
    assert term_issues({"content": "uses AI now"}, terms)
