"""Category value pools for the murder mystery puzzle.

Each category has a pool of 12 values. get_schema(n, difficulty) returns the
first n values from active categories, suitable for a game with n players.

Category scaling is driven by difficulty level:

  Players  Easy  Medium  Hard
  4-6      3     4       5
  7-12     3     3       4

Categories drop in order (last dropped first):
  pet, house_color, drink, nationality, weapon
  (weapon is never dropped)
"""

from __future__ import annotations

CATEGORIES: dict[str, list[str]] = {
    "nationality": [
        "British",
        "Swedish",
        "Danish",
        "Norwegian",
        "German",
        "French",
        "Italian",
        "Spanish",
        "Japanese",
        "Brazilian",
        "Korean",
        "Mexican",
    ],
    "house_color": [
        "Red",
        "Green",
        "Blue",
        "Yellow",
        "White",
        "Ivory",
        "Purple",
        "Orange",
        "Pink",
        "Black",
        "Teal",
        "Crimson",
    ],
    "drink": [
        "Tea",
        "Coffee",
        "Milk",
        "Juice",
        "Wine",
        "Water",
        "Soda",
        "Lemonade",
        "Cocoa",
        "Cider",
        "Espresso",
        "Smoothie",
    ],
    "pet": [
        "Dog",
        "Cat",
        "Bird",
        "Fish",
        "Horse",
        "Snake",
        "Hamster",
        "Parrot",
        "Rabbit",
        "Turtle",
        "Gecko",
        "Ferret",
    ],
    "weapon": [
        "Knife",
        "Candlestick",
        "Revolver",
        "Rope",
        "Lead Pipe",
        "Wrench",
        "Poison",
        "Axe",
        "Crossbow",
        "Garrote",
        "Dagger",
        "Mace",
    ],
}

# The category used as the "character name" — each player gets one
NAME_CATEGORY = "name"

# The category whose value determines the murder weapon
WEAPON_CATEGORY = "weapon"


# Ordered list of categories from most to least droppable.
# weapon is never dropped.
_ALL_CATEGORIES = ["weapon", "nationality", "drink", "house_color", "pet"]

# Difficulty → number of puzzle categories by player tier.
#   Players  Easy  Medium  Hard  Harder  Hardest
#   4-6      3     4       5     5       5
#   7-12     3     3       4     4       4
_CATEGORY_COUNT: dict[str, tuple[int, int]] = {
    # (small_tier, large_tier)
    "easy": (3, 3),
    "medium": (4, 3),
    "hard": (5, 4),
    "harder": (5, 4),
    "hardest": (5, 4),
}


def get_active_categories(n: int, difficulty: str = "medium") -> list[str]:
    """Return the category names active for a game of size *n* and *difficulty*.

    Difficulty controls how many puzzle categories are used:
      Players  Easy  Medium  Hard
      4-6      3     4       5
      7-12     3     3       4
    """
    small, large = _CATEGORY_COUNT[difficulty]
    count = small if n <= 6 else large
    return list(_ALL_CATEGORIES[:count])


def get_schema(
    n: int,
    player_names: list[str] | None = None,
    difficulty: str = "medium",
) -> dict[str, list[str]]:
    """Return the first *n* values for each active category.

    Args:
        n: Number of positions/players (4-12).
        player_names: Player names to use for the "name" category.
            Required for actual game use. If omitted, generates
            placeholder names (useful for tests).
        difficulty: One of "easy", "medium", "hard".

    Raises ValueError if n < 4 or n > 12.
    """
    if not 4 <= n <= 12:
        raise ValueError(f"n must be between 4 and 12, got {n}")
    if player_names is not None and len(player_names) != n:
        raise ValueError(f"Expected {n} player names, got {len(player_names)}")

    active = get_active_categories(n, difficulty)
    schema = {cat: CATEGORIES[cat][:n] for cat in active}
    if player_names is not None:
        schema[NAME_CATEGORY] = list(player_names)
    else:
        schema[NAME_CATEGORY] = [f"Player {i + 1}" for i in range(n)]
    return schema
