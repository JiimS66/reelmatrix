"""Provider factories — the single swap point for the visual model.

New backends (HiDream-O1 / Ideogram / Qwen-Image / SDXL via local ComfyUI or hosted
Fal/Replicate/DashScope) register here; business code asks for a provider by name and
never imports a concrete model.
"""

from core.media.base import MediaProvider, VisionProvider
from core.media.mock import MockMediaProvider, MockVisionProvider


def create_media_provider(name: str = "mock") -> MediaProvider:
    if name == "mock":
        return MockMediaProvider()
    raise ValueError(
        f"Unsupported media provider '{name}'. Available: mock "
        "(local/hosted image models plug in here)."
    )


def create_vision_provider(name: str = "mock") -> VisionProvider:
    if name == "mock":
        return MockVisionProvider()
    raise ValueError(
        f"Unsupported vision provider '{name}'. Available: mock "
        "(a VLM like Qwen-VL plugs in here)."
    )
