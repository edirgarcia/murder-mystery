"""In-memory game store.

Manages game rooms, players, and puzzle state. Ephemeral — all data
is lost on server restart, which is fine for a party game.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field

from fastapi import WebSocket

from .config import ROOM_CODE_LENGTH
from .models import GamePhase
from .puzzle.distributor import PlayerCard
from .puzzle.generator import Solution


@dataclass
class Player:
    id: str
    name: str
    is_host: bool = False


@dataclass
class GameRoom:
    code: str
    phase: GamePhase = GamePhase.LOBBY
    players: list[Player] = field(default_factory=list)
    # Set after puzzle generation
    solution: Solution | None = None
    murderer_name: str | None = None
    murder_weapon: str | None = None
    cards: list[PlayerCard] | None = None
    murder_clue_dicts: list[dict] | None = None
    # Player guesses: {player_id: suspect_name}
    guesses: dict[str, str] = field(default_factory=dict)
    # WebSocket connections: {player_id: WebSocket}
    connections: dict[str, WebSocket] = field(default_factory=dict)


class GameStore:
    """In-memory store for all active game rooms."""

    def __init__(self) -> None:
        self._rooms: dict[str, GameRoom] = {}

    def _generate_code(self) -> str:
        while True:
            code = "".join(
                random.choices(string.ascii_uppercase, k=ROOM_CODE_LENGTH)
            )
            if code not in self._rooms:
                return code

    def create_room(self) -> GameRoom:
        code = self._generate_code()
        room = GameRoom(code=code)
        self._rooms[code] = room
        return room

    def get_room(self, code: str) -> GameRoom | None:
        return self._rooms.get(code.upper())

    def add_player(self, room: GameRoom, name: str, is_host: bool = False) -> Player:
        player_id = f"p_{random.randint(10000, 99999)}"
        player = Player(id=player_id, name=name, is_host=is_host)
        room.players.append(player)
        return player

    def get_player(self, room: GameRoom, player_id: str) -> Player | None:
        for p in room.players:
            if p.id == player_id:
                return p
        return None

    def get_player_card(self, room: GameRoom, player_id: str) -> PlayerCard | None:
        if not room.cards:
            return None
        player = self.get_player(room, player_id)
        if not player:
            return None
        # Cards are indexed by player order
        idx = room.players.index(player)
        if idx < len(room.cards):
            return room.cards[idx]
        return None


# Singleton
store = GameStore()
