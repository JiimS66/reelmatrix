"""The rule pack — rules as data, each declaring its own severity + fix (Guardrails-AI
on_fail style). Add a rule by appending a function; a real deployment authors these as
YAML and could enforce via OPA/Rego, Presidio (PII), or transformer classifiers.
"""

from __future__ import annotations

import re

from core.policy.base import Violation

# Absolute superlatives — high-value because China Advertising Law fines run RMB 200k–1M
# for 最/第一-class claims; FTC also polices unqualified superlatives.
_SUPERLATIVES = (
    "最", "第一", "the best", "best-in-class", "#1", "number one", "world's leading",
    "guaranteed results", "100% effective", "the only",
)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\b\+?\d[\d\s().-]{8,}\d\b")
# Brand-safety / tragedy contexts — the newsjacking kill-switch, generalized to all output.
_SENSITIVE = (
    "death", "died", "tragedy", "shooting", "disaster", "war", "funeral",
    "outbreak", "layoff", "attack",
)
_PARTNER = ("sponsored", "in partnership", "paid partner", "#sponsored")


def _word_hit(text: str, terms) -> str | None:
    """First term present as a whole WORD (ascii letter terms / phrases) or as a substring
    (non-letter terms like 最 / 第一 / #1). Whole-word matching avoids 'war' in 'software'."""
    low = text.lower()
    for t in terms:
        tl = t.lower()
        compact = tl.replace(" ", "").replace("-", "")
        if tl.isascii() and compact.isalpha():
            if re.search(r"\b" + re.escape(tl) + r"\b", low):
                return t
        elif t in text or tl in low:
            return t
    return None


def superlative_rule(text: str, ctx: dict) -> Violation | None:
    hit = _word_hit(text, _SUPERLATIVES)
    if hit:
        return Violation(
            "superlatives", "block",
            f"Absolute superlative ('{hit.strip()}') risks ad-law violation "
            "(China Advertising Law / FTC unqualified-claim rules).",
            "Replace with a verifiable, sourced claim or drop the superlative.",
        )
    return None


def pii_rule(text: str, ctx: dict) -> Violation | None:
    if _EMAIL.search(text) or _PHONE.search(text):
        return Violation(
            "pii", "warn",
            "Appears to contain an email/phone number (PII).",
            "Remove personal contact details before publishing.",
        )
    return None


def brand_safety_rule(text: str, ctx: dict) -> Violation | None:
    hit = _word_hit(text, _SENSITIVE)
    if hit:
        return Violation(
            "brand_safety", "block",
            f"Sensitive/tragedy context ('{hit}') — don't publish without a human call.",
            "Pull the angle or get explicit human sign-off.",
        )
    return None


def disclosure_rule(text: str, ctx: dict) -> Violation | None:
    low = text.lower()
    mentions_partner = any(p in low for p in _PARTNER)
    has_disclosure = "#ad" in low or "advertisement" in low or "paid partnership" in low
    if mentions_partner and not has_disclosure:
        return Violation(
            "disclosure", "warn",
            "Mentions a paid/partner relationship without a clear #ad disclosure.",
            "Add a clear, conspicuous '#ad' / 'Paid partnership' disclosure (FTC).",
        )
    return None


RULES = (superlative_rule, pii_rule, brand_safety_rule, disclosure_rule)
