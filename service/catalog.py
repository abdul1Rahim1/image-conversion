"""In-memory catalog loaded from the Amazon-shape JSON file."""

import json
from pathlib import Path

from src.config import CFG


class Catalog:
    def __init__(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Catalog file not found: {path}")
        data = json.loads(p.read_text(encoding="utf-8"))
        rows = data["products"] if isinstance(data, dict) and "products" in data else data
        self._rows: list[dict] = list(rows)
        self._by_id: dict[str, dict] = {}
        for r in self._rows:
            pid = str(r.get(CFG.col_id, "")).strip()
            if pid:
                self._by_id[pid] = r

    def __len__(self) -> int:
        return len(self._rows)

    def get(self, product_id: str) -> dict | None:
        return self._by_id.get(product_id)

    def search(self, query: str, limit: int = 20) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return []
        terms = [t for t in q.split() if t]
        hits: list[tuple[int, dict]] = []
        for r in self._rows:
            title = str(r.get(CFG.col_title, "") or "").lower()
            category = str(r.get(CFG.col_description, "") or "").lower()
            haystack = f"{title} {category}"
            score = sum(1 for t in terms if t in haystack)
            if score:
                hits.append((score, r))
        hits.sort(key=lambda pair: (-pair[0], pair[1].get("Position") or 9999))
        return [r for _, r in hits[:limit]]
