"""Graders — judge prompt as data. Each expectation maps to a scorer; mock-first scorers
reuse the existing deterministic gates (policy, GEO) so an eval run tests REAL logic with a
reproducible 0–1 score + reason. A real LLM-as-judge for subjective quality (brand voice,
persuasiveness) swaps in behind grade_case for new expectations."""

from __future__ import annotations

from core.content.geo import geo_issues
from core.policy.gate import policy_issues


def grade_case(input_text: str, expectation: str) -> dict:
    """Return {score 0–1, passed, reason} for one case under its expectation."""
    text = input_text or ""
    if expectation == "no_policy_block":
        blocks = [i for i in policy_issues(text) if i["severity"] == "block"]
        ok = not blocks
        return {
            "score": 1.0 if ok else 0.0,
            "passed": ok,
            "reason": "no policy block" if ok else f"blocked: {blocks[0]['rule']}",
        }
    if expectation == "geo_citable":
        gaps = geo_issues(text)
        score = round(max(0.0, 1.0 - len(gaps) * 0.25), 2)
        return {"score": score, "passed": score >= 0.5, "reason": f"{len(gaps)} GEO gap(s)"}
    return {"score": 1.0, "passed": True, "reason": "no grader for expectation"}


# The default suite seeded for a new tenant — exercises the compliance + GEO gates.
DEFAULT_CASES = [
    ("Clean compliant post", "We help engineering teams ship verified code faster.", "no_policy_block"),
    ("Superlative violation", "We are the best #1 tool, guaranteed results.", "no_policy_block"),
    ("Citable content", "Slow shipping? 80% of teams improve, according to our study.", "geo_citable"),
    ("Thin content", "We help teams ship faster.", "geo_citable"),
]
