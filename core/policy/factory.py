"""Factory for the policy gate (config-swappable; mock rule pack today)."""

from __future__ import annotations

from core.policy.base import PolicyGate
from core.policy.gate import RulePackPolicyGate


def create_policy_gate(name: str = "rules") -> PolicyGate:
    return RulePackPolicyGate()
