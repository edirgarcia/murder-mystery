"""Random solution generation for the puzzle.

A *solution* is a dict mapping each category to a list of values, where
solution[cat][i] is the value assigned to position i (0-indexed).
"""

from __future__ import annotations

import random

from .schema import get_schema

Solution = dict[str, list[str]]


def generate_solution(
    n: int,
    rng: random.Random | None = None,
    player_names: list[str] | None = None,
    difficulty: str = "medium",
) -> Solution:
    """Generate a random valid solution for *n* positions.

    Each category's values are randomly permuted across the n positions.
    """
    rng = rng or random.Random()
    schema = get_schema(n, player_names=player_names, difficulty=difficulty)
    solution: Solution = {}
    for cat, values in schema.items():
        perm = list(values)
        rng.shuffle(perm)
        solution[cat] = perm
    return solution
