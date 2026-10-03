"""Trading City game info builder (lobby GET response)."""

from __future__ import annotations

import time

from .config import MAX_PLAYERS, MIN_PLAYERS
from .game_state import TCRoom
from .views import public_view


def build_game_info(room: TCRoom) -> dict:
    return {
        "code": room.code,
        "phase": room.phase.value,
        "players": [{"id": p.id, "name": p.name} for p in room.players],
        "min_players": MIN_PLAYERS,
        "max_players": MAX_PLAYERS,
        "host_name": room.host_name,
        "state": public_view(room.game, room.deadline, time.time(), room.ready) if room.game else None,
    }
