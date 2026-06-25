"""Privacy primitives: PII detection/redaction + the egress decision object."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PiiSpan:
    entity_type: str  # EMAIL | PHONE | CARD | ...
    start: int
    end: int


@dataclass
class EgressVerdict:
    allow: bool
    masked_text: str
    action: str  # allow | mask | block
    reason: str


class PIIRedactor(ABC):
    @abstractmethod
    def analyze(self, text: str) -> list[PiiSpan]:
        """Locate PII spans (Presidio Analyzer shape)."""

    @abstractmethod
    def redact(self, text: str) -> str:
        """Return the text with PII replaced by <ENTITY> placeholders."""
