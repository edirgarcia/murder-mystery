"""Werewolf game info builder for the shared lobby router."""

from __future__ import annotations

from .config import MAX_PLAYERS, MIN_PLAYERS
from .game_state import WerewolfRoom


def build_game_info(room: WerewolfRoom) -> dict:
    """Build the game info response dict for werewolf."""
    players = []
    for p in room.players:
        gp = room.game_players.get(p.id)
        players.append({
            "id": p.id,
            "name": p.name,
            "alive": gp.alive if gp else True,
        })

    alive_count = (
        sum(1 for gp in room.game_players.values() if gp.alive)
        if room.game_players
        else len(room.players)
    )

    return {
        "code": room.code,
        "phase": room.phase.value,
        "players": players,
        "min_players": MIN_PLAYERS,
        "max_players": MAX_PLAYERS,
        "host_name": room.host_name,
        "night_number": room.night_number,
        "day_number": room.day_number,
        "night_sub_phase": room.night_sub_phase.value if room.night_sub_phase else None,
        "day_sub_phase": room.day_sub_phase.value if room.day_sub_phase else None,
        "alive_count": alive_count,
        "winner": room.winner.value if room.winner else None,
        "phase_ends_at": room.phase_ends_at,
        "discussion_seconds": room.discussion_seconds,
    }
