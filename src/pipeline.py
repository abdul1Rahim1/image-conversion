"""End-to-end orchestrator: one product row → N new variants + rewritten copy."""

import asyncio
import traceback

import httpx
from tqdm.asyncio import tqdm_asyncio

from .config import CFG
from .content_rewrite import rewrite
from .image_variations import generate_variations, make_provider
from .io_utils import already_processed_ids, append_output_row, download_bytes, load_rows
from .metadata import scrub_and_randomize
from .storage import make_key, upload


CONTENT_TYPES = {
    "webp": "image/webp",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
}


def _output_fieldnames() -> list[str]:
    fields = [CFG.col_id, CFG.col_title, CFG.col_description, CFG.col_image_url]
    for i in range(1, CFG.variations_per_image + 1):
        fields.append(f"variant_{i}_url")
    fields.append("error")
    return fields


async def process_row(
    row: dict,
    provider,
    http: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    output_path: str,
) -> None:
    async with sem:
        pid = str(row.get(CFG.col_id, "")).strip()
        title = str(row.get(CFG.col_title, "") or "")
        desc = str(row.get(CFG.col_description, "") or "")
        image_url = str(row.get(CFG.col_image_url, "") or "").strip()

        out: dict = {
            CFG.col_id: pid,
            CFG.col_title: title,
            CFG.col_description: desc,
            CFG.col_image_url: image_url,
            "error": "",
        }
        try:
            if not image_url:
                raise ValueError("empty image_url")

            source_bytes = await download_bytes(image_url, http)

            variants_task = generate_variations(
                provider, source_bytes, CFG.variations_per_image
            )
            rewrite_task = rewrite(title, desc)
            variants, (new_title, new_desc) = await asyncio.gather(
                variants_task, rewrite_task
            )

            out[CFG.col_title] = new_title
            out[CFG.col_description] = new_desc

            ext = CFG.output_format
            ctype = CONTENT_TYPES.get(ext, "application/octet-stream")

            async def _finalize(idx: int, raw: bytes) -> tuple[int, str]:
                scrubbed = await asyncio.to_thread(
                    scrub_and_randomize, raw, ext, CFG.output_quality
                )
                key = make_key(pid or "product", idx, ext)
                url = await upload(key, scrubbed, ctype)
                return idx, url

            results = await asyncio.gather(
                *[_finalize(i + 1, v) for i, v in enumerate(variants)]
            )
            for idx, url in results:
                out[f"variant_{idx}_url"] = url

        except Exception as e:
            out["error"] = f"{type(e).__name__}: {e}"
            traceback.print_exc()

        append_output_row(output_path, out, _output_fieldnames())


async def run(input_path: str, output_path: str) -> None:
    rows = load_rows(input_path)
    done = already_processed_ids(output_path, CFG.col_id)
    todo = [r for r in rows if str(r.get(CFG.col_id, "")).strip() not in done]
    print(f"Loaded {len(rows)} rows; {len(done)} already processed; {len(todo)} to do.")

    if not todo:
        return

    provider = make_provider()
    sem = asyncio.Semaphore(CFG.concurrency)
    async with httpx.AsyncClient() as http:
        tasks = [process_row(r, provider, http, sem, output_path) for r in todo]
        await tqdm_asyncio.gather(*tasks, desc="Products")
