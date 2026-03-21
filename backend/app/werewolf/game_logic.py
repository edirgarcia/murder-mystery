"""Werewolf game logic -- pure functions."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .models import Role, WinCondition
from .game_state import WWPlayer


@dataclass
class NightResolution:
    deaths: list[str] = field(default_factory=list)
    werewolf_target: str | None = None
    witch_saved: bool = False
    witch_killed: str | None = None
    death_causes: dict[str, str] = field(default_factory=dict)


def resolve_night(
    werewolf_victim: str | None,
    witch_healed: bool,
    witch_kill_target: str | None,
    lovers: tuple[str, str] | None,
    game_players: dict[str, WWPlayer],
) -> NightResolution:
    """Resolve all night actions into a list of deaths.

    Order: werewolf kill (unless healed) -> witch kill -> lover chain.
    """
    deaths: list[str] = []
    death_causes: dict[str, str] = {}

    # 1. Werewolf kill
    if (
        werewolf_victim
        and werewolf_victim in game_players
        and game_players[werewolf_victim].alive
    ):
        if not witch_healed:
            deaths.append(werewolf_victim)
            death_causes[werewolf_victim] = "werewolf"

    # 2. Witch kill
    if (
        witch_kill_target
        and witch_kill_target not in deaths
        and witch_kill_target in game_players
        and game_players[witch_kill_target].alive
    ):
        deaths.append(witch_kill_target)
        death_causes[witch_kill_target] = "witch"

    # 3. Lover chain deaths
    if lovers:
        for pid in list(deaths):
            if pid in lovers:
                partner = lovers[0] if lovers[1] == pid else lovers[1]
                if (
                    partner not in deaths
                    and partner in game_players
                    and game_players[partner].alive
                ):
                    deaths.append(partner)
                    death_causes[partner] = "lover"

    return NightResolution(
        deaths=deaths,
        werewolf_target=werewolf_victim,
        witch_saved=witch_healed and werewolf_victim is not None,
        witch_killed=witch_kill_target,
        death_causes=death_causes,
    )


def resolve_day_vote(
    votes: dict[str, str],
    alive_player_ids: list[str],
) -> str | None:
    """Resolve day vote. Plurality wins, tie or skip majority = no elimination."""
    vote_counts: dict[str, int] = {}
    skip_count = 0
    for target in votes.values():
        if target == "skip":
            skip_count += 1
        else:
            vote_counts[target] = vote_counts.get(target, 0) + 1

    if not vote_counts:
        return None

    max_votes = max(vote_counts.values())
    top_targets = [pid for pid, count in vote_counts.items() if count == max_votes]

    if len(top_targets) > 1:
        return None

    if skip_count >= max_votes:
        return None

    return top_targets[0]


def check_win_condition(
    game_players: dict[str, WWPlayer],
    lovers: tuple[str, str] | None,
) -> WinCondition | None:
    """Check if any faction has won.

    Checked after every death:
    1. Lovers win: only the two lovers remain alive
    2. Villagers win: all werewolves dead
    3. Werewolves win: werewolves >= non-werewolf alive
    """
    alive = {pid: p for pid, p in game_players.items() if p.alive}
    alive_wolves = [p for p in alive.values() if p.role == Role.WEREWOLF]
    alive_non_wolves = [p for p in alive.values() if p.role != Role.WEREWOLF]

    # Lovers win check
    if lovers and len(alive) == 2:
        if set(alive.keys()) == set(lovers):
            return WinCondition.LOVERS

    # Villagers win: all werewolves dead
    if len(alive_wolves) == 0:
        return WinCondition.VILLAGERS

    # Werewolves win: wolves >= non-wolves
    if len(alive_wolves) >= len(alive_non_wolves):
        return WinCondition.WEREWOLVES

    return None


def resolve_werewolf_vote(
    votes: dict[str, str],
    alpha_wolf_id: str | None = None,
) -> str | None:
    """Resolve werewolf pack vote. Majority wins, Alpha breaks ties."""
    if not votes:
        return None

    vote_counts: dict[str, int] = {}
    for target in votes.values():
        vote_counts[target] = vote_counts.get(target, 0) + 1

    max_votes = max(vote_counts.values())
    top_targets = [pid for pid, count in vote_counts.items() if count == max_votes]

    if len(top_targets) == 1:
        return top_targets[0]

    # Tie-breaking: Alpha's vote wins if their target is among the tied
    if alpha_wolf_id and alpha_wolf_id in votes:
        alpha_choice = votes[alpha_wolf_id]
        if alpha_choice in top_targets:
            return alpha_choice

    return random.choice(top_targets)
