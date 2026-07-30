"""CLI entry point.

Usage:
    python run.py <input.csv|input.json> <output.csv>
"""

import asyncio
import sys

from src.pipeline import run


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python run.py <input.csv|input.json> <output.csv>")
        sys.exit(2)
    asyncio.run(run(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
