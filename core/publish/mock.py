"""Deterministic mock publisher — stable mock permalinks, no network, so the publish
flow (draft → scheduled → published) runs end-to-end before a real provider is wired.
"""

import hashlib

from core.publish.base import (
    ChannelConstraints,
    PublishMode,
    PublishProvider,
    PublishRequest,
    PublishResult,
    PublishStatus,
)

# Per-network limits drawn from the platform docs (caption length, media, etc.).
_CONSTRAINTS: dict[str, ChannelConstraints] = {
    "linkedin": ChannelConstraints(3000, 9, True, True, True),
    "x / twitter": ChannelConstraints(280, 4, True, False, True),
    "email": ChannelConstraints(100000, 0, False, False, True),
    "instagram": ChannelConstraints(2200, 10, True, True, True),
    "landing page": ChannelConstraints(100000, 1, True, False, False),
}


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


class MockPublishProvider(PublishProvider):
    def constraints(self, channel: str) -> ChannelConstraints:
        return _CONSTRAINTS.get(
            (channel or "").strip().lower(),
            ChannelConstraints(2200, 10, True, True, True),
        )

    async def publish(self, *, request: PublishRequest, mode: PublishMode) -> PublishResult:
        ref = _digest(request.text)
        channel = (request.channel or "post").strip().lower().replace(" ", "")
        if mode == PublishMode.HUMAN_FINAL:
            return PublishResult(PublishStatus.DRAFT, "mock", external_id=f"mock-draft-{ref}")
        if mode == PublishMode.SCHEDULED:
            return PublishResult(
                PublishStatus.SCHEDULED, "mock",
                external_id=f"mock-{ref}", scheduled_at=request.scheduled_at,
            )
        return PublishResult(
            PublishStatus.PUBLISHED, "mock",
            external_id=f"mock-{ref}", permalink=f"mock://{channel}/{ref}",
        )
