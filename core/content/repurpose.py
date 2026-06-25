"""RepurposeProvider — atomize one pillar asset into channel derivatives (HubSpot
Content Remix / Jasper Campaigns turn one source into a cross-channel set). Mock returns
canned-but-tailored derivatives that inherit the pillar's gist + a rotating funnel stage,
so spokes stay consistent by construction; an LLM repurposer swaps in behind the same
interface later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Derivative:
    channel: str
    funnel_stage: str  # TOFU | MOFU | BOFU
    title: str
    content: str
    call_to_action: str


_FUNNEL_CTA = {
    "TOFU": "See how it works",
    "MOFU": "Compare your options",
    "BOFU": "Start free today",
}


class RepurposeProvider(ABC):
    @abstractmethod
    def atomize(
        self, *, pillar_title: str, source_text: str, channels: list[str]
    ) -> list[Derivative]:
        """One derivative per channel, each tagged to a funnel stage."""


class MockRepurposeProvider(RepurposeProvider):
    def atomize(
        self, *, pillar_title: str, source_text: str, channels: list[str]
    ) -> list[Derivative]:
        gist = (source_text or pillar_title).strip().split(".")[0][:140]
        stages = ["TOFU", "MOFU", "BOFU"]
        out: list[Derivative] = []
        for i, channel in enumerate(channels):
            stage = stages[i % len(stages)]
            out.append(
                Derivative(
                    channel=channel,
                    funnel_stage=stage,
                    title=f"{pillar_title} — for {channel}",
                    content=f"{gist}. (Repurposed for {channel}, {stage}.)",
                    call_to_action=_FUNNEL_CTA[stage],
                )
            )
        return out


def create_repurpose_provider(name: str = "mock") -> RepurposeProvider:
    return MockRepurposeProvider()
