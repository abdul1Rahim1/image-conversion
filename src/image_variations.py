"""Generate variations of a product image via a pluggable provider."""

import asyncio
import base64
import io
from typing import Protocol

import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import CFG
from .prompts import VARIATION_PROMPTS


class ImageProvider(Protocol):
    async def edit(self, source_png: bytes, prompt: str) -> bytes: ...


class OpenAIProvider:
    def __init__(self) -> None:
        if not CFG.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for IMAGE_PROVIDER=openai")
        self.client = AsyncOpenAI(api_key=CFG.openai_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
    async def edit(self, source_png: bytes, prompt: str) -> bytes:
        # gpt-image-1 image.edit accepts a file-like object as "image"
        buf = io.BytesIO(source_png)
        buf.name = "source.png"
        resp = await self.client.images.edit(
            model=CFG.openai_image_model,
            image=buf,
            prompt=prompt,
            size=CFG.openai_image_size,
            quality=CFG.openai_image_quality,
            n=1,
        )
        b64 = resp.data[0].b64_json
        return base64.b64decode(b64)


class ReplicateProvider:
    """Flux Kontext (image-to-image edit) via Replicate."""

    def __init__(self) -> None:
        if not CFG.replicate_api_token:
            raise RuntimeError(
                "REPLICATE_API_TOKEN is required for IMAGE_PROVIDER=replicate"
            )
        import replicate  # local import so openai-only users don't need it
        self._replicate = replicate.Client(api_token=CFG.replicate_api_token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
    async def edit(self, source_png: bytes, prompt: str) -> bytes:
        # Replicate client is sync; run in a thread
        def _run() -> str | list:
            data_uri = "data:image/png;base64," + base64.b64encode(source_png).decode()
            return self._replicate.run(
                CFG.replicate_model,
                input={
                    "prompt": prompt,
                    "input_image": data_uri,
                    "output_format": "png",
                    "safety_tolerance": 2,
                },
            )

        result = await asyncio.to_thread(_run)
        url = result[0] if isinstance(result, list) else str(result)
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=120, follow_redirects=True)
            r.raise_for_status()
            return r.content


def make_provider() -> ImageProvider:
    if CFG.image_provider == "openai":
        return OpenAIProvider()
    if CFG.image_provider == "replicate":
        return ReplicateProvider()
    raise ValueError(f"Unknown IMAGE_PROVIDER: {CFG.image_provider}")


def _to_png(image_bytes: bytes) -> bytes:
    """Providers need PNG. Convert whatever the source URL served us."""
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


async def generate_variations(
    provider: ImageProvider,
    source_bytes: bytes,
    n: int,
) -> list[bytes]:
    png = _to_png(source_bytes)
    prompts = VARIATION_PROMPTS[:n] if n <= len(VARIATION_PROMPTS) else (
        VARIATION_PROMPTS * ((n // len(VARIATION_PROMPTS)) + 1)
    )[:n]

    tasks = [provider.edit(png, p) for p in prompts]
    return await asyncio.gather(*tasks)
