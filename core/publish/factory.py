"""Publish-provider factory — the single swap point for the publishing backend.

A real backend (Buffer's GraphQL/MCP fans out to many networks behind one token; or
per-platform native APIs) registers here; callers ask by name and never import a
concrete client. Most networks gate publishing behind app-review, so ``human_final``
mode stays the safe default until a provider is connected.
"""

from core.publish.base import PublishProvider
from core.publish.mock import MockPublishProvider


def create_publish_provider(name: str = "mock") -> PublishProvider:
    if name == "mock":
        return MockPublishProvider()
    raise ValueError(
        f"Unsupported publish provider '{name}'. Available: mock "
        "(buffer / per-platform native APIs plug in here — most need app-review)."
    )
