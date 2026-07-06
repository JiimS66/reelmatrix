"""Brand consistency checks.

Deterministic checks first: forbidden wording is a hard, cheap signal. Tone /
voice judging (LLM-based) is a later layer. Checks are advisory — they surface
issues to the human reviewer rather than hard-blocking.
"""


def _asset_text(asset: dict) -> str:
    parts = [str(asset.get(key) or "") for key in ("title", "content", "call_to_action")]
    return " ".join(parts).lower()


def forbidden_word_issues(asset: dict, forbidden_words: list[str]) -> list[dict]:
    """Flag forbidden brand wording present anywhere in the asset copy."""
    text = _asset_text(asset)
    issues: list[dict] = []
    for word in forbidden_words or []:
        normalized = (word or "").strip().lower()
        if normalized and normalized in text:
            issues.append(
                {"code": "forbidden_word", "detail": f"uses forbidden wording: {word}"}
            )
    return issues
