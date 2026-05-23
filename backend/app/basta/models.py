"""Basta specific Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ..shared.models import GamePhase, PlayerInfo
from .config import ROUND_SECONDS, ROUNDS_TO_PLAY


class StartBastaRequest(BaseModel):
    categories: list[str] | None = None
    rounds_to_play: int = Field(default=ROUNDS_TO_PLAY, ge=1, le=20)
    round_seconds: int = Field(default=ROUND_SECONDS, ge=5, le=300)
    host_paced: bool = False

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None

        cleaned: list[str] = []
        seen: set[str] = set()
        for category in value:
            name = category.strip()
            key = name.casefold()
            if name and key not in seen:
                cleaned.append(name[:40])
                seen.add(key)

        if not cleaned:
            raise ValueError("At least one category is required")
        if len(cleaned) > 12:
            raise ValueError("Basta supports up to 12 categories")
        return cleaned


class SubmitAnswersRequest(BaseModel):
    answers: dict[str, str]
    auto_submit: bool = False


class VetoRequest(BaseModel):
    category: str
    target_player_id: str


class CategoryResult(BaseModel):
    category: str
    answers: dict[str, str]
    points: dict[str, int]
    invalid_players: list[str]
    vetoed_players: list[str] = []


class RoundResultResponse(BaseModel):
    letter: str
    categories: list[str]
    category_results: list[CategoryResult]
    round_points: dict[str, int]
    scores: dict[str, int]
    winner_name: str | None


class BastaGameInfo(BaseModel):
    code: str
    phase: GamePhase
    players: list[PlayerInfo]
    min_players: int
    max_players: int
    host_name: str
    # Game-specific
    scores: dict[str, int] = {}
    current_round: int = 0
    round_phase: str | None = None
    categories: list[str] = []
    current_letter: str | None = None
    current_review_category: str | None = None
    current_review_index: int | None = None
    current_review_answers: list[dict] = []
    round_ends_at: str | None = None
    submissions_in: int = 0
    winner: str | None = None
    rounds_to_play: int = ROUNDS_TO_PLAY
    round_seconds: int = ROUND_SECONDS
    host_paced: bool = False
    last_round_result: RoundResultResponse | None = None


class PlayerScoreEntry(BaseModel):
    player_id: str
    player_name: str
    score: int
