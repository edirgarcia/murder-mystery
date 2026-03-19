"""Orchestrates full puzzle generation.

The main entry point: generate_puzzle(n, difficulty) produces a complete puzzle
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

# Chain hops by (player_tier, difficulty).
#   Players  Easy  Medium  Hard  Harder  Hardest
#   4-6      3     4       5     5       5
#   7-12     2     3       4     4       4
_CHAIN_HOPS: dict[str, tuple[int, int]] = {
    # (small_tier, large_tier)
    "easy": (3, 2),
    "medium": (4, 3),
    "hard": (5, 4),
    "harder": (5, 4),
    "hardest": (5, 4),
}

# Clue type weights by difficulty.  None means unweighted (all types equal).
# "harder" and "hardest" bias toward less-informative clue types.
CLUE_WEIGHTS: dict[str, dict[str, float] | None] = {
    "easy": None,
    "medium": None,
    "hard": None,
    "harder": {
        "PositionClue": 0.5,
        "DirectEquality": 1.0,
        "Adjacency": 2.0,
        "Ordering": 3.0,
        "Negation": 2.0,
    },
    "hardest": {
        "PositionClue": 0.0,
        "DirectEquality": 0.5,
        "Adjacency": 1.5,
        "Ordering": 3.0,
        "Negation": 3.0,
    },
}


def _get_chain_hops(n: int, difficulty: str) -> int:
    """Return the murder chain hop count for n players and difficulty."""
    small, large = _CHAIN_HOPS[difficulty]
    return small if n <= 6 else large


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
    difficulty: str

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "difficulty": self.difficulty,
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
    difficulty: str = "medium",
    max_iterations: int = 100,
) -> Puzzle:
    """Generate a complete murder mystery puzzle for *n* players.

    Args:
        n: Number of players/positions (4-12).
        seed: Optional random seed for reproducibility.
        max_attempts: Number of retries if generation fails.
        player_names: If provided, uses real player names instead of
            hardcoded character names.
        difficulty: One of "easy", "medium", "hard".

    Returns:
        A fully generated Puzzle.

    Raises:
        RuntimeError: If unable to generate after max_attempts.
    """
    rng = random.Random(seed)
    chain_hops = _get_chain_hops(n, difficulty)

    # Build the schema once and set it as the solver override so all
    # solver calls use the correct name values.
    schema = get_schema(n, player_names=player_names, difficulty=difficulty)
    set_schema_override(schema)

    try:
        for attempt in range(max_attempts):
            try:
                logger.info("Attempt %d: generating puzzle for n=%d difficulty=%s", attempt + 1, n, difficulty)

                # Step 1: Generate random solution
                solution = generate_solution(n, rng, player_names=player_names, difficulty=difficulty)
                logger.info("Generated solution")

                # Step 2: Generate murder chain
                murderer_name, murder_weapon, murder_clues = generate_murder_clues(
                    solution, rng, chain_hops=chain_hops
                )
                logger.info(
                    "Murder chain: %s is the killer (weapon: %s, %d hops)",
                    murderer_name, murder_weapon, chain_hops,
                )

                # Step 3: Generate candidate clue pool
                candidates = generate_candidates(solution, rng)
                # Remove candidates that duplicate murder clues
                murder_texts = {c.render() for c in murder_clues}
                candidates = [c for c in candidates if c.render() not in murder_texts]
                logger.info("Generated %d candidate clues", len(candidates))

                # Step 4: Select minimal clue set
                clue_weights = CLUE_WEIGHTS[difficulty]
                selected = select_clues(n, solution, candidates, murder_clues, max_iterations=max_iterations, clue_weights=clue_weights)
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
                    difficulty=difficulty,
                )

            except RuntimeError as e:
                logger.warning("Attempt %d failed: %s", attempt + 1, e)
                continue

        raise RuntimeError(f"Failed to generate puzzle after {max_attempts} attempts")
    finally:
        set_schema_override(None)
