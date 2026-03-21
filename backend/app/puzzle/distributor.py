"""Distribute clues across player cards.

Each player gets a character card with a subset of the puzzle clues.
Murder chain clues are spread across different cards so no single player
can deduce the murderer alone.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .clues import Clue


@dataclass
class PlayerCard:
    """A player's character card with their clues."""

    character_name: str
    clues: list[Clue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "character_name": self.character_name,
            "clues": [c.to_dict() for c in self.clues],
        }


def _smallest_card(cards: list[PlayerCard], rng: random.Random) -> int:
    """Return the index of the card with the fewest clues (random tie-break)."""
    min_size = min(len(c.clues) for c in cards)
    candidates = [i for i, c in enumerate(cards) if len(c.clues) == min_size]
    return rng.choice(candidates)


def distribute_clues(
    character_names: list[str],
    all_clues: list[Clue],
    murder_clues: list[Clue],
    rng: random.Random | None = None,
    overlap_fraction: float = 0.2,
) -> list[PlayerCard]:
    """Distribute clues across player cards.

    Rules:
    - Murder clues go on separate cards.
    - Remaining clues fill the smallest card first (balanced).
    - ~overlap_fraction of non-murder clues appear on multiple cards,
      always targeting the smallest card.
    - Final card sizes differ by at most 1.

    Args:
        character_names: List of character names, one per player.
        all_clues: All clues (including murder clues).
        murder_clues: The murder chain clues specifically.
        rng: Random number generator.
        overlap_fraction: Fraction of clues to duplicate across cards.

    Returns:
        List of PlayerCard, one per player.
    """
    rng = rng or random.Random()
    n_players = len(character_names)

    cards = [PlayerCard(character_name=name) for name in character_names]

    # Distribute murder clues to separate cards, picking the smallest each time
    murder_used_indices: set[int] = set()
    for clue in murder_clues:
        # Prefer smallest card that hasn't received a murder clue yet
        min_size = float("inf")
        candidates: list[int] = []
        for i, c in enumerate(cards):
            if i in murder_used_indices:
                continue
            size = len(c.clues)
            if size < min_size:
                min_size = size
                candidates = [i]
            elif size == min_size:
                candidates.append(i)
        # Fallback: if all cards already have a murder clue, use any smallest
        if not candidates:
            candidates = [_smallest_card(cards, rng)]
        idx = rng.choice(candidates)
        murder_used_indices.add(idx)
        cards[idx].clues.append(clue)

    # Non-murder clues — always add to the smallest card
    murder_clue_ids = {id(c) for c in murder_clues}
    other_clues = [c for c in all_clues if id(c) not in murder_clue_ids]
    rng.shuffle(other_clues)

    for clue in other_clues:
        idx = _smallest_card(cards, rng)
        cards[idx].clues.append(clue)

    # Add overlap: duplicate some clues to additional cards,
    # always targeting the smallest eligible card
    n_overlap = int(len(other_clues) * overlap_fraction)
    if n_overlap > 0:
        overlap_clues = rng.sample(other_clues, min(n_overlap, len(other_clues)))
        for clue in overlap_clues:
            clue_text = clue.render()
            # Find smallest card that doesn't already have this clue
            min_size = float("inf")
            candidates = []
            for i, c in enumerate(cards):
                if any(existing.render() == clue_text for existing in c.clues):
                    continue
                size = len(c.clues)
                if size < min_size:
                    min_size = size
                    candidates = [i]
                elif size == min_size:
                    candidates.append(i)
            if candidates:
                idx = rng.choice(candidates)
                cards[idx].clues.append(clue)

    # Shuffle clues within each card
    for card in cards:
        rng.shuffle(card.clues)

    return cards


def assign_rounds(
    cards: list[PlayerCard],
    murder_clues: list[Clue],
    num_rounds: int = 3,
    rng: random.Random | None = None,
) -> list[list[int]]:
    """Assign each clue on each card to a round (1..num_rounds).

    Murder chain clues are spread across different rounds so no single
    round reveals the entire chain.  Non-murder clues are distributed
    as evenly as possible across rounds.

    Returns a parallel structure: ``assignments[card_idx][clue_idx]``
    is the round number (1-based) for that clue.
    """
    rng = rng or random.Random()
    murder_texts = {c.render() for c in murder_clues}

    assignments: list[list[int]] = []

    for card in cards:
        n_clues = len(card.clues)
        rounds: list[int] = [0] * n_clues

        # Identify murder vs non-murder clue indices
        murder_idxs = [i for i, c in enumerate(card.clues) if c.render() in murder_texts]
        other_idxs = [i for i, c in enumerate(card.clues) if c.render() not in murder_texts]

        # Spread murder clues across rounds (cycling 1, 2, 3, 1, ...)
        for seq, idx in enumerate(murder_idxs):
            rounds[idx] = (seq % num_rounds) + 1

        # Distribute non-murder clues evenly across rounds
        rng.shuffle(other_idxs)
        for seq, idx in enumerate(other_idxs):
            rounds[idx] = (seq % num_rounds) + 1

        assignments.append(rounds)

    return assignments
