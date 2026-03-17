"""Murder chain logic.

Generates 2-3 clues that form a deduction chain linking the murder weapon
to the murderer's identity. Players must combine these clues (spread across
different cards) to figure out who the killer is.
"""

from __future__ import annotations

import random

from .clues import Clue, DirectEquality
from .generator import Solution
from .schema import NAME_CATEGORY, WEAPON_CATEGORY


def generate_murder_clues(
    solution: Solution,
    rng: random.Random | None = None,
) -> tuple[str, str, list[Clue]]:
    """Generate murder chain clues.

    Returns:
        (murderer_name, murder_weapon, list_of_murder_clues)

    The chain works like:
      weapon=<chosen> -> intermediate_cat=some_value (clue 1)
      intermediate_cat=some_value -> name=murderer (clue 2)

    For larger games (n>=5), add a 3-clue chain through two intermediates.
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

    clues: list[Clue] = []

    if n >= 5 and len(other_cats) >= 2:
        # 3-clue chain: weapon -> cat_a -> cat_b -> name
        cat_a = other_cats[0]
        cat_b = other_cats[1]
        val_a = solution[cat_a][murder_pos]
        val_b = solution[cat_b][murder_pos]

        clues.append(DirectEquality(WEAPON_CATEGORY, murder_weapon, cat_a, val_a))
        clues.append(DirectEquality(cat_a, val_a, cat_b, val_b))
        clues.append(DirectEquality(cat_b, val_b, NAME_CATEGORY, murderer_name))
    else:
        # 2-clue chain: weapon -> cat_a -> name
        cat_a = other_cats[0]
        val_a = solution[cat_a][murder_pos]

        clues.append(DirectEquality(WEAPON_CATEGORY, murder_weapon, cat_a, val_a))
        clues.append(DirectEquality(cat_a, val_a, NAME_CATEGORY, murderer_name))

    return murderer_name, murder_weapon, clues
