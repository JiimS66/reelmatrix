"""DashScope-backed visual providers — the Qwen family, cloud side.

Decision (verified 2026-07): **Qwen-Image** for generation (Apache-2.0 family;
best-in-class in-image text rendering — the marketing-poster requirement) and
**Qwen3-VL** for understanding/critique (native image+video understanding).
The same model family ships open weights, so the on-prem story stays intact
(see ``core/media/zimage.py`` for the self-hosted generator).

Both providers speak DashScope's OpenAI-compatible endpoint with the same API
key the LLM layer already uses — going real is a config change:

    MEDIA_PROVIDER=dashscope
    VISION_PROVIDER=dashscope
"""

import json
from typing import Optional

import httpx

from configs.settings import get_settings
from core.media.base import (
    GeneratedImage,
    MediaCritique,
    MediaProvider,
    MediaUnderstanding,
    VisionProvider,
)

_TIMEOUT_SECONDS = 60.0
_DEFAULT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _base_url() -> str:
    settings = get_settings()
    return settings.resolved_dashscope_base_url or _DEFAULT_BASE


def _headers() -> dict:
    settings = get_settings()
    if not settings.dashscope_api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is required for the dashscope media/vision provider."
        )
    return {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }


class DashScopeMediaProvider(MediaProvider):
    """Text-to-image via Qwen-Image on DashScope (OpenAI-compatible images API)."""

    async def generate_image(
        self, *, prompt, brand=None, refs=None, controls=None, aspect_ratio="1:1"
    ) -> GeneratedImage:
        settings = get_settings()
        brand_hint = ""
        if brand:
            voice = str(brand.get("voice", "")).strip()
            if voice:
                brand_hint = f" Brand voice: {voice}."
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{_base_url()}/images/generations",
                headers=_headers(),
                json={
                    "model": settings.dashscope_image_model,
                    "prompt": f"{prompt}{brand_hint}",
                    "n": 1,
                    # DashScope accepts size strings; map the common ratios.
                    "size": {"1:1": "1024*1024", "16:9": "1664*928", "9:16": "928*1664"}.get(
                        aspect_ratio, "1024*1024"
                    ),
                },
            )
            response.raise_for_status()
            data = response.json().get("data", [])
        image_url = (data[0] or {}).get("url", "") if data else ""
        if not image_url:
            raise RuntimeError("DashScope returned no image.")
        return GeneratedImage(
            image_ref=image_url,
            aspect_ratio=aspect_ratio,
            provider="dashscope",
            model=settings.dashscope_image_model,
        )


class DashScopeVisionProvider(VisionProvider):
    """Qwen3-VL as the understanding/critique eye (VLM-as-judge)."""

    async def _chat(self, content: list) -> str:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{_base_url()}/chat/completions",
                headers=_headers(),
                json={
                    "model": settings.dashscope_vl_model,
                    "messages": [{"role": "user", "content": content}],
                },
            )
            response.raise_for_status()
            choices = response.json().get("choices", [])
        if not choices:
            raise RuntimeError("DashScope VL returned no choices.")
        return str(choices[0].get("message", {}).get("content", ""))

    async def understand(self, *, media_ref) -> MediaUnderstanding:
        text = await self._chat(
            [
                {"type": "image_url", "image_url": {"url": media_ref}},
                {
                    "type": "text",
                    "text": (
                        "Describe this marketing asset for a content team: one-sentence "
                        "summary, then up to 6 short tags. Answer as JSON "
                        '{"summary": str, "tags": [str]}.'
                    ),
                },
            ]
        )
        summary, tags = text.strip(), []
        try:
            parsed = json.loads(text)
            summary = str(parsed.get("summary", summary))
            tags = [str(t) for t in parsed.get("tags", [])]
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
        return MediaUnderstanding(summary=summary, tags=tags)

    async def critique(self, *, media_ref, campaign_text, brand=None) -> MediaCritique:
        brand_desc = json.dumps(brand or {}, ensure_ascii=False)
        text = await self._chat(
            [
                {"type": "image_url", "image_url": {"url": media_ref}},
                {
                    "type": "text",
                    "text": (
                        "You are a brand reviewer. Judge whether this image fits the "
                        f"campaign message: {campaign_text!r} and the brand: {brand_desc}. "
                        'Answer as JSON {"on_brand": bool, "issues": [str]} — issues '
                        "empty when it fits."
                    ),
                },
            ]
        )
        try:
            parsed = json.loads(text)
            return MediaCritique(
                on_brand=bool(parsed.get("on_brand", True)),
                issues=[str(issue) for issue in parsed.get("issues", [])],
            )
        except (json.JSONDecodeError, AttributeError, TypeError):
            # An unparseable verdict is surfaced, not swallowed — a human decides.
            return MediaCritique(on_brand=False, issues=[f"Unparseable critique: {text[:200]}"])
