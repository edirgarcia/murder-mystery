"""Pure helpers for Prisoner's Dilemma round resolution."""

from __future__ import annotations

import random
from collections import Counter

from ..shared.game_state import Player
from .config import SPY_SABOTAGE_CHARGES
from .game_state import PDPlayer
from .models import Decision, TeamColor


def assign_teams_and_spies(players: list[Player]) -> dict[str, PDPlayer]:
    shuffled = players[:]
    random.shuffle(shuffled)

    assignments: dict[str, PDPlayer] = {}
    team_members: dict[TeamColor, list[Player]] = {
        TeamColor.RED: [],
        TeamColor.BLUE: [],
    }

    for index, player in enumerate(shuffled):
        team = TeamColor.RED if index % 2 == 0 else TeamColor.BLUE
        team_members[team].append(player)
        assignments[player.id] = PDPlayer(id=player.id, name=player.name, team=team)

    for team, members in team_members.items():
        spy = random.choice(members)
        assignments[spy.id].is_spy = True
        assignments[spy.id].sabotage_charges = SPY_SABOTAGE_CHARGES

    return assignments


def player_ids_for_team(game_players: dict[str, PDPlayer], team: TeamColor) -> list[str]:
    return [pid for pid, player in game_players.items() if player.team == team]


def majority_choice(choices: list[Decision]) -> tuple[Decision, dict[Decision, int]]:
    counts = Counter(choices)
    trust_count = counts.get(Decision.TRUST, 0)
    betray_count = counts.get(Decision.BETRAY, 0)
    if trust_count > betray_count:
        return Decision.TRUST, {
            Decision.TRUST: trust_count,
            Decision.BETRAY: betray_count,
        }
    return Decision.BETRAY, {
        Decision.TRUST: trust_count,
        Decision.BETRAY: betray_count,
    }


def score_choices(
    red_choice: Decision,
    blue_choice: Decision,
    multiplier: int = 1,
) -> dict[TeamColor, int]:
    if red_choice == Decision.TRUST and blue_choice == Decision.TRUST:
        return {
            TeamColor.RED: 6 * multiplier,
            TeamColor.BLUE: 6 * multiplier,
        }
    if red_choice == Decision.TRUST and blue_choice == Decision.BETRAY:
        return {
            TeamColor.RED: -12 * multiplier,
            TeamColor.BLUE: 12 * multiplier,
        }
    if red_choice == Decision.BETRAY and blue_choice == Decision.TRUST:
        return {
            TeamColor.RED: 12 * multiplier,
            TeamColor.BLUE: -12 * multiplier,
        }
    return {
        TeamColor.RED: -6 * multiplier,
        TeamColor.BLUE: -6 * multiplier,
    }


def resolve_team_accusation(
    team_player_ids: list[str],
    accusations: dict[str, str | None],
    active_spy_id: str | None,
) -> dict:
    accusers = [target_id for target_id in accusations.values() if target_id]
    majority_threshold = len(team_player_ids) / 2

    if len(accusers) <= majority_threshold:
        return {
            "accusation_triggered": False,
            "accused_player_id": None,
            "correct": None,
            "score_delta": 0,
            "spy_neutralized": False,
        }

    counts = Counter(accusers)
    top_count = max(counts.values())
    top_targets = [target_id for target_id, count in counts.items() if count == top_count]
    if len(top_targets) != 1:
        return {
            "accusation_triggered": False,
            "accused_player_id": None,
            "correct": None,
            "score_delta": 0,
            "spy_neutralized": False,
        }

    accused_player_id = top_targets[0]
    correct = active_spy_id is not None and accused_player_id == active_spy_id
    return {
        "accusation_triggered": True,
        "accused_player_id": accused_player_id,
        "correct": correct,
        "score_delta": 0 if correct else -1,
        "spy_neutralized": correct,
    }


def winner_for_scores(team_scores: dict[TeamColor, int]) -> str:
    red_score = team_scores.get(TeamColor.RED, 0)
    blue_score = team_scores.get(TeamColor.BLUE, 0)
    if red_score > blue_score:
        return TeamColor.RED.value
    if blue_score > red_score:
        return TeamColor.BLUE.value
    return "draw"
