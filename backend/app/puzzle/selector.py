"""Greedy clue selection and pruning.

Selects the minimal set of clues that yield a unique solution.
Uses the CSP solver with early stopping instead of enumerating all solutions.
"""

from __future__ import annotations

import logging
import random

from .clues import Clue
from .generator import Solution
from .solver import count_solutions_bounded, is_unique

logger = logging.getLogger(__name__)


def select_clues(
    n: int,
    solution: Solution,
    candidate_pool: list[Clue],
    required_clues: list[Clue] | None = None,
    max_iterations: int = 100,
    sample_size: int = 40,
    rng: random.Random | None = None,
) -> list[Clue]:
    """Select clues until the puzzle has a unique solution, then prune.

    Strategy: At each step, sample candidates and pick the one that most
    reduces the solution count (checked via bounded CSP solving).

    Args:
        n: Number of positions.
        solution: The target solution.
        candidate_pool: Pool of candidate clues (already shuffled).
        required_clues: Clues that must be included (e.g. murder clues).
        max_iterations: Safety limit on selection rounds.
        sample_size: Number of candidates to evaluate per round.
        rng: Random number generator.
    """
    rng = rng or random.Random()
    selected: list[Clue] = list(required_clues) if required_clues else []
    required_set = {id(c) for c in selected}
    remaining = [c for c in candidate_pool if id(c) not in required_set]

    for iteration in range(max_iterations):
        if is_unique(n, selected):
            logger.info("Unique solution found after %d extra clues", iteration)
            break

        # Sample a subset of candidates to evaluate
        batch = remaining[:sample_size] if len(remaining) <= sample_size else rng.sample(remaining, sample_size)

        best_clue = None
        best_count = float("inf")

        for candidate in batch:
            test_clues = selected + [candidate]
            count = count_solutions_bounded(n, test_clues, limit=50)
            if count == 0:
                continue  # Clue is inconsistent with solution — skip
            if count < best_count:
                best_count = count
                best_clue = candidate
                if count == 1:
                    break

        if best_clue is None:
            # No candidate from sample helped — try adding a random DirectEquality
            # to make progress
            for c in remaining:
                test_clues = selected + [c]
                count = count_solutions_bounded(n, test_clues, limit=50)
                if 0 < count < 50:
                    best_clue = c
                    break

        if best_clue is None:
            raise RuntimeError(
                f"Cannot reduce solutions further after {iteration} iterations."
            )

        selected.append(best_clue)
        remaining.remove(best_clue)
        logger.info("Iteration %d: added clue (best_count=%s)", iteration, best_count)
    else:
        raise RuntimeError(f"Failed to reach unique solution after {max_iterations} iterations.")

    # Prune redundant non-required clues
    selected = _prune(n, selected, required_set)
    return selected


def _prune(n: int, clues: list[Clue], required_ids: set[int]) -> list[Clue]:
    """Remove redundant clues while maintaining uniqueness."""
    pruned = list(clues)
    i = len(pruned) - 1
    while i >= 0:
        if id(pruned[i]) in required_ids:
            i -= 1
            continue
        candidate = pruned.pop(i)
        if is_unique(n, pruned):
            logger.info("Pruned clue: %s", candidate.render())
        else:
            pruned.insert(i, candidate)
        i -= 1
    return pruned
