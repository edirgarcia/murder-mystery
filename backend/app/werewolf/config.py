"""Werewolf game settings."""

from __future__ import annotations

MIN_PLAYERS = 6
MAX_PLAYERS = 16

# Timer durations in seconds
WEREWOLF_VOTE_SECONDS = 30
SEER_SECONDS = 20
WITCH_SECONDS = 30
CUPID_SECONDS = 25
HUNTER_SECONDS = 20
ANNOUNCEMENT_SECONDS = 10
DISCUSSION_SECONDS = 90
DAY_VOTE_SECONDS = 45
VOTE_RESULT_SECONDS = 10

# Role distribution: (min_players, max_players, num_werewolves)
WEREWOLF_COUNT_RULES: list[tuple[int, int, int]] = [
    (6, 8, 2),
    (9, 12, 3),
    (13, 16, 4),
]
