"""Phase 8 — structured short-video generation behind the MediaProvider pattern. A post
becomes a VideoSpec (script → ordered scenes), which a VideoProvider renders. Mock-first:
the script is deterministic and render returns a manifest immediately; a real generator
(HeyGen/Synthesia-style async render + webhook) swaps in behind the same interface. This
is what finally makes "ReelMatrix" do reels.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass


@dataclass
class VideoScene:
    visual_prompt: str
    caption: str
    duration: float
    voiceover_text: str


class VideoProvider(ABC):
    @abstractmethod
    def script(self, *, topic: str, copy: str, channel: str) -> list[VideoScene]:
        """Decompose a post into ordered scenes (the VideoSpec)."""

    @abstractmethod
    async def render(self, scenes: list[VideoScene]) -> dict:
        """Render the scenes → a manifest {status, video_ref, duration, scenes}."""


class MockVideoProvider(VideoProvider):
    def script(self, *, topic: str, copy: str, channel: str) -> list[VideoScene]:
        parts = [
            s.strip()
            for s in (copy or topic or "").replace("\n", " ").split(".")
            if s.strip()
        ][:3]
        if not parts:
            parts = [topic or "Your story"]
        roles = ["Hook", "Value", "CTA"]
        scenes: list[VideoScene] = []
        for i, text in enumerate(parts):
            label = roles[i] if i < len(roles) else "Scene"
            scenes.append(
                VideoScene(
                    visual_prompt=f"{label}: visualize “{text[:48]}”",
                    caption=text[:90],
                    duration=4.0,
                    voiceover_text=text,
                )
            )
        return scenes

    async def render(self, scenes: list[VideoScene]) -> dict:
        # The only async point — a real renderer is slow + webhook-driven; the mock
        # returns the manifest immediately so the contract is identical.
        return {
            "status": "rendered",
            "video_ref": f"mock-video://reel/{len(scenes)}-scenes",
            "duration": round(sum(s.duration for s in scenes), 1),
            "scenes": [asdict(s) for s in scenes],
        }


def create_video_provider(name: str = "mock") -> VideoProvider:
    return MockVideoProvider()
