"""Per-platform format specs and a format validator.

A campaign asset is a per-platform rendering of the shared campaign content
core. Each platform has a format spec (length budget, structure, tone shift)
that drives generation and a validator that flags assets that break the
platform's format.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlatformSpec:
    channel: str
    asset_type: str
    format: str
    max_chars: Optional[int]
    structure: str
    tone_shift: str


@dataclass(frozen=True)
class FormatIssue:
    code: str
    detail: str


PLATFORM_SPECS: dict[str, PlatformSpec] = {
    "linkedin": PlatformSpec(
        "LinkedIn", "Social post", "short_post", 3000,
        "Hook, insight, proof, then CTA in short paragraphs", "Professional, founder-led",
    ),
    "x / twitter": PlatformSpec(
        "X / Twitter", "Launch thread", "thread", 280,
        "Numbered posts, one idea each, a strong first hook", "Punchy and concrete",
    ),
    "email": PlatformSpec(
        "Email", "Email", "email", 1500,
        "Subject, three short paragraphs, one CTA", "Direct and skimmable",
    ),
    "blog": PlatformSpec(
        "Blog", "Article", "long_form", None,
        "Title, intro, H2 sections, takeaway", "Technical and evidence-led",
    ),
    "github / cli": PlatformSpec(
        "GitHub / CLI", "Quickstart", "code_quickstart", None,
        "What and why, install, a minimal code block, next step", "Terse and copy-pasteable",
    ),
    "landing page": PlatformSpec(
        "Landing Page", "Hero", "landing_hero", 400,
        "Headline, subhead, a single CTA", "Bold and benefit-first",
    ),
    "community": PlatformSpec(
        "Community", "Community note", "short_post", 1200,
        "Context, value, a low-key invitation", "Peer and helpful",
    ),
}


def spec_for_channel(channel: str) -> Optional[PlatformSpec]:
    return PLATFORM_SPECS.get((channel or "").strip().lower())


def validate_format(asset: dict, spec: PlatformSpec) -> list[FormatIssue]:
    """Flag ways the asset breaks its platform's format."""
    issues: list[FormatIssue] = []
    content = str(asset.get("content") or "")
    if spec.max_chars is not None and len(content) > spec.max_chars:
        issues.append(
            FormatIssue(
                "too_long",
                f"{len(content)} chars exceeds the {spec.max_chars} budget for {spec.channel}",
            )
        )
    if not str(asset.get("call_to_action") or "").strip():
        issues.append(FormatIssue("missing_cta", f"{spec.channel} asset has no call to action"))
    if spec.format == "thread" and content.count("\n") < 2:
        issues.append(FormatIssue("thin_thread", "a thread should contain multiple posts"))
    return issues


def format_checks(asset: dict, channel: str) -> list[dict]:
    """Format issues as serializable dicts (empty list when the channel is unknown)."""
    spec = spec_for_channel(channel)
    if spec is None:
        return []
    return [{"code": issue.code, "detail": issue.detail} for issue in validate_format(asset, spec)]
