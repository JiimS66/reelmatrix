from core.content.atoms import atoms_from_asset


def test_atoms_from_asset_extracts_named_blocks() -> None:
    asset = {
        "title": "Verify AI-generated code",
        "content": "The real gap is verification.\n\nMore detail here.",
        "call_to_action": "Start free",
    }
    atoms = dict(atoms_from_asset(asset))
    assert atoms["headline"] == "Verify AI-generated code"
    assert atoms["cta"] == "Start free"
    assert atoms["hook"] == "The real gap is verification."


def test_atoms_from_asset_skips_empty_fields() -> None:
    assert atoms_from_asset({"title": "", "content": "", "call_to_action": ""}) == []
