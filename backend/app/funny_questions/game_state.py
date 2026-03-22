"""Funny questions game state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from ..shared.game_state import BaseGameRoom, GameStore
from .questions import Question


@dataclass
class FQRoom(BaseGameRoom):
    # Scores: {player_id: total_points}
    scores: dict[str, int] = field(default_factory=dict)
    current_round: int = 0
    # "voting" | "reveal" | None
    round_phase: str | None = None
    shame_holder: str | None = None
    questions: list[Question] = field(default_factory=list)
    question_index: int = 0
    # Current round state
    current_votes: dict[str, str] = field(default_factory=dict)
    # Signals
    vote_complete: asyncio.Event | None = None
    game_task: asyncio.Task | None = None
    # Narration
    narration_ack: asyncio.Event | None = None
    # Config
    points_to_win: int = 20
    voting_ends_at: str | None = None
    winner: str | None = None


class FQStore(GameStore[FQRoom]):
    def __init__(self) -> None:
        super().__init__(FQRoom)


# Singleton
store = FQStore()
