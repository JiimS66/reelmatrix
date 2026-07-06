"""Factory for the import provider (mock-first; real connectors swap in here)."""

from __future__ import annotations

from core.ingest.base import ImportProvider
from core.ingest.mock import MockImportProvider


def create_import_provider(name: str = "mock") -> ImportProvider:
    return MockImportProvider()
