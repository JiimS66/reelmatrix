from core.content.platform_specs import (
    format_checks,
    spec_for_channel,
    validate_format,
)


def test_spec_for_channel_is_case_insensitive() -> None:
    assert spec_for_channel("LinkedIn") is spec_for_channel("linkedin")
    assert spec_for_channel("  X / Twitter ").channel == "X / Twitter"
    assert spec_for_channel("unknown-channel") is None


def test_validate_format_flags_overlong_thread_without_cta() -> None:
    spec = spec_for_channel("X / Twitter")  # 280 char budget, thread format
    asset = {"content": "x" * 500, "call_to_action": ""}
    codes = {issue.code for issue in validate_format(asset, spec)}
    assert {"too_long", "missing_cta", "thin_thread"} <= codes


def test_validate_format_passes_a_clean_asset() -> None:
    spec = spec_for_channel("LinkedIn")
    asset = {"content": "Short hook\n\nProof point", "call_to_action": "Join the waitlist"}
    assert validate_format(asset, spec) == []


def test_format_checks_serializes_and_is_empty_for_unknown_channel() -> None:
    assert format_checks({"content": "x", "call_to_action": "go"}, "unknown") == []
    issues = format_checks({"content": "x" * 5000, "call_to_action": ""}, "Landing Page")
    assert any(issue["code"] == "too_long" for issue in issues)
