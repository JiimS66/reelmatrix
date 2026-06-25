"""The PolicyGate contract — callers pass structured input and get back a decision
object, never an enforcement side effect (OPA/Rego decoupling)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Violation:
    rule_id: str
    severity: str  # block | warn
    message: str
    fix: str


@dataclass
class PolicyVerdict:
    allow: bool  # False if ANY block-severity violation is present
    violations: list[Violation]


class PolicyGate(ABC):
    @abstractmethod
    def evaluate(self, *, text: str, locale: str = "", channel: str = "") -> PolicyVerdict:
        """Evaluate content against the rule pack; return allow + violations."""
