"""The EgressGate — gates text leaving the environment per DeploymentProfile (LiteLLM-
shaped MASK/BLOCK): air_gapped blocks any non-local destination; hybrid/on_prem mask PII
before a cloud call; cloud allows. Returns a decision object, like PolicyGate."""

from __future__ import annotations

from core.privacy.base import EgressVerdict, PIIRedactor
from core.privacy.mock import MockPIIRedactor

_LOCAL_DESTINATIONS = ("local", "on_box")


class EgressGate:
    def __init__(self, profile: str = "cloud", redactor: PIIRedactor | None = None) -> None:
        self.profile = profile
        self.redactor = redactor or MockPIIRedactor()

    def evaluate(self, text: str, *, destination: str = "cloud") -> EgressVerdict:
        if destination in _LOCAL_DESTINATIONS:
            return EgressVerdict(True, text or "", "allow", "local — never leaves the box")
        if self.profile == "air_gapped":
            return EgressVerdict(
                False, "", "block", "air-gapped: no data may leave the environment"
            )
        if self.profile in ("hybrid", "on_prem"):
            masked = self.redactor.redact(text or "")
            action = "mask" if masked != (text or "") else "allow"
            return EgressVerdict(True, masked, action, "PII masked before egress")
        return EgressVerdict(True, text or "", "allow", "cloud profile")
