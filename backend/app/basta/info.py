"""Basta game info builder for the shared lobby router."""

from __future__ import annotations

from .config import MAX_PLAYERS, MIN_PLAYERS, REVIEW_SECONDS, VETOES_REQUIRED
from .game_state import BastaRoom
from .scoring import normalize_text


def _word_veto_counts(room: BastaRoom, category: str) -> dict[str, int]:
    word_voters: dict[str, set[str]] = {}
    for target_pid, voter_ids in room.current_vetoes.get(category, {}).items():
        answer = room.current_answers.get(target_pid, {}).get(category, "")
        normalized_answer = normalize_text(answer)
        if normalized_answer:
            word_voters.setdefault(normalized_answer, set()).update(voter_ids)
    return {word: len(voters) for word, voters in word_voters.items()}


def build_game_info(room: BastaRoom) -> dict:
    """Build the game info response dict for Basta."""
    id_to_name = {p.id: p.name for p in room.players}
    name_scores = {
        id_to_name.get(pid, pid): score for pid, score in room.scores.items()
    }

    winner_name = id_to_name.get(room.winner, None) if room.winner else None
    current_review_category = None
    current_review_index = None
    current_review_answers = []
    if room.review_category_index is not None:
        current_review_index = room.review_category_index
        current_review_category = room.categories[room.review_category_index]
        veto_counts = _word_veto_counts(room, current_review_category)
        current_review_answers = [
            {
                "player_id": p.id,
                "player_name": p.name,
                "answer": room.current_answers.get(p.id, {}).get(
                    current_review_category, ""
                ),
                "veto_count": veto_counts.get(
                    normalize_text(
                        room.current_answers.get(p.id, {}).get(
                            current_review_category, ""
                        )
                    ),
                    0,
                ),
            }
            for p in room.players
        ]

    return {
        "code": room.code,
        "phase": room.phase.value,
        "players": [{"id": p.id, "name": p.name} for p in room.players],
        "min_players": MIN_PLAYERS,
        "max_players": MAX_PLAYERS,
        "host_name": room.host_name,
        "scores": name_scores,
        "current_round": room.current_round,
        "round_phase": room.round_phase,
        "categories": room.categories,
        "current_letter": room.current_letter,
        "current_review_category": current_review_category,
        "current_review_index": current_review_index,
        "current_review_answers": current_review_answers,
        "review_seconds": REVIEW_SECONDS,
        "vetoes_required": VETOES_REQUIRED,
        "round_ends_at": room.round_ends_at,
        "submissions_in": len(room.current_answers),
        "winner": winner_name,
        "rounds_to_play": room.rounds_to_play,
        "round_seconds": room.round_seconds,
        "host_paced": room.host_paced,
        "last_round_result": room.last_round_result,
    }
