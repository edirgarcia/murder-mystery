"""Prisoner's Dilemma specific Pydantic models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from ..shared.models import GamePhase, PlayerInfo


class TeamColor(str, Enum):
    RED = "red"
    BLUE = "blue"


class Decision(str, Enum):
    TRUST = "trust"
    BETRAY = "betray"


class PDPlayerInfo(PlayerInfo):
    team: TeamColor | None = None
    spy_exposed: bool = False


class StartPDRequest(BaseModel):
    voting_seconds: int = Field(default=45, ge=15, le=180)
    accusation_seconds: int = Field(default=20, ge=10, le=90)


class VoteRequest(BaseModel):
    choice: Decision
    sabotage: bool = False


class AccusationRequest(BaseModel):
    accuse: bool = False
    target_id: str | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "AccusationRequest":
        if self.accuse and not self.target_id:
            raise ValueError("target_id is required when accuse is true")
        if not self.accuse:
            self.target_id = None
        return self


class PDGameInfo(BaseModel):
    code: str
    phase: GamePhase
    players: list[PDPlayerInfo]
    min_players: int
    max_players: int
    host_name: str
    current_round: int = 0
    total_rounds: int = 10
    round_phase: str | None = None
    voting_ends_at: str | None = None
    accusation_ends_at: str | None = None
    team_scores: dict[TeamColor, int] = Field(default_factory=dict)
    winner: str | None = None


class PDPrivateState(BaseModel):
    player_id: str
    player_name: str
    team: TeamColor
    is_spy: bool
    spy_active: bool
    sabotage_charges: int

