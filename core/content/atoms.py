"""Extract reusable named content atoms from an approved asset.

Auto-atomize on approval: each approved asset contributes structured, reusable
named blocks (headline, CTA, hook) to the tenant's atom library. Extraction is
deterministic — it reads the asset's structured fields, no guessing.
"""

ATOM_KINDS = ("headline", "hook", "cta", "proof", "one_liner")


def atoms_from_asset(asset: dict) -> list[tuple[str, str]]:
    """Return (kind, text) pairs to harvest from an approved asset."""
    atoms: list[tuple[str, str]] = []
    title = str(asset.get("title") or "").strip()
    if title:
        atoms.append(("headline", title))
    cta = str(asset.get("call_to_action") or "").strip()
    if cta:
        atoms.append(("cta", cta))
    content = str(asset.get("content") or "").strip()
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
    if first_line and first_line != title:
        atoms.append(("hook", first_line))
    return atoms
