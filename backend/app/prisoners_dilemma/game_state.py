"""Prisoner's Dilemma game state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from ..shared.game_state import BaseGameRoom, GameStore
from .models import TeamColor


@dataclass
class PDPlayer:
    id: str
    name: str
    team: TeamColor | None = None
    is_spy: bool = False
    spy_active: bool = True
    spy_exposed: bool = False
    sabotage_charges: int = 0


@dataclass
class PDRoom(BaseGameRoom):
    game_players: dict[str, PDPlayer] = field(default_factory=dict)
    team_scores: dict[TeamColor, int] = field(
        default_factory=lambda: {
            TeamColor.RED: 0,
            TeamColor.BLUE: 0,
        }
    )
    current_round: int = 0
    total_rounds: int = 10
    round_phase: str | None = None
    current_votes: dict[str, str] = field(default_factory=dict)
    sabotage_requests: dict[str, bool] = field(default_factory=dict)
    current_accusations: dict[str, str | None] = field(default_factory=dict)
    voting_ends_at: str | None = None
    accusation_ends_at: str | None = None
    winner: str | None = None
    vote_complete: asyncio.Event | None = None
    accusation_complete: asyncio.Event | None = None
    narration_ack: asyncio.Event | None = None
    game_task: asyncio.Task | None = None
    voting_seconds: int = 45
    accusation_seconds: int = 20


class PDStore(GameStore[PDRoom]):
    def __init__(self) -> None:
        super().__init__(PDRoom)


store = PDStore()
