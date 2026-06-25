"""On-prem privacy gates: PII redaction + the egress gate per deployment profile."""

from core.privacy.factory import create_egress_gate, create_pii_redactor


def test_pii_redactor_masks_email_and_phone() -> None:
    out = create_pii_redactor().redact("Reach Dana at dana@acme.dev or +1 415 555 1234.")
    assert "<EMAIL>" in out and "dana@acme.dev" not in out
    assert "<PHONE>" in out


def test_egress_gate_air_gapped_blocks_external() -> None:
    gate = create_egress_gate("air_gapped")
    assert gate.evaluate("anything", destination="external").allow is False
    # local destinations never leave the box → always allowed, even air-gapped.
    assert gate.evaluate("x", destination="local").allow is True


def test_egress_gate_hybrid_masks_pii_before_cloud() -> None:
    v = create_egress_gate("hybrid").evaluate("mail a@b.com", destination="cloud")
    assert v.allow and v.action == "mask" and "<EMAIL>" in v.masked_text


def test_egress_gate_cloud_allows() -> None:
    v = create_egress_gate("cloud").evaluate("hello", destination="cloud")
    assert v.allow and v.action == "allow"
