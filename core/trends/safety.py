"""A pre-draft gate for a trend angle — fit + a brand-safety kill-switch.

Newsjacking's failure mode is jumping on a trending term without checking WHY it's
trending (the #Aurora / #WhyIStayed disasters). So sensitivity is a hard veto: a
sensitive angle is blocked from drafting regardless of how topically relevant it is —
never a deductible point. A safe angle gets a 0–100 fit score (relevance to the brand)
that orders, but does not gate, the draft.
"""

# Words that signal a tragedy / sensitive context — a hard block, not a deduction.
_SENSITIVE = (
    "shooting", "shooter", "massacre", "terror", "attack", "bombing", "explosion",
    "death", "died", "dead", "killed", "killing", "murder", "suicide", "tragedy",
    "disaster", "earthquake", "hurricane", "flood", "wildfire", "war", "genocide",
    "hostage", "assault", "abuse", "outbreak", "pandemic", "crisis", "layoffs",
)


def angle_safety(angle: str, brand_keywords: list[str]) -> dict:
    """{safe: bool, score: 0-100, reason: str} for a trend angle.

    ``safe=False`` blocks drafting (sensitivity veto). Otherwise ``score`` reflects how
    on-brand the angle is (more brand keywords present → higher), to order angles.
    """
    text = (angle or "").lower()
    hit = next((w for w in _SENSITIVE if w in text), None)
    if hit is not None:
        return {
            "safe": False,
            "score": 0,
            "reason": f"sensitive context ('{hit}') — do not newsjack; needs a human call",
        }
    matches = sum(1 for kw in (brand_keywords or []) if kw and kw.lower() in text)
    score = min(100, 55 + matches * 15) if angle.strip() else 0
    reason = "on-brand and safe" if matches else "safe, but relevance to the brand is loose"
    return {"safe": True, "score": score, "reason": reason}
