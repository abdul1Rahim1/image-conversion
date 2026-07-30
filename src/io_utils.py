import csv
import json
import io
from pathlib import Path
from typing import Iterator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


def load_rows(path: str) -> list[dict]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict) and "products" in data:
            return list(data["products"])
        if isinstance(data, list):
            return data
        raise ValueError(f"Unrecognized JSON shape in {path}")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def write_output_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def append_output_row(path: str, row: dict, fieldnames: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    exists = p.exists()
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)


def already_processed_ids(path: str, id_field: str = "id") -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    with open(p, newline="", encoding="utf-8") as f:
        return {r[id_field] for r in csv.DictReader(f) if r.get(id_field)}


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=16))
async def download_bytes(url: str, client: httpx.AsyncClient) -> bytes:
    r = await client.get(url, timeout=60, follow_redirects=True)
    r.raise_for_status()
    return r.content
