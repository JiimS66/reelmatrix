"""The ExperimentDesigner + a mock outcome simulator.

`design_variants` turns one brief into N variants PRE-TAGGED with the shared attribute
vocabulary, so every experiment doubles as a labeled training signal for the flywheel
(Optimizely Opal / AdCreative generate the variants; we additionally tag them). Mock-
first: variants are deterministic blueprints whose draft self-consistently carries those
attributes (so extract_attributes round-trips), and `simulated_outcome` fabricates
metrics for a demo. An LLM ExperimentDesigner + real GA4 swap in behind the same shapes.
"""

from __future__ import annotations

# control first; one arm per distinct attribute hypothesis.
_VARIANT_BLUEPRINTS = [
    {
        "key": "control",
        "attributes": {"hook_type": "statement", "cta_style": "soft", "length_bucket": "medium"},
        "rationale": "Baseline — plain statement, soft CTA, medium length.",
    },
    {
        "key": "A",
        "attributes": {"hook_type": "question", "cta_style": "direct", "length_bucket": "short"},
        "rationale": "Open with a curiosity question, direct CTA, tightened.",
    },
    {
        "key": "B",
        "attributes": {"hook_type": "stat", "cta_style": "curiosity", "length_bucket": "medium"},
        "rationale": "Lead with a hard stat, tease the CTA.",
    },
    {
        "key": "C",
        "attributes": {"hook_type": "bold_claim", "cta_style": "direct", "length_bucket": "short"},
        "rationale": "Bold claim + direct CTA, short.",
    },
]

_CTA_TEXT = {
    "direct": "Start free today",
    "curiosity": "See how it works",
    "soft": "More inside",
}
_LEN_WORDS = {"short": 30, "medium": 60, "long": 110}


def _draft_for(attributes: dict, hypothesis: str) -> dict:
    """A draft whose extracted attributes round-trip to ``attributes`` (self-consistent,
    so the variant's tags match what the flywheel would read off its content)."""
    topic = (hypothesis or "your workflow").strip().rstrip(".?!")
    hook = attributes.get("hook_type", "statement")
    if hook == "question":
        title = f"Still fighting {topic}?"
    elif hook == "stat":
        title = f"80% of teams get {topic} wrong"
    elif hook == "bold_claim":
        title = f"The only real fix for {topic}"
    elif hook == "how_to":
        title = f"How to fix {topic}"
    else:
        title = f"Rethinking {topic}"
    cta = _CTA_TEXT.get(attributes.get("cta_style", "soft"), "More inside")
    words = _LEN_WORDS.get(attributes.get("length_bucket", "medium"), 60)
    content = " ".join([topic] + ["value"] * words)
    return {"title": title, "content": content, "call_to_action": cta}


def design_variants(hypothesis: str, n: int = 3) -> list[dict]:
    """N variants (incl. one 'control'), each pre-tagged + drafted. n in [2, 4]."""
    count = max(2, min(n, len(_VARIANT_BLUEPRINTS)))
    out = []
    for bp in _VARIANT_BLUEPRINTS[:count]:
        out.append(
            {
                "key": bp["key"],
                "attributes": dict(bp["attributes"]),
                "rationale": bp["rationale"],
                "content": _draft_for(bp["attributes"], hypothesis),
            }
        )
    return out


def _simulated_cvr(attributes: dict) -> float:
    """A deterministic 'market' that rewards stronger attribute combos, so a demo run
    produces a clear winner. Mock only — real metrics come from GA4 via MetricSnapshot."""
    cvr = 0.03
    if attributes.get("hook_type") in ("question", "stat"):
        cvr += 0.03
    if attributes.get("cta_style") == "direct":
        cvr += 0.02
    if attributes.get("length_bucket") == "short":
        cvr += 0.01
    return cvr


def simulated_outcome(attributes: dict, base_impressions: int = 2000) -> tuple[int, int]:
    """(impressions, conversions) for a variant under the mock market."""
    conversions = round(base_impressions * _simulated_cvr(attributes))
    return base_impressions, conversions
