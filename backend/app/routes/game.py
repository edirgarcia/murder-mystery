"""Game routes: start, get card, guess, get solution."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Header

from ..config import MIN_PLAYERS
from ..game_state import store
from ..models import (
    ClueInfo,
    GamePhase,
    GuessRequest,
    GuessResponse,
    PlayerCardResponse,
    SolutionResponse,
    StartGameRequest,
)
from ..puzzle.pipeline import generate_puzzle
from .ws import broadcast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/games", tags=["game"])


@router.post("/{code}/start")
async def start_game(
    code: str,
    req: StartGameRequest | None = None,
    x_player_id: str = Header(...),
) -> dict:
    if req is None:
        req = StartGameRequest()
    difficulty = req.difficulty.value

    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")

    player = store.get_player(room, x_player_id)
    if not player or not player.is_host:
        raise HTTPException(status_code=403, detail="Only the host can start the game")

    if room.phase != GamePhase.LOBBY:
        raise HTTPException(status_code=400, detail="Game already started")

    if len(room.players) < MIN_PLAYERS:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least {MIN_PLAYERS} players",
        )

    room.difficulty = difficulty
    room.phase = GamePhase.GENERATING
    await broadcast(room, "game_starting", {"message": "Generating puzzle..."})

    # Run CPU-bound puzzle generation in a thread
    n = len(room.players)
    player_names = [p.name for p in room.players]
    loop = asyncio.get_running_loop()
    try:
        puzzle = await loop.run_in_executor(
            None, lambda: generate_puzzle(n, player_names=player_names, difficulty=difficulty)
        )
    except RuntimeError as e:
        room.phase = GamePhase.LOBBY
        await broadcast(room, "generation_failed", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Puzzle generation failed: {e}")

    room.solution = puzzle.solution
    room.murderer_name = puzzle.murderer_name
    room.murder_weapon = puzzle.murder_weapon
    room.cards = puzzle.cards
    room.murder_clue_dicts = [c.to_dict() for c in puzzle.murder_clues]
    room.phase = GamePhase.PLAYING

    await broadcast(room, "game_started", {"message": "The game has begun!"})
    return {"status": "started"}


@router.get("/{code}/card", response_model=PlayerCardResponse)
async def get_card(code: str, x_player_id: str = Header(...)) -> PlayerCardResponse:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase not in (GamePhase.PLAYING, GamePhase.FINISHED):
        raise HTTPException(status_code=400, detail="Game not in progress")

    card = store.get_player_card(room, x_player_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    return PlayerCardResponse(
        character_name=card.character_name,
        clues=[ClueInfo(type=c["type"], text=c["text"]) for c in card.to_dict()["clues"]],
    )


@router.post("/{code}/guess", response_model=GuessResponse)
async def make_guess(
    code: str, req: GuessRequest, x_player_id: str = Header(...)
) -> GuessResponse:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in guess phase")

    player = store.get_player(room, x_player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    room.guesses[player.id] = req.suspect_name
    correct = req.suspect_name == room.murderer_name

    await broadcast(
        room,
        "guess_made",
        {"player_name": player.name, "suspect": req.suspect_name, "correct": correct},
    )

    # Check if all players have guessed
    if len(room.guesses) >= len(room.players):
        room.phase = GamePhase.FINISHED
        await broadcast(
            room,
            "game_over",
            {"murderer": room.murderer_name},
        )

    return GuessResponse(
        correct=correct,
        suspect_name=req.suspect_name,
        actual_murderer=room.murderer_name if correct or room.phase == GamePhase.FINISHED else None,
    )


@router.get("/{code}/solution", response_model=SolutionResponse)
async def get_solution(code: str) -> SolutionResponse:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.FINISHED:
        raise HTTPException(status_code=400, detail="Game not finished yet")

    return SolutionResponse(
        murderer_name=room.murderer_name or "",
        murder_weapon=room.murder_weapon or "",
        solution=room.solution or {},
        murder_clues=[
            ClueInfo(type=c["type"], text=c["text"])
            for c in (room.murder_clue_dicts or [])
        ],
    )
