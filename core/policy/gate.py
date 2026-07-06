"""The rule-pack PolicyGate: run every rule, collect violations, allow unless any is a
block. Deterministic + pure, so it doubles as the asset 'policy' check and the pre-publish
gate."""

from __future__ import annotations

from core.policy.base import PolicyGate, PolicyVerdict
from core.policy.rules import RULES


class RulePackPolicyGate(PolicyGate):
    def evaluate(self, *, text: str, locale: str = "", channel: str = "") -> PolicyVerdict:
        ctx = {"locale": locale, "channel": channel}
        violations = [
            v for v in (rule(text or "", ctx) for rule in RULES) if v is not None
        ]
        allow = not any(v.severity == "block" for v in violations)
        return PolicyVerdict(allow=allow, violations=violations)


def policy_issues(text: str, *, locale: str = "", channel: str = "") -> list[dict]:
    """The PolicyGate verdict as a check-group payload (for asset.checks['policy'])."""
    verdict = RulePackPolicyGate().evaluate(text=text, locale=locale, channel=channel)
    return [
        {"rule": v.rule_id, "severity": v.severity, "message": v.message, "fix": v.fix}
        for v in verdict.violations
    ]
