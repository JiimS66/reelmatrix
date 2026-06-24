from core.content.brand import forbidden_word_issues


def test_forbidden_word_issues_flags_banned_wording() -> None:
    asset = {
        "title": "Bug-free testing",
        "content": "It is basically magic.",
        "call_to_action": "Try it",
    }
    issues = forbidden_word_issues(asset, ["bug-free", "magic", "unused-word"])
    assert [i["code"] for i in issues] == ["forbidden_word", "forbidden_word"]
    assert any("bug-free" in i["detail"] for i in issues)


def test_forbidden_word_issues_passes_clean_copy() -> None:
    asset = {
        "title": "Verification loop",
        "content": "Technical proof, no hype.",
        "call_to_action": "Start",
    }
    assert forbidden_word_issues(asset, ["bug-free", "magic"]) == []


def test_forbidden_word_issues_with_no_forbidden_list() -> None:
    assert forbidden_word_issues({"content": "anything"}, []) == []
