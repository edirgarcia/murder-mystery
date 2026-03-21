"""Load pre-generated puzzles from disk and relabel them.

Relabeling swaps placeholder names for real player names and shuffles
category values (nationalities, weapons, etc.) so each game feels
different even when reusing the same structural puzzle.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from .distributor import PlayerCard, assign_rounds
from .pipeline import Puzzle
from .schema import CATEGORIES

# Lightweight Clue stand-in for loaded puzzles (already rendered to text).
# Matches the interface used by the game server: to_dict() and render().


class _LoadedClue:
    """A clue reconstructed from serialized text."""

    def __init__(self, clue_type: str, text: str) -> None:
        self._type = clue_type
        self._text = text

    def render(self) -> str:
        return self._text

    def to_dict(self) -> dict:
        return {"type": self._type, "text": self._text}


PUZZLES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "puzzles"


def load_puzzle(
    n: int,
    player_names: list[str],
    difficulty: str = "medium",
    rng: random.Random | None = None,
) -> Puzzle | None:
    """Load a pre-generated puzzle, relabel it, and return a Puzzle object.

    Picks a random puzzle file for the given (n, difficulty) config,
    substitutes real player names, and shuffles category values.

    Returns None if no pre-generated puzzle is available.
    """
    rng = rng or random.Random()

    # Find available puzzle files for this config
    candidates = sorted(PUZZLES_DIR.glob(f"{n}p_{difficulty}_*.json"))
    if not candidates:
        return None

    path = rng.choice(candidates)
    raw = json.loads(path.read_text())
    relabeled = relabel(raw, player_names, rng)
    return _dict_to_puzzle(relabeled)


def relabel(
    puzzle_dict: dict,
    player_names: list[str],
    rng: random.Random | None = None,
) -> dict:
    """Relabel a serialized puzzle dict with real names and shuffled values.

    Builds a mapping for each category (old value -> new value) and applies
    it to the solution, clue text, cards, murderer_name, and murder_weapon.
    """
    rng = rng or random.Random()
    n = puzzle_dict["n"]

    # --- Build mappings per category ---
    mappings: dict[str, dict[str, str]] = {}

    # Name: shuffle real player names, map "Player i" -> name
    shuffled_names = list(player_names)
    rng.shuffle(shuffled_names)
    old_names = [f"Player {i + 1}" for i in range(n)]
    mappings["name"] = dict(zip(old_names, shuffled_names))

    # Other categories: pick N random values from the full pool of 12
    for cat, pool in CATEGORIES.items():
        if cat not in puzzle_dict["solution"]:
            continue
        old_values = puzzle_dict["solution"][cat]
        new_values = rng.sample(pool, n)
        mappings[cat] = dict(zip(old_values, new_values))

    # --- Apply to structured fields (direct lookup) ---
    new_solution = {}
    for cat, values in puzzle_dict["solution"].items():
        cat_map = mappings.get(cat, {})
        new_solution[cat] = [cat_map.get(v, v) for v in values]

    new_murderer = mappings["name"][puzzle_dict["murderer_name"]]
    new_weapon = mappings.get("weapon", {}).get(
        puzzle_dict["murder_weapon"], puzzle_dict["murder_weapon"]
    )

    # --- Apply to clue text (two-pass to avoid swap collisions) ---
    # Flatten all mappings into one old->new map
    text_map: dict[str, str] = {}
    for cat_map in mappings.values():
        text_map.update(cat_map)

    def relabel_text(text: str) -> str:
        # Pass 1: replace old values with unique placeholders (longest first)
        placeholders: dict[str, str] = {}
        result = text
        for old in sorted(text_map, key=len, reverse=True):
            if old in result:
                ph = f"\x00PH{len(placeholders)}\x00"
                placeholders[ph] = text_map[old]
                result = result.replace(old, ph)
        # Pass 2: replace placeholders with new values
        for ph, new in placeholders.items():
            result = result.replace(ph, new)
        return result

    new_clues = [
        {"type": c["type"], "text": relabel_text(c["text"])}
        for c in puzzle_dict["clues"]
    ]
    new_murder_clues = [
        {"type": c["type"], "text": relabel_text(c["text"])}
        for c in puzzle_dict["murder_clues"]
    ]
    new_cards = [
        {
            "character_name": mappings["name"].get(
                card["character_name"], card["character_name"]
            ),
            "clues": [
                {"type": c["type"], "text": relabel_text(c["text"])}
                for c in card["clues"]
            ],
        }
        for card in puzzle_dict["cards"]
    ]

    return {
        "n": n,
        "difficulty": puzzle_dict["difficulty"],
        "solution": new_solution,
        "murderer_name": new_murderer,
        "murder_weapon": new_weapon,
        "clues": new_clues,
        "murder_clues": new_murder_clues,
        "cards": new_cards,
    }


def _dict_to_puzzle(d: dict) -> Puzzle:
    """Convert a relabeled puzzle dict into a Puzzle object."""
    clues = [_LoadedClue(c["type"], c["text"]) for c in d["clues"]]
    murder_clues = [_LoadedClue(c["type"], c["text"]) for c in d["murder_clues"]]
    cards = [
        PlayerCard(
            character_name=card["character_name"],
            clues=[_LoadedClue(c["type"], c["text"]) for c in card["clues"]],
        )
        for card in d["cards"]
    ]

    round_assignments = assign_rounds(cards, murder_clues)

    return Puzzle(
        n=d["n"],
        solution=d["solution"],
        clues=clues,
        murder_clues=murder_clues,
        murderer_name=d["murderer_name"],
        murder_weapon=d["murder_weapon"],
        cards=cards,
        difficulty=d["difficulty"],
        clue_round_assignments=round_assignments,
    )
