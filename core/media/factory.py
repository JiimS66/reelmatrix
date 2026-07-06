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
    if name == "dashscope":
        from core.media.dashscope import DashScopeMediaProvider

        return DashScopeMediaProvider()
    if name == "zimage":
        from core.media.zimage import ZImageMediaProvider

        return ZImageMediaProvider()
    raise ValueError(
        f"Unsupported media provider '{name}'. Available: mock, dashscope "
        "(Qwen-Image), zimage (self-hosted Z-Image-Turbo)."
    )


def create_vision_provider(name: str = "mock") -> VisionProvider:
    if name == "mock":
        return MockVisionProvider()
    if name == "dashscope":
        from core.media.dashscope import DashScopeVisionProvider

        return DashScopeVisionProvider()
    raise ValueError(
        f"Unsupported vision provider '{name}'. Available: mock, dashscope (Qwen3-VL)."
    )
