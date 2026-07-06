"""Z-Image-Turbo — the self-hosted / on-prem image generator.

Decision (verified 2026-07): Z-Image-Turbo (Tongyi-MAI, Apache 2.0, 6B) runs in
16GB consumer VRAM with sub-second inference — it drops the on-prem hardware
bar from datacenter GPUs to a single workstation card, which is what makes the
air-gapped deployment profile realistic for visuals.

Speaks a local OpenAI-style images endpoint (vLLM / diffusers server / ComfyUI
bridge — anything that serves ``POST {base}/images/generations``):

    MEDIA_PROVIDER=zimage
    ZIMAGE_BASE_URL=http://localhost:9800/v1
"""

import httpx

from configs.settings import get_settings
from core.media.base import GeneratedImage, MediaProvider

_TIMEOUT_SECONDS = 60.0


class ZImageMediaProvider(MediaProvider):
    async def generate_image(
        self, *, prompt, brand=None, refs=None, controls=None, aspect_ratio="1:1"
    ) -> GeneratedImage:
        settings = get_settings()
        base_url = (settings.zimage_base_url or "").rstrip("/")
        if not base_url:
            raise RuntimeError(
                "ZIMAGE_BASE_URL is required for the zimage media provider."
            )
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{base_url}/images/generations",
                json={
                    "model": "z-image-turbo",
                    "prompt": prompt,
                    "n": 1,
                    "size": {"1:1": "1024x1024", "16:9": "1664x928", "9:16": "928x1664"}.get(
                        aspect_ratio, "1024x1024"
                    ),
                },
            )
            response.raise_for_status()
            data = response.json().get("data", [])
        entry = (data[0] or {}) if data else {}
        image_ref = entry.get("url") or (
            f"data:image/png;base64,{entry['b64_json']}" if entry.get("b64_json") else ""
        )
        if not image_ref:
            raise RuntimeError("Z-Image server returned no image.")
        return GeneratedImage(
            image_ref=image_ref,
            aspect_ratio=aspect_ratio,
            provider="zimage",
            model="z-image-turbo",
        )
