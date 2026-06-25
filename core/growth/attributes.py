"""Heuristic content-attribute extraction — the shared vocabulary the growth loop
learns over (Persado / Adobe GenStudio do attribute-LEVEL learning, not per-post).
Mock-first: deterministic rules infer an attribute set from a rendered post; a real
classifier swaps in behind this same function later. Every loop (flywheel, experiments,
paid creative) reads and writes this same vocabulary, so winners are comparable.
"""

from __future__ import annotations

# The attribute types this extractor emits (the columns of the shared vocabulary).
ATTRIBUTE_TYPES = ("hook_type", "cta_style", "length_bucket")

_DIRECT_CTA = (
    "start", "sign up", "sign-up", "signup", "get ", "book", "buy", "try",
    "download", "join", "claim", "request", "register",
)
_CURIOSITY_CTA = ("see ", "discover", "find out", "learn ", "curious", "explore", "?")


def _word_count(text: str) -> int:
    return len([w for w in (text or "").split() if w])


def _hook_type(title: str, content: str) -> str:
    head = (title or content or "").strip()
    low = head.lower()
    if "?" in head:
        return "question"
    if low.startswith(("how ", "why ", "what ")) or "how to" in low or "ways to" in low:
        return "how_to"
    if any(ch.isdigit() for ch in head) or "%" in head:
        return "stat"
    if any(w in low for w in ("best", "only", "#1", "never", "stop ", "future of")):
        return "bold_claim"
    return "statement"


def _cta_style(cta: str) -> str:
    low = (cta or "").lower()
    if any(p in low for p in _CURIOSITY_CTA):
        return "curiosity"
    if any(p in low for p in _DIRECT_CTA):
        return "direct"
    return "soft"


def _length_bucket(content: str) -> str:
    n = _word_count(content)
    if n < 40:
        return "short"
    if n <= 90:
        return "medium"
    return "long"


def extract_attributes(output: dict | None) -> dict[str, str]:
    """The structured attribute tags for one rendered post — the unit the flywheel
    accumulates outcomes against. Tolerant of partial output (uses .get)."""
    if not output:
        return {}
    title = str(output.get("title") or "")
    content = str(output.get("content") or "")
    cta = str(output.get("call_to_action") or "")
    return {
        "hook_type": _hook_type(title, content),
        "cta_style": _cta_style(cta),
        "length_bucket": _length_bucket(content),
    }
