"""Swappable visual generation + understanding, mirroring the LLM provider factory.

The hard constraint (designed for model upgrades from day 1): business code depends
only on these interfaces, never on a concrete model, so swapping the image model is a
config change with no business-code change.

``MediaProvider`` turns a prompt (+ brand identity, reference images, layout controls)
into an image. ``VisionProvider`` does the reverse two jobs: **understand** a
human-provided image into a structured brief, and **critique** an image against the
campaign text + brand (a VLM-as-judge — the visual analogue of the text consistency
check). Implementations are local (ComfyUI / diffusers), hosted (Fal / Replicate /
Ideogram / DashScope), or mock.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class GeneratedImage:
    image_ref: str  # URL or data-ref to the rendered image
    aspect_ratio: str
    provider: str
    model: Optional[str] = None


@dataclass(frozen=True)
class MediaUnderstanding:
    summary: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MediaCritique:
    on_brand: bool
    issues: list[str] = field(default_factory=list)


class MediaProvider(ABC):
    @abstractmethod
    async def generate_image(
        self,
        *,
        prompt: str,
        brand: Optional[dict] = None,
        refs: Optional[list[str]] = None,
        controls: Optional[dict] = None,
        aspect_ratio: str = "1:1",
    ) -> GeneratedImage:
        """Render an image from a prompt, the brand identity, optional reference
        images (IP-Adapter / subject-driven personalization), and layout controls."""
        raise NotImplementedError


class VisionProvider(ABC):
    @abstractmethod
    async def understand(self, *, media_ref: str) -> MediaUnderstanding:
        """Read a human-provided image into a structured brief + reference tags."""
        raise NotImplementedError

    @abstractmethod
    async def critique(
        self, *, media_ref: str, campaign_text: str, brand: Optional[dict] = None
    ) -> MediaCritique:
        """Judge an image against the campaign text + brand (VLM-as-judge)."""
        raise NotImplementedError
