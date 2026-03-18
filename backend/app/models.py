"""Pydantic models for API requests/responses."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class GamePhase(str, Enum):
    LOBBY = "lobby"
    GENERATING = "generating"
    PLAYING = "playing"
    FINISHED = "finished"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    HARDER = "harder"
    HARDEST = "hardest"


# --- Requests ---


class CreateGameRequest(BaseModel):
    host_name: str = Field(..., min_length=1, max_length=30)


class StartGameRequest(BaseModel):
    difficulty: Difficulty = Difficulty.MEDIUM
    timer_minutes: int = Field(default=10, ge=5, le=30)


class JoinGameRequest(BaseModel):
    player_name: str = Field(..., min_length=1, max_length=30)


class GuessRequest(BaseModel):
    suspect_name: str


# --- Responses ---


class PlayerInfo(BaseModel):
    id: str
    name: str


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
    timer_duration_seconds: int | None = None
    started_at: str | None = None
    guesses_count: int = 0


class ClueInfo(BaseModel):
    type: str
    text: str


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


class CreateGameResponse(BaseModel):
    code: str
    host_id: str


class JoinGameResponse(BaseModel):
    player_id: str


# --- WebSocket events ---


class WSEvent(BaseModel):
    event: str
    data: dict = Field(default_factory=dict)
