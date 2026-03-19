#!/usr/bin/env python3
"""Pre-generate puzzles for every (player_count, difficulty) configuration.

Generates 3 puzzles per configuration and saves them as JSON to
backend/data/puzzles/{n}p_{difficulty}_{i}.json

Usage:
    cd backend && uv run python scripts/pregenerate.py
    cd backend && uv run python scripts/pregenerate.py --max-iterations 500
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Add parent dir so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.puzzle.pipeline import Puzzle, generate_puzzle

DIFFICULTIES = ["easy", "medium", "hard", "harder", "hardest"]
MIN_PLAYERS = 4
MAX_PLAYERS = 12
PUZZLES_PER_CONFIG = 3

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "puzzles"


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-generate murder mystery puzzles")
    parser.add_argument(
        "--max-iterations", type=int, default=100,
        help="Max iterations for clue selection (default 100, raise for large puzzles)",
    )
    parser.add_argument(
        "--max-attempts", type=int, default=10,
        help="Max retry attempts per puzzle (default 10)",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total = (MAX_PLAYERS - MIN_PLAYERS + 1) * len(DIFFICULTIES) * PUZZLES_PER_CONFIG
    generated = 0
    skipped = 0
    failed = 0

    print(f"Generating {total} puzzles into {OUTPUT_DIR}")
    print(f"  max_iterations={args.max_iterations}  max_attempts={args.max_attempts}\n")

    for n in range(MIN_PLAYERS, MAX_PLAYERS + 1):
        for difficulty in DIFFICULTIES:
            for i in range(PUZZLES_PER_CONFIG):
                label = f"n={n:2d}  {difficulty:<8s}  #{i + 1}"
                out_path = OUTPUT_DIR / f"{n}p_{difficulty}_{i}.json"

                if out_path.exists():
                    print(f"  {label}  SKIP (exists)")
                    skipped += 1
                    continue

                print(f"  {label}  ...", end="", flush=True)
                t0 = time.time()
                try:
                    puzzle = generate_puzzle(
                        n,
                        seed=n * 1000 + hash(difficulty) + i,
                        difficulty=difficulty,
                        max_attempts=args.max_attempts,
                        max_iterations=args.max_iterations,
                    )
                    data = puzzle.to_dict()
                    out_path.write_text(json.dumps(data, indent=2))
                    elapsed = time.time() - t0
                    print(f"  OK  ({elapsed:.1f}s)")
                    generated += 1
                except Exception as e:
                    elapsed = time.time() - t0
                    print(f"  FAIL ({elapsed:.1f}s): {e}")
                    failed += 1

    print(f"\nDone: {generated} generated, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
