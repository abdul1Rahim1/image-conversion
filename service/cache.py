"""SQLite-backed cache of materialized products."""

import json
import sqlite3
import time
from pathlib import Path


class Cache:
    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
              asin       TEXT PRIMARY KEY,
              status     TEXT NOT NULL,
              data       TEXT NOT NULL,
              updated_at INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def get(self, asin: str) -> dict | None:
        cur = self._conn.execute(
            "SELECT status, data FROM products WHERE asin = ?", (asin,)
        )
        row = cur.fetchone()
        if not row:
            return None
        status, data = row
        return {"status": status, "product": json.loads(data)}

    def put(self, asin: str, status: str, product: dict) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO products (asin, status, data, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (asin, status, json.dumps(product, ensure_ascii=False), int(time.time())),
        )
        self._conn.commit()

    def count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM products WHERE status = 'ready'")
        return cur.fetchone()[0]
