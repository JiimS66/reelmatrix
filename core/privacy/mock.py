"""Regex PII redactor (Presidio-shaped). Swap to Microsoft Presidio (Analyzer +
Anonymizer, runs fully offline) later — same interface, no caller change."""

from __future__ import annotations

import re

from core.privacy.base import PIIRedactor, PiiSpan

# Order matters for redact(): phone/card (long digit runs) before nothing else collides.
_PATTERNS = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("PHONE", re.compile(r"\b\+?\d[\d\s().-]{7,}\d\b")),
]


class MockPIIRedactor(PIIRedactor):
    def analyze(self, text: str) -> list[PiiSpan]:
        spans: list[PiiSpan] = []
        for entity_type, pattern in _PATTERNS:
            spans.extend(
                PiiSpan(entity_type, m.start(), m.end()) for m in pattern.finditer(text or "")
            )
        return spans

    def redact(self, text: str) -> str:
        out = text or ""
        for entity_type, pattern in _PATTERNS:
            out = pattern.sub(f"<{entity_type}>", out)
        return out
