"""Werewolf-specific Pydantic models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..shared.models import GamePhase, PlayerInfo


class Role(str, Enum):
    VILLAGER = "villager"
    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    CUPID = "cupid"


class NightSubPhase(str, Enum):
    CUPID = "cupid"
    WEREWOLVES = "werewolves"
    SEER = "seer"
    WITCH = "witch"


class DaySubPhase(str, Enum):
    ANNOUNCEMENT = "announcement"
    DISCUSSION = "discussion"
    VOTING = "voting"
    VOTE_RESULT = "vote_result"
    HUNTER_REVENGE = "hunter_revenge"


class WinCondition(str, Enum):
    VILLAGERS = "villagers"
    WEREWOLVES = "werewolves"
    LOVERS = "lovers"


class StartWWRequest(BaseModel):
    discussion_seconds: int = Field(default=90, ge=30, le=300)


class NightActionRequest(BaseModel):
    action: str  # werewolf_vote, seer_investigate, witch_heal, witch_kill, witch_pass, cupid_link, hunter_shoot
    target: str | None = None
    target2: str | None = None  # for cupid_link (two targets)


class DayVoteRequest(BaseModel):
    target: str  # player_id or "skip"


class WWPlayerInfo(PlayerInfo):
    alive: bool = True
    role: Role | None = None


class WWGameInfo(BaseModel):
    code: str
    phase: GamePhase
    players: list[WWPlayerInfo]
    min_players: int
    max_players: int
    host_name: str
    night_number: int = 0
    day_number: int = 0
    night_sub_phase: str | None = None
    day_sub_phase: str | None = None
    alive_count: int = 0
    winner: str | None = None
