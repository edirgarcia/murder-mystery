"""Werewolf game state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from ..shared.game_state import BaseGameRoom, GameStore
from .models import Role, NightSubPhase, DaySubPhase, WinCondition


@dataclass
class WWPlayer:
    id: str
    name: str
    role: Role = Role.VILLAGER
    alive: bool = True
    lover_id: str | None = None


@dataclass
class WerewolfRoom(BaseGameRoom):
    # Game players with roles (populated on game start from base players list)
    game_players: dict[str, WWPlayer] = field(default_factory=dict)

    # Night state
    night_number: int = 0
    night_sub_phase: NightSubPhase | None = None
    werewolf_votes: dict[str, str] = field(default_factory=dict)
    werewolf_preselections: dict[str, str] = field(default_factory=dict)
    werewolf_victim: str | None = None
    alpha_wolf_id: str | None = None
    seer_target: str | None = None
    witch_heal_used: bool = False
    witch_kill_used: bool = False
    witch_healed_this_night: bool = False
    witch_killed_target: str | None = None

    # Day state
    day_number: int = 0
    day_sub_phase: DaySubPhase | None = None
    day_votes: dict[str, str] = field(default_factory=dict)

    # Cupid / lovers
    lovers: tuple[str, str] | None = None

    # Hunter
    hunter_pending: bool = False
    hunter_shot_target: str | None = None

    # Game outcome
    winner: WinCondition | None = None
    discussion_seconds: int = 90
    phase_ends_at: str | None = None
    last_deaths: list[str] = field(default_factory=list)
    last_death_causes: dict[str, str] = field(default_factory=dict)

    # Async control
    night_action_complete: asyncio.Event | None = None
    day_vote_complete: asyncio.Event | None = None
    hunter_action_complete: asyncio.Event | None = None
    game_task: asyncio.Task | None = None


class WWStore(GameStore[WerewolfRoom]):
    def __init__(self) -> None:
        super().__init__(WerewolfRoom)


# Singleton
store = WWStore()
