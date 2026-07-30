"""End-to-end orchestrator: one product row → N new variants + rewritten copy."""

import asyncio
import random
import string
import traceback

import httpx
from tqdm.asyncio import tqdm_asyncio

from .config import CFG
from .content_rewrite import rewrite
from .image_variations import generate_variations, make_provider
from .io_utils import (
    already_processed_ids,
    append_output_row,
    download_bytes,
    finalize_output,
    load_rows,
)
from .metadata import scrub_and_randomize
from .storage import make_key, upload


CONTENT_TYPES = {
    "webp": "image/webp",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
}


NEW_ID_COL_PREFIX = "new_"
_ID_ALPHABET = string.ascii_uppercase + string.digits


def _new_asin_like(original: str) -> str:
    """Generate an ASIN-lookalike: 10 uppercase alphanumeric chars, B0-prefix."""
    length = max(len(original), 10) if original else 10
    body = "".join(random.choices(_ID_ALPHABET, k=length - 2))
    return f"B0{body}"


def build_fieldnames(rows: list[dict]) -> list[str]:
    """Union of every key across every input row, in first-seen order, plus
    the pipeline's added columns. Used as CSV header — irrelevant for JSON."""
    new_id_col = NEW_ID_COL_PREFIX + CFG.col_id
    priority = [
        CFG.col_id,
        new_id_col,
        CFG.col_title,
        CFG.col_description,
        CFG.col_image_url,
    ]
    tail = [f"variant_{i}_url" for i in range(1, CFG.variations_per_image + 1)]
    tail.append("error")

    seen: set[str] = set(priority) | set(tail)
    middle: list[str] = []
    for r in rows:
        for k in r.keys():
            k = str(k)
            if k not in seen:
                seen.add(k)
                middle.append(k)
    return priority + middle + tail


async def process_row(
    row: dict,
    provider,
    http: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    output_path: str,
    fieldnames: list[str],
) -> None:
    async with sem:
        pid = str(row.get(CFG.col_id, "")).strip()
        title = str(row.get(CFG.col_title, "") or "")
        desc = str(row.get(CFG.col_description, "") or "")
        image_url = str(row.get(CFG.col_image_url, "") or "").strip()

        new_id_col = NEW_ID_COL_PREFIX + CFG.col_id
        new_id = _new_asin_like(pid)

        # Preserve every input field. Overlay only what the pipeline changes
        # or adds (new_<id>, rewritten title/desc, variant URLs, error).
        out: dict = dict(row)
        out[new_id_col] = new_id
        out["error"] = ""
        for i in range(1, CFG.variations_per_image + 1):
            out.setdefault(f"variant_{i}_url", "")

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
                key = make_key(new_id or "product", idx, ext)
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

        append_output_row(output_path, out, fieldnames)


async def run(input_path: str, output_path: str) -> None:
    rows = load_rows(input_path)
    fieldnames = build_fieldnames(rows)
    done = already_processed_ids(output_path, CFG.col_id)
    todo = [r for r in rows if str(r.get(CFG.col_id, "")).strip() not in done]
    print(f"Loaded {len(rows)} rows; {len(done)} already processed; {len(todo)} to do.")

    if not todo:
        finalize_output(output_path)
        return

    provider = make_provider()
    sem = asyncio.Semaphore(CFG.concurrency)
    async with httpx.AsyncClient() as http:
        tasks = [
            process_row(r, provider, http, sem, output_path, fieldnames) for r in todo
        ]
        await tqdm_asyncio.gather(*tasks, desc="Products")

    finalize_output(output_path)
