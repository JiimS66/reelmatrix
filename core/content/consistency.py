"""Cross-platform consistency checks.

Every platform asset should render from one shared campaign content core, so
the message and the claims stay consistent across platforms. ``campaign_content_core``
makes that shared source explicit; ``unsourced_stat_issues`` flags an asset that
introduces a statistic not backed by an approved (source-backed) claim — the
deterministic half of cross-platform consistency and the claim/truth rail.
"""

import re

# Money, percentages, multipliers/magnitudes, and grouped thousands — but NOT
# bare small integers like the "1/" "2/" markers in a thread.
_STAT_RE = re.compile(
    r"\$\s?\d[\d,\.]*\s?(?:k|m|b|million|billion)?"
    r"|\d[\d,\.]*\s?%"
    r"|\d[\d,\.]*\s?(?:x|k|m|b|million|billion)\b"
    r"|\d{1,3}(?:,\d{3})+",
    re.IGNORECASE,
)


def campaign_content_core(plan: dict) -> dict:
    """The shared source every platform asset should render from."""
    return {
        "core_message": plan.get("core_message", ""),
        "content_pillars": plan.get("content_pillars") or [],
        "approved_claims": [
            claim.get("claim", "")
            for claim in (plan.get("claim_checks") or [])
            if claim.get("status") == "source_backed"
        ],
    }


def _norm(text: str) -> str:
    return "".join((text or "").lower().split())


def approved_stat_text(plan: dict, proof_points: list[dict]) -> str:
    """All text whose statistics are considered approved/sourced."""
    parts = [
        claim.get("claim", "")
        for claim in (plan.get("claim_checks") or [])
        if claim.get("status") == "source_backed"
    ]
    parts += [point.get("claim", "") for point in (proof_points or [])]
    return " ".join(parts)


def unsourced_stat_issues(asset: dict, approved_text: str) -> list[dict]:
    """Flag statistics in the asset that don't appear in an approved claim."""
    approved = _norm(approved_text)
    content = " ".join(
        str(asset.get(key) or "") for key in ("title", "content", "call_to_action")
    )
    issues: list[dict] = []
    seen: set[str] = set()
    for match in _STAT_RE.finditer(content):
        stat = match.group(0).strip()
        if not stat or stat in seen:
            continue
        seen.add(stat)
        if _norm(stat) not in approved:
            issues.append(
                {"code": "unsourced_stat", "detail": f"stat not backed by an approved claim: {stat}"}
            )
    return issues
