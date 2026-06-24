"""Swappable publishing, behind one interface so business code never depends on a
specific network or aggregator.

A ``PublishProvider`` takes a rendered post and either publishes it, schedules it, or
stages it as a draft for a human to ship (``human_final`` — the honest default that
matches the real-world gates: Buffer's queue, TikTok's SELF_ONLY, anything pending an
app-review). Real backends (Buffer's GraphQL/MCP, or per-platform native APIs) plug in
behind the factory; most carry app-review/business-verification walls, which is exactly
why the interface lets a human be the final actuator.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PublishMode(str, Enum):
    AUTO = "auto"  # publish immediately
    SCHEDULED = "scheduled"  # queue for scheduled_at
    HUMAN_FINAL = "human_final"  # stage a draft; a human ships it in the tool


class PublishStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass(frozen=True)
class ChannelConstraints:
    max_chars: int
    max_media: int
    supports_video: bool = True
    supports_first_comment: bool = False
    supports_schedule: bool = True


@dataclass(frozen=True)
class PublishRequest:
    channel: str
    text: str
    link: Optional[str] = None  # the UTM-tagged destination
    media_refs: list[str] = field(default_factory=list)
    scheduled_at: Optional[str] = None
    metadata: dict = field(default_factory=dict)  # first_comment, ig_post_type, thread...


@dataclass(frozen=True)
class PublishResult:
    status: PublishStatus
    provider: str
    external_id: Optional[str] = None  # provider/platform post id
    permalink: Optional[str] = None  # public URL once live
    scheduled_at: Optional[str] = None
    error: Optional[str] = None


class PublishProvider(ABC):
    @abstractmethod
    def constraints(self, channel: str) -> ChannelConstraints:
        """Per-network limits so a post can be pre-flighted before publish."""
        raise NotImplementedError

    @abstractmethod
    async def publish(self, *, request: PublishRequest, mode: PublishMode) -> PublishResult:
        raise NotImplementedError
