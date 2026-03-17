"""Orchestrates full puzzle generation.

The main entry point: generate_puzzle(n) produces a complete puzzle
with solution, clues, murder chain, and player cards.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from .clues import Clue, generate_candidates
from .distributor import PlayerCard, distribute_clues
from .generator import Solution, generate_solution
from .murder import generate_murder_clues
from .schema import get_schema
from .selector import select_clues
from .solver import set_schema_override

logger = logging.getLogger(__name__)


@dataclass
class Puzzle:
    """A complete generated puzzle."""

    n: int
    solution: Solution
    clues: list[Clue]
    murder_clues: list[Clue]
    murderer_name: str
    murder_weapon: str
    cards: list[PlayerCard]

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "solution": self.solution,
            "murderer_name": self.murderer_name,
            "murder_weapon": self.murder_weapon,
            "clues": [c.to_dict() for c in self.clues],
            "murder_clues": [c.to_dict() for c in self.murder_clues],
            "cards": [card.to_dict() for card in self.cards],
        }


def generate_puzzle(
    n: int,
    seed: int | None = None,
    max_attempts: int = 5,
    player_names: list[str] | None = None,
) -> Puzzle:
    """Generate a complete murder mystery puzzle for *n* players.

    Args:
        n: Number of players/positions (3-6).
        seed: Optional random seed for reproducibility.
        max_attempts: Number of retries if generation fails.
        player_names: If provided, uses real player names instead of
            hardcoded character names.

    Returns:
        A fully generated Puzzle.

    Raises:
        RuntimeError: If unable to generate after max_attempts.
    """
    rng = random.Random(seed)

    # Build the schema once and set it as the solver override so all
    # solver calls use the correct name values.
    schema = get_schema(n, player_names=player_names)
    set_schema_override(schema)

    try:
        for attempt in range(max_attempts):
            try:
                logger.info("Attempt %d: generating puzzle for n=%d", attempt + 1, n)

                # Step 1: Generate random solution
                solution = generate_solution(n, rng, player_names=player_names)
                logger.info("Generated solution")

                # Step 2: Generate murder chain
                murderer_name, murder_weapon, murder_clues = generate_murder_clues(solution, rng)
                logger.info("Murder chain: %s is the killer (weapon: %s)", murderer_name, murder_weapon)

                # Step 3: Generate candidate clue pool
                candidates = generate_candidates(solution, rng)
                # Remove candidates that duplicate murder clues
                murder_texts = {c.render() for c in murder_clues}
                candidates = [c for c in candidates if c.render() not in murder_texts]
                logger.info("Generated %d candidate clues", len(candidates))

                # Step 4: Select minimal clue set
                selected = select_clues(n, solution, candidates, murder_clues)
                logger.info("Selected %d clues (including %d murder)", len(selected), len(murder_clues))

                # Step 5: Distribute clues to player cards
                names = solution["name"]
                cards = distribute_clues(names, selected, murder_clues, rng)
                logger.info("Distributed clues to %d cards", len(cards))

                return Puzzle(
                    n=n,
                    solution=solution,
                    clues=selected,
                    murder_clues=murder_clues,
                    murderer_name=murderer_name,
                    murder_weapon=murder_weapon,
                    cards=cards,
                )

            except RuntimeError as e:
                logger.warning("Attempt %d failed: %s", attempt + 1, e)
                continue

        raise RuntimeError(f"Failed to generate puzzle after {max_attempts} attempts")
    finally:
        set_schema_override(None)
