"""Murder chain logic.

Generates clues that form a deduction chain linking the murder weapon
to the murderer's identity. Players must combine these clues (spread across
different cards) to figure out who the killer is.

The chain length (number of hops) is controlled by difficulty:
  weapon → intermediate₁ → ... → name
"""

from __future__ import annotations

import random

from .clues import Clue, DirectEquality
from .generator import Solution
from .schema import NAME_CATEGORY, WEAPON_CATEGORY


def generate_murder_clues(
    solution: Solution,
    rng: random.Random | None = None,
    chain_hops: int | None = None,
) -> tuple[str, str, list[Clue]]:
    """Generate murder chain clues.

    Args:
        solution: The full puzzle solution.
        rng: Random instance for reproducibility.
        chain_hops: Number of links in the chain (weapon → ... → name).
            Must be >= 2. The number of intermediate categories needed is
            chain_hops - 1. If None, defaults to len(intermediates) + 1
            (i.e. uses all available intermediate categories).

    Returns:
        (murderer_name, murder_weapon, list_of_murder_clues)
    """
    rng = rng or random.Random()
    n = len(solution[NAME_CATEGORY])

    # Randomly pick a weapon from the solution
    murder_pos = rng.randrange(n)
    murder_weapon = solution[WEAPON_CATEGORY][murder_pos]
    murderer_name = solution[NAME_CATEGORY][murder_pos]

    # Pick intermediate categories (not name, not weapon)
    other_cats = [
        c for c in solution.keys() if c not in (NAME_CATEGORY, WEAPON_CATEGORY)
    ]
    rng.shuffle(other_cats)

    if chain_hops is None:
        # Default: use all available intermediates + 1
        chain_hops = len(other_cats) + 1

    intermediates_needed = chain_hops - 1
    if intermediates_needed > len(other_cats):
        raise ValueError(
            f"chain_hops={chain_hops} requires {intermediates_needed} intermediate "
            f"categories, but only {len(other_cats)} available"
        )

    # Build chain: weapon → cat₁ → cat₂ → ... → name
    chain_cats = other_cats[:intermediates_needed]
    clues: list[Clue] = []

    # First link: weapon → first intermediate
    prev_cat = WEAPON_CATEGORY
    prev_val = murder_weapon
    for cat in chain_cats:
        val = solution[cat][murder_pos]
        clues.append(DirectEquality(prev_cat, prev_val, cat, val))
        prev_cat = cat
        prev_val = val

    # Final link: last intermediate → name
    clues.append(DirectEquality(prev_cat, prev_val, NAME_CATEGORY, murderer_name))

    return murderer_name, murder_weapon, clues
