"""Audit the output of the pipeline for leaks of the source data.

Downloads each variant image, scans its raw bytes and metadata for any
mention of the original image URL, original ID, brand-neutral scraper
markers ("amazon", "media-amazon"), and AI-provenance blocks (C2PA /
ContentCredentials). Also compares rewritten title/description against
the source to catch verbatim-copy laziness.

Usage:
    python verify.py <input.json> <output.json>

Prints a per-row PASS/FAIL summary and exits non-zero on any failure.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx


LEAK_TOKENS = ["amazon", "media-amazon", "amzn", "asin", "sspa"]
PROVENANCE_TOKENS = [b"c2pa", b"contentcredentials", b"jumbf", b"provenance"]


def _load(path: str):
    text = Path(path).read_text(encoding="utf-8")
    data = json.loads(text)
    return data["products"] if isinstance(data, dict) and "products" in data else data


def _bytes_scan(blob: bytes, needles: list[str | bytes]) -> list[str]:
    lower = blob.lower()
    hits = []
    for n in needles:
        needle = n.encode() if isinstance(n, str) else n
        if needle.lower() in lower:
            hits.append(n.decode() if isinstance(n, bytes) else n)
    return hits


def _verbatim_overlap(original: str, rewritten: str, min_run: int = 40) -> str | None:
    """Return the longest verbatim substring of length >= min_run shared
    between original and rewritten (case-insensitive, whitespace-normalized).
    None if the rewrite is genuinely different."""
    if not original or not rewritten:
        return None
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
    o, r = norm(original), norm(rewritten)
    for length in range(len(r), min_run - 1, -1):
        for start in range(0, len(r) - length + 1):
            chunk = r[start : start + length]
            if chunk in o:
                return chunk
    return None


def _get(row: dict, *candidates):
    for c in candidates:
        if c in row and row[c]:
            return row[c]
    return ""


def audit_row(orig: dict, out: dict, client: httpx.AsyncClient | httpx.Client) -> list[str]:
    problems: list[str] = []
    orig_url = str(_get(orig, "Image URL", "image_url"))
    orig_id = str(_get(orig, "ASIN", "id"))
    orig_title = str(_get(orig, "Title", "title"))
    orig_desc = str(_get(orig, "Category", "description"))

    id_tokens: list[str] = []
    if orig_id:
        id_tokens.append(orig_id)
    if orig_url:
        parsed = urlparse(orig_url)
        # last path segment (e.g. "61k2hb+jrIL._AC_UL320_.jpg")
        stub = parsed.path.rsplit("/", 1)[-1]
        if stub:
            id_tokens.append(stub)

    urls_to_check: list[tuple[str, str]] = []
    if out.get("image_url"):
        urls_to_check.append(("image", str(out["image_url"])))
    for i in range(1, 10):
        u = out.get(f"variant_{i}_url")
        if u:
            urls_to_check.append((f"variant_{i}", str(u)))

    for label, url in urls_to_check:
        try:
            r = client.get(url, timeout=60, follow_redirects=True)
            r.raise_for_status()
            blob = r.content
        except Exception as e:
            problems.append(f"{label}: download failed ({e})")
            continue

        text_leaks = _bytes_scan(blob, LEAK_TOKENS + id_tokens)
        if text_leaks:
            problems.append(f"{label}: leak in bytes → {text_leaks}")
        prov_hits = _bytes_scan(blob, PROVENANCE_TOKENS)
        if prov_hits:
            problems.append(f"{label}: AI-provenance metadata present → {prov_hits}")

    for field, orig_val in (("Title", orig_title), ("Category", orig_desc)):
        new_val = str(out.get(field, ""))
        overlap = _verbatim_overlap(orig_val, new_val, min_run=40)
        if overlap:
            problems.append(f"{field}: verbatim substring survived → {overlap!r}")

    combined = json.dumps(out, ensure_ascii=False).lower()
    if orig_url and orig_url.lower() in combined.replace(orig_url.lower(), "", 1).lower():
        # source URL is expected to appear once in Image URL passthrough;
        # flag only if it shows up in a second place
        problems.append("original image URL appears in more than one output field")

    return problems


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python verify.py <input.json> <output.json>")
        sys.exit(2)

    inputs = _load(sys.argv[1])
    outputs = _load(sys.argv[2])
    by_id = {}
    for i in inputs:
        key = str(i.get("ASIN") or i.get("id") or "")
        if key:
            by_id[key] = i

    fail_count = 0
    with httpx.Client() as client:
        for out in outputs:
            key = str(out.get("ASIN") or out.get("id") or "")
            orig = by_id.get(key, {})
            problems = audit_row(orig, out, client)
            if problems:
                fail_count += 1
                print(f"[FAIL] {key}")
                for p in problems:
                    print(f"       - {p}")
            else:
                print(f"[PASS] {key}")

    total = len(outputs)
    print(f"\n{total - fail_count}/{total} rows clean.")
    sys.exit(1 if fail_count else 0)


if __name__ == "__main__":
    main()
