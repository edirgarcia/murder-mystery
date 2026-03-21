"""Murder mystery specific Pydantic models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..shared.models import GamePhase, PlayerInfo


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    HARDER = "harder"
    HARDEST = "hardest"


class StartGameRequest(BaseModel):
    difficulty: Difficulty = Difficulty.MEDIUM
    round_minutes: int = Field(default=5, ge=1, le=15)


class GuessRequest(BaseModel):
    suspect_name: str


class GameInfo(BaseModel):
    code: str
    phase: GamePhase
    players: list[PlayerInfo]
    min_players: int
    max_players: int
    character_names: list[str] = []
    murder_weapon: str | None = None
    difficulty: str | None = None
    host_name: str = ""
    current_round: int = 0
    round_durations: list[int] = []
    round_started_at: str | None = None
    started_at: str | None = None
    guesses_count: int = 0


class ClueInfo(BaseModel):
    type: str
    text: str
    round: int = 1


class PlayerCardResponse(BaseModel):
    character_name: str
    clues: list[ClueInfo]


class GuessResponse(BaseModel):
    status: str
    guessed_at: str


class LeaderboardEntry(BaseModel):
    rank: int
    player_name: str
    suspect_guessed: str
    correct: bool
    time_taken_seconds: float | None = None


class ResultsResponse(BaseModel):
    murderer_name: str
    murder_weapon: str
    leaderboard: list[LeaderboardEntry]
    murder_clues: list[ClueInfo]
