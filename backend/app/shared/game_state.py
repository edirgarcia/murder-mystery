"""Shared in-memory game store.

Manages game rooms, players, and connections. Ephemeral -- all data
is lost on server restart, which is fine for a party game.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field

from fastapi import WebSocket

from .config import ROOM_CODE_LENGTH
from .models import GamePhase


@dataclass
class Player:
    id: str
    name: str


@dataclass
class BaseGameRoom:
    code: str
    phase: GamePhase = GamePhase.LOBBY
    host_id: str = ""
    host_name: str = ""
    players: list[Player] = field(default_factory=list)
    # WebSocket connections: {client_id: WebSocket}
    connections: dict[str, WebSocket] = field(default_factory=dict)


class GameStore[T: BaseGameRoom]:
    """Generic in-memory store for game rooms."""

    def __init__(self, room_factory: type[T]) -> None:
        self._rooms: dict[str, T] = {}
        self._room_factory = room_factory

    def _generate_code(self) -> str:
        # TODO: remove hardcoded code before deploying
        if "AAAA" not in self._rooms:
            return "AAAA"
        while True:
            code = "".join(
                random.choices(string.ascii_uppercase, k=ROOM_CODE_LENGTH)
            )
            if code not in self._rooms:
                return code

    def create_room(self) -> T:
        code = self._generate_code()
        room = self._room_factory(code=code)
        self._rooms[code] = room
        return room

    def get_room(self, code: str) -> T | None:
        return self._rooms.get(code.upper())

    def set_host(self, room: T, name: str) -> str:
        host_id = f"h_{random.randint(10000, 99999)}"
        room.host_id = host_id
        room.host_name = name
        return host_id

    def add_player(self, room: T, name: str) -> Player:
        player_id = f"p_{random.randint(10000, 99999)}"
        player = Player(id=player_id, name=name)
        room.players.append(player)
        return player

    def get_player(self, room: T, player_id: str) -> Player | None:
        for p in room.players:
            if p.id == player_id:
                return p
        return None

    def is_host(self, room: T, client_id: str) -> bool:
        return room.host_id == client_id
