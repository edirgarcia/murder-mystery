"""Funny questions game info builder for the shared lobby router."""

from __future__ import annotations

from .config import MAX_PLAYERS
from .game_state import FQRoom


def build_game_info(room: FQRoom) -> dict:
    """Build the game info response dict for funny questions."""
    # Map scores from player_id to player_name for display
    name_scores = {}
    for p in room.players:
        name_scores[p.name] = room.scores.get(p.id, 0)

    current_question = None
    if room.questions and room.question_index < len(room.questions):
        current_question = room.questions[room.question_index].text

    winner_name = None
    if room.winner:
        for p in room.players:
            if p.id == room.winner:
                winner_name = p.name
                break

    shame_holder_name = None
    if room.shame_holder:
        for p in room.players:
            if p.id == room.shame_holder:
                shame_holder_name = p.name
                break

    return {
        "code": room.code,
        "phase": room.phase.value,
        "players": [{"id": p.id, "name": p.name} for p in room.players],
        "min_players": 3,
        "max_players": MAX_PLAYERS,
        "host_name": room.host_name,
        "scores": name_scores,
        "current_round": room.current_round,
        "round_phase": room.round_phase,
        "current_question": current_question if room.round_phase == "voting" else None,
        "shame_holder": shame_holder_name,
        "voting_ends_at": room.voting_ends_at,
        "winner": winner_name,
        "points_to_win": room.points_to_win,
    }
