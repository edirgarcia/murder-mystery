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

    # Ensure every card has at least 3 clues (one per round) by duplicating
    # clues from other cards if needed
    min_per_card = 3
    for i, card in enumerate(cards):
        while len(card.clues) < min_per_card:
            # Find a clue from another card that this card doesn't have
            existing_texts = {c.render() for c in card.clues}
            donor = None
            for other in rng.sample(cards, len(cards)):
                for clue in other.clues:
                    if clue.render() not in existing_texts:
                        donor = clue
                        break
                if donor:
                    break
            if donor:
                card.clues.append(donor)
            else:
                break  # no unique clues left to duplicate

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

    Round 1: each card gets exactly 1 clue. Exactly one card receives a
    murder clue in round 1; all other cards get a non-murder clue.
    Rounds 2-3: remaining clues are distributed randomly.

    Returns a parallel structure: ``assignments[card_idx][clue_idx]``
    is the round number (1-based) for that clue.
    """
    rng = rng or random.Random()
    murder_texts = {c.render() for c in murder_clues}

    # Build per-card murder/non-murder indices
    per_card: list[tuple[list[int], list[int]]] = []
    for card in cards:
        murder_idxs = [i for i, c in enumerate(card.clues) if c.render() in murder_texts]
        other_idxs = [i for i, c in enumerate(card.clues) if c.render() not in murder_texts]
        per_card.append((murder_idxs, other_idxs))

    # Pick exactly one card to reveal a murder clue in round 1
    cards_with_murder = [ci for ci, (m, _) in enumerate(per_card) if m]
    murder_r1_card = rng.choice(cards_with_murder) if cards_with_murder else -1

    assignments: list[list[int]] = []

    for ci, card in enumerate(cards):
        murder_idxs, other_idxs = per_card[ci]
        rounds: list[int] = [0] * len(card.clues)

        # Round 1: exactly 1 clue
        if ci == murder_r1_card:
            # This card shows a murder clue in round 1
            r1_idx = rng.choice(murder_idxs)
            murder_idxs = [i for i in murder_idxs if i != r1_idx]
        else:
            # This card shows a non-murder clue in round 1
            rng.shuffle(other_idxs)
            r1_idx = other_idxs.pop(0) if other_idxs else murder_idxs.pop(0)

        rounds[r1_idx] = 1

        # Remaining clues: distribute across rounds 2 and 3,
        # guaranteeing at least one clue per round when possible
        remaining = murder_idxs + other_idxs
        rng.shuffle(remaining)
        if len(remaining) >= 2:
            # Guarantee at least one clue in round 2 and one in round 3
            rounds[remaining[0]] = 2
            rounds[remaining[1]] = 3
            for idx in remaining[2:]:
                rounds[idx] = rng.choice([2, 3])
        elif len(remaining) == 1:
            rounds[remaining[0]] = 2
        # len == 0: nothing to assign

        assignments.append(rounds)

    return assignments
