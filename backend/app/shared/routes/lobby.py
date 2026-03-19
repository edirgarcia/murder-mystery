"""Shared lobby routes factory: create and join games."""

from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, HTTPException

from ..game_state import BaseGameRoom, GameStore, Player
from ..models import (
    CreateGameRequest,
    CreateGameResponse,
    GamePhase,
    JoinGameRequest,
    JoinGameResponse,
    PlayerInfo,
)


def create_lobby_router(
    store: GameStore,
    max_players: int,
    game_info_builder: Callable[[BaseGameRoom], dict],
    prefix: str,
) -> APIRouter:
    """Create a lobby router bound to a specific game store.

    Args:
        store: The game store instance.
        max_players: Maximum number of players per room.
        game_info_builder: Callable that takes a room and returns a dict for the game info response.
        prefix: API prefix for the router (e.g. "/api/mm/games").
    """
    router = APIRouter(prefix=prefix, tags=["lobby"])

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
        if len(room.players) >= max_players:
            raise HTTPException(status_code=400, detail="Game is full")
        # Check for duplicate names (including host name)
        if req.player_name.lower() == room.host_name.lower():
            raise HTTPException(status_code=400, detail="Name already taken")
        if any(p.name.lower() == req.player_name.lower() for p in room.players):
            raise HTTPException(status_code=400, detail="Name already taken")

        player = store.add_player(room, req.player_name)
        return JoinGameResponse(player_id=player.id)

    @router.get("/{code}")
    async def get_game(code: str) -> dict:
        room = store.get_room(code)
        if not room:
            raise HTTPException(status_code=404, detail="Game not found")
        return game_info_builder(room)

    return router
