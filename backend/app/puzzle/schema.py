"""Category value pools for the murder mystery puzzle.

Each category has a pool of 10 values. get_schema(n) returns the first n values
from active categories, suitable for a game with n players/positions.

Category scaling by player count:
  n <= 4:  5 categories (all)
  n <= 6:  4 categories (drop pet)
  n <= 10: 3 categories (weapon + nationality + drink)
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
    ],
}

# The category used as the "character name" — each player gets one
NAME_CATEGORY = "name"

# The category whose value determines the murder weapon
WEAPON_CATEGORY = "weapon"


# Ordered list of categories from most to least droppable.
# weapon, nationality, drink are never dropped.
_ALL_CATEGORIES = ["weapon", "nationality", "drink", "house_color", "pet"]


def get_active_categories(n: int) -> list[str]:
    """Return the category names active for a game of size *n*.

    Fewer categories for more players keeps the puzzle tractable and the
    party experience snappy.

      n <= 4:  5 categories (all)
      n <= 6:  4 categories (drop pet)
      n <= 10: 3 categories (weapon + nationality + drink)
    """
    if n <= 4:
        return list(_ALL_CATEGORIES)  # 5
    if n <= 6:
        return _ALL_CATEGORIES[:4]  # drop pet
    return _ALL_CATEGORIES[:3]  # weapon, nationality, drink


def get_schema(n: int, player_names: list[str] | None = None) -> dict[str, list[str]]:
    """Return the first *n* values for each active category.

    Args:
        n: Number of positions/players (3-10).
        player_names: Player names to use for the "name" category.
            Required for actual game use. If omitted, generates
            placeholder names (useful for tests).

    Raises ValueError if n < 3 or n > 10.
    """
    if not 3 <= n <= 10:
        raise ValueError(f"n must be between 3 and 10, got {n}")
    if player_names is not None and len(player_names) != n:
        raise ValueError(f"Expected {n} player names, got {len(player_names)}")

    active = get_active_categories(n)
    schema = {cat: CATEGORIES[cat][:n] for cat in active}
    if player_names is not None:
        schema[NAME_CATEGORY] = list(player_names)
    else:
        schema[NAME_CATEGORY] = [f"Player {i + 1}" for i in range(n)]
    return schema
