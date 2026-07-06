"""Factories for the privacy providers (mock-first; Presidio / real gateway later)."""

from __future__ import annotations

from core.privacy.base import PIIRedactor
from core.privacy.gate import EgressGate
from core.privacy.mock import MockPIIRedactor


def create_pii_redactor(name: str = "mock") -> PIIRedactor:
    return MockPIIRedactor()


def create_egress_gate(profile: str = "cloud") -> EgressGate:
    return EgressGate(profile)
