"""Deterministic mock media + vision providers for dev and tests.

The mock returns a stable, prompt-derived ``image_ref`` (no pixels) so the visual
pipeline is exercisable end-to-end before a real image model is wired in.
"""

import hashlib

from core.media.base import (
    GeneratedImage,
    MediaCritique,
    MediaProvider,
    MediaUnderstanding,
    VisionProvider,
)


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


class MockMediaProvider(MediaProvider):
    async def generate_image(
        self, *, prompt, brand=None, refs=None, controls=None, aspect_ratio="1:1"
    ) -> GeneratedImage:
        return GeneratedImage(
            image_ref=f"mock://image/{_digest(prompt)}",
            aspect_ratio=aspect_ratio,
            provider="mock",
        )


class MockVisionProvider(VisionProvider):
    async def understand(self, *, media_ref) -> MediaUnderstanding:
        return MediaUnderstanding(
            summary=f"Mock understanding of {media_ref}", tags=["mock"]
        )

    async def critique(self, *, media_ref, campaign_text, brand=None) -> MediaCritique:
        return MediaCritique(on_brand=True, issues=[])
