"""Shared Pydantic models for API requests/responses."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class GamePhase(str, Enum):
    LOBBY = "lobby"
    GENERATING = "generating"
    PLAYING = "playing"
    FINISHED = "finished"


# --- Requests ---


class CreateGameRequest(BaseModel):
    host_name: str = Field(..., min_length=1, max_length=30)


class JoinGameRequest(BaseModel):
    player_name: str = Field(..., min_length=1, max_length=30)


# --- Responses ---


class PlayerInfo(BaseModel):
    id: str
    name: str


class CreateGameResponse(BaseModel):
    code: str
    host_id: str


class JoinGameResponse(BaseModel):
    player_id: str


# --- WebSocket events ---


class WSEvent(BaseModel):
    event: str
    data: dict = Field(default_factory=dict)
