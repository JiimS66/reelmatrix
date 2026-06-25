"""Deterministic mock import — normalizes rows + extracts a brand draft with zero
external calls. Real connectors (Splink dedup, LlamaIndex/Unstructured RAG ingestion, a
vision auto-tagger, a CRM/GA4 source) swap in behind the same interface."""

from __future__ import annotations

import re
from collections import Counter

from core.ingest.base import BrandDraft, HistoricalPost, ImportProvider


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


class MockImportProvider(ImportProvider):
    def parse_historical(self, rows: list[dict]) -> list[HistoricalPost]:
        out: list[HistoricalPost] = []
        for r in rows:
            out.append(
                HistoricalPost(
                    title=str(r.get("title", "")),
                    content=str(r.get("content", "")),
                    call_to_action=str(r.get("call_to_action") or r.get("cta") or ""),
                    channel=str(r.get("channel", "")),
                    segment=str(r.get("segment", "")),
                    impressions=_int(r.get("impressions")),
                    clicks=_int(r.get("clicks")),
                    conversions=_int(r.get("conversions") if r.get("conversions") is not None else r.get("signups")),
                    published_at=str(r.get("published_at") or r.get("date") or ""),
                )
            )
        return out

    def extract_brand(self, text: str) -> BrandDraft:
        sentences = [s.strip() for s in (text or "").replace("\n", " ").split(".") if s.strip()]
        value_proposition = sentences[0][:140] if sentences else ""
        # Recurring capitalized themes → messaging pillars (mock for an LLM extractor).
        themes = [w for w, _ in Counter(re.findall(r"\b[A-Z][a-z]{3,}\b", text or "")).most_common(3)]
        pillars = [{"name": t, "proof_points": []} for t in themes]
        low = (text or "").lower()
        tone_rules = []
        if any(k in low for k in ("concise", "clear", "simple")):
            tone_rules.append("Be concise and clear")
        if any(k in low for k in ("technical", "developer", "engineer")):
            tone_rules.append("Speak to a technical audience")
        return BrandDraft(
            voice="Derived from provided samples",
            tone_rules=tone_rules,
            forbidden_words=[],
            value_proposition=value_proposition,
            messaging_pillars=pillars,
            segments=[],
        )
