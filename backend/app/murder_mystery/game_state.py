"""Murder mystery game state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from ..shared.game_state import BaseGameRoom, GameStore, Player
from ..puzzle.distributor import PlayerCard
from ..puzzle.generator import Solution


@dataclass
class GuessRecord:
    suspect_name: str
    guessed_at: datetime


@dataclass
class MurderRoom(BaseGameRoom):
    # Set after puzzle generation
    solution: Solution | None = None
    murderer_name: str | None = None
    murder_weapon: str | None = None
    cards: list[PlayerCard] | None = None
    murder_clue_dicts: list[dict] | None = None
    difficulty: str | None = None
    # Rounds & timer
    started_at: datetime | None = None  # overall game start (for scoring)
    current_round: int = 0  # 0=not started, 1-3 during play
    round_durations: list[int] = field(default_factory=lambda: [180, 300, 300])
    round_started_at: datetime | None = None
    timer_task: asyncio.Task | None = None
    clue_round_assignments: list[list[int]] | None = None
    # Player guesses: {player_id: GuessRecord}
    guesses: dict[str, GuessRecord] = field(default_factory=dict)
    # Narration
    narration_ack: asyncio.Event | None = None
    intro_task: asyncio.Task | None = None


class MurderStore(GameStore[MurderRoom]):
    def __init__(self) -> None:
        super().__init__(MurderRoom)

    def get_player_card(self, room: MurderRoom, player_id: str) -> PlayerCard | None:
        if not room.cards:
            return None
        player = self.get_player(room, player_id)
        if not player:
            return None
        idx = room.players.index(player)
        if idx < len(room.cards):
            return room.cards[idx]
        return None


# Singleton
store = MurderStore()
