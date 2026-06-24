import asyncio

import pytest

from core.media.base import GeneratedImage, MediaCritique, MediaUnderstanding
from core.media.factory import create_media_provider, create_vision_provider


def test_mock_media_provider_is_deterministic() -> None:
    provider = create_media_provider("mock")
    a = asyncio.run(provider.generate_image(prompt="a clean hero image", aspect_ratio="16:9"))
    b = asyncio.run(provider.generate_image(prompt="a clean hero image", aspect_ratio="16:9"))
    c = asyncio.run(provider.generate_image(prompt="a different prompt"))
    assert isinstance(a, GeneratedImage)
    assert a.image_ref.startswith("mock://image/")
    assert a.aspect_ratio == "16:9" and a.provider == "mock"
    assert a.image_ref == b.image_ref  # same prompt -> stable ref
    assert a.image_ref != c.image_ref  # different prompt -> different ref


def test_mock_vision_provider_understands_and_critiques() -> None:
    provider = create_vision_provider("mock")
    understanding = asyncio.run(provider.understand(media_ref="mock://image/abc"))
    critique = asyncio.run(
        provider.critique(media_ref="mock://image/abc", campaign_text="launch", brand={})
    )
    assert isinstance(understanding, MediaUnderstanding) and understanding.tags == ["mock"]
    assert isinstance(critique, MediaCritique) and critique.on_brand is True


def test_factory_rejects_unknown_providers() -> None:
    with pytest.raises(ValueError, match="Unsupported media provider"):
        create_media_provider("nope")
    with pytest.raises(ValueError, match="Unsupported vision provider"):
        create_vision_provider("nope")
