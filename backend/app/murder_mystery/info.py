"""Murder mystery game info builder for the shared lobby router."""

from __future__ import annotations

from ..shared.models import PlayerInfo
from .config import MAX_PLAYERS
from .game_state import MurderRoom


def build_game_info(room: MurderRoom) -> dict:
    """Build the game info response dict for murder mystery."""
    character_names = []
    if room.solution and "name" in room.solution:
        character_names = room.solution["name"]

    return {
        "code": room.code,
        "phase": room.phase.value,
        "players": [
            {"id": p.id, "name": p.name}
            for p in room.players
        ],
        "min_players": 3,
        "max_players": MAX_PLAYERS,
        "character_names": character_names,
        "murder_weapon": room.murder_weapon,
        "difficulty": room.difficulty,
        "host_name": room.host_name,
        "current_round": room.current_round,
        "round_durations": room.round_durations,
        "round_started_at": room.round_started_at.isoformat() if room.round_started_at else None,
        "started_at": room.started_at.isoformat() if room.started_at else None,
        "guesses_count": len(room.guesses),
    }
