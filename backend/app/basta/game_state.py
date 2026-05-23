"""Basta game state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from ..shared.game_state import BaseGameRoom, GameStore
from .config import DEFAULT_CATEGORIES, ROUND_SECONDS, ROUNDS_TO_PLAY


@dataclass
class BastaRoom(BaseGameRoom):
    # Scores: {player_id: total_points}
    scores: dict[str, int] = field(default_factory=dict)
    current_round: int = 0
    # "answering" | "review" | "reveal" | None
    round_phase: str | None = None
    categories: list[str] = field(default_factory=lambda: list(DEFAULT_CATEGORIES))
    current_letter: str | None = None
    used_letters: list[str] = field(default_factory=list)
    # Current round state: {player_id: {category: answer}}
    current_answers: dict[str, dict[str, str]] = field(default_factory=dict)
    current_drafts: dict[str, dict[str, str]] = field(default_factory=dict)
    # Vetoes: {category: {target_player_id: {voter_player_ids}}}
    current_vetoes: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    review_category_index: int | None = None
    round_complete: asyncio.Event | None = None
    round_timer_started: asyncio.Event | None = None
    review_advance: asyncio.Event | None = None
    next_round: asyncio.Event | None = None
    game_task: asyncio.Task | None = None
    round_ends_at: str | None = None
    last_round_result: dict | None = None
    winner: str | None = None
    # Config
    rounds_to_play: int = ROUNDS_TO_PLAY
    round_seconds: int = ROUND_SECONDS
    host_paced: bool = False


class BastaStore(GameStore[BastaRoom]):
    def __init__(self) -> None:
        super().__init__(BastaRoom)


# Singleton
store = BastaStore()
