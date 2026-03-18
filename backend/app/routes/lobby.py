"""Lobby routes: create and join games."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import MAX_PLAYERS
from ..game_state import store
from ..models import (
    CreateGameRequest,
    CreateGameResponse,
    GameInfo,
    GamePhase,
    JoinGameRequest,
    JoinGameResponse,
    PlayerInfo,
)

router = APIRouter(prefix="/api/games", tags=["lobby"])


@router.post("", response_model=CreateGameResponse)
async def create_game(req: CreateGameRequest) -> CreateGameResponse:
    room = store.create_room()
    host_id = store.set_host(room, req.host_name)
    return CreateGameResponse(code=room.code, host_id=host_id)


@router.post("/{code}/join", response_model=JoinGameResponse)
async def join_game(code: str, req: JoinGameRequest) -> JoinGameResponse:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.LOBBY:
        raise HTTPException(status_code=400, detail="Game already started")
    if len(room.players) >= MAX_PLAYERS:
        raise HTTPException(status_code=400, detail="Game is full")
    # Check for duplicate names (including host name)
    if req.player_name.lower() == room.host_name.lower():
        raise HTTPException(status_code=400, detail="Name already taken")
    if any(p.name.lower() == req.player_name.lower() for p in room.players):
        raise HTTPException(status_code=400, detail="Name already taken")

    player = store.add_player(room, req.player_name)
    return JoinGameResponse(player_id=player.id)


@router.get("/{code}", response_model=GameInfo)
async def get_game(code: str) -> GameInfo:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    # Include character names once puzzle is generated
    character_names = []
    if room.solution and "name" in room.solution:
        character_names = room.solution["name"]

    return GameInfo(
        code=room.code,
        phase=room.phase,
        players=[
            PlayerInfo(id=p.id, name=p.name)
            for p in room.players
        ],
        min_players=3,
        max_players=MAX_PLAYERS,
        character_names=character_names,
        murder_weapon=room.murder_weapon,
        difficulty=room.difficulty,
        host_name=room.host_name,
        timer_duration_seconds=room.duration_seconds if room.started_at else None,
        started_at=room.started_at.isoformat() if room.started_at else None,
        guesses_count=len(room.guesses),
    )
