"""A predicted-performance heuristic for a post — a DIFFERENT concept from the
conformance ``content_score`` (which measures checks): this estimates how the creative
itself is likely to perform, from signals the leaders use (hook, CTA, length fit,
clarity). It is explicitly directional — a heuristic, not a guarantee — and is kept as
a single function so a trained model can swap in behind it later.
"""

from typing import Optional

from core.content.platform_specs import spec_for_channel

_NOTE = "Predicted (heuristic) — directional, not a guarantee; confirm with a real test."


def predicted_performance(output: Optional[dict], channel: str) -> Optional[dict]:
    """{"overall": int, "factors": {name: int}, "note": str} for a post, or None."""
    if not output:
        return None
    content = str(output.get("content") or "")
    cta = str(output.get("call_to_action") or "").strip()
    if not content:
        return None

    first_line = content.split("\n", 1)[0].strip()
    hook = 90 if 0 < len(first_line) <= 90 else 65  # a punchy first line wins

    cta_score = 88 if cta else 45

    spec = spec_for_channel(channel)
    if spec is not None and spec.max_chars:
        ratio = len(content) / spec.max_chars
        length_fit = 90 if 0.15 <= ratio <= 1.0 else 55 if ratio > 1.0 else 70
    else:
        length_fit = 80

    clarity = 85 if 40 <= len(content) <= 1200 else 68

    factors = {
        "hook": hook,
        "cta": cta_score,
        "length_fit": length_fit,
        "clarity": clarity,
    }
    overall = round(sum(factors.values()) / len(factors))
    return {"overall": overall, "factors": factors, "note": _NOTE}
