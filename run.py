"""CLI entry point.

Usage:
    python run.py <input.csv|input.json> <output.csv|output.json|output.jsonl>

Output format is chosen from the extension:
    .csv    → CSV with header row
    .jsonl  → newline-delimited JSON (one object per line, append-safe)
    .json   → single JSON array (aggregated at end; a .jsonl sidecar is
              maintained during the run for resumability)
"""

import asyncio
import sys

from src.pipeline import run


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage: python run.py <input.csv|input.json> "
            "<output.csv|output.json|output.jsonl>"
        )
        sys.exit(2)
    asyncio.run(run(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
