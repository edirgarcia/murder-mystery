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
    # Timer
    started_at: datetime | None = None
    duration_seconds: int = 600
    timer_task: asyncio.Task | None = None
    # Player guesses: {player_id: GuessRecord}
    guesses: dict[str, GuessRecord] = field(default_factory=dict)


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
