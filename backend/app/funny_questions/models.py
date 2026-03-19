"""Funny questions specific Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..shared.models import GamePhase, PlayerInfo


class StartFQRequest(BaseModel):
    categories: list[str] | None = None
    max_spice: int = Field(default=2, ge=1, le=3)
    points_to_win: int = Field(default=20, ge=5, le=50)


class VoteRequest(BaseModel):
    voted_for: str  # player_id


class FQGameInfo(BaseModel):
    code: str
    phase: GamePhase
    players: list[PlayerInfo]
    min_players: int
    max_players: int
    host_name: str
    # Game-specific
    scores: dict[str, int] = {}
    current_round: int = 0
    round_phase: str | None = None  # "voting" | "reveal" | None
    current_question: str | None = None
    shame_holder: str | None = None
    voting_ends_at: str | None = None
    winner: str | None = None
    points_to_win: int = 20


class PlayerScoreEntry(BaseModel):
    player_id: str
    player_name: str
    score: int
    has_shame: bool


class RoundResultResponse(BaseModel):
    question: str
    most_voted: str | None
    most_voted_name: str | None
    vote_breakdown: dict[str, list[str]]  # {target_name: [voter_names]}
    point_deltas: dict[str, int]  # {player_name: delta}
    scores: dict[str, int]  # {player_name: total}
    shame_holder_name: str | None
    winner_name: str | None
