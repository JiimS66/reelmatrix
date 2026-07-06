"""Typed-terminology check — the governance layer above forbidden words.

Flags ``avoid`` terms (with the preferred replacement to suggest) and ``use_carefully``
terms (for a human double-check), in the same advisory ``{code, detail}`` shape as the
other checks. ``approved`` terms document house style and are not flagged.
"""


def _asset_text(asset: dict) -> str:
    return " ".join(str(asset.get(key) or "") for key in ("title", "content", "call_to_action"))


def term_issues(asset: dict, terms: list[dict]) -> list[dict]:
    text = _asset_text(asset)
    issues: list[dict] = []
    for term in terms or []:
        kind = term.get("term_type")
        if kind not in ("avoid", "use_carefully"):
            continue
        raw = (term.get("term") or "").strip()
        if not raw:
            continue
        case_sensitive = bool(term.get("case_sensitive"))
        haystack = text if case_sensitive else text.lower()
        needle = raw if case_sensitive else raw.lower()
        if needle not in haystack:
            continue
        if kind == "avoid":
            replacement = (term.get("replacement") or "").strip()
            detail = f'avoid "{raw}"' + (f' — use "{replacement}"' if replacement else "")
            issues.append({"code": "avoid_term", "detail": detail})
        else:
            issues.append(
                {"code": "use_carefully", "detail": f'"{raw}" needs careful use — check the context'}
            )
    return issues
