"""Prisoner's Dilemma game info builder."""

from __future__ import annotations

from .config import MAX_PLAYERS, MIN_PLAYERS
from .game_state import PDRoom


def build_game_info(room: PDRoom) -> dict:
    players = []
    for player in room.players:
        game_player = room.game_players.get(player.id)
        players.append(
            {
                "id": player.id,
                "name": player.name,
                "team": game_player.team.value if game_player and room.phase.value != "lobby" else None,
                "spy_exposed": game_player.spy_exposed if game_player else False,
            }
        )

    return {
        "code": room.code,
        "phase": room.phase.value,
        "players": players,
        "min_players": MIN_PLAYERS,
        "max_players": MAX_PLAYERS,
        "host_name": room.host_name,
        "current_round": room.current_round,
        "total_rounds": room.total_rounds,
        "round_phase": room.round_phase,
        "voting_ends_at": room.voting_ends_at,
        "accusation_ends_at": room.accusation_ends_at,
        "team_scores": {
            team.value: score for team, score in room.team_scores.items()
        },
        "winner": room.winner,
    }
