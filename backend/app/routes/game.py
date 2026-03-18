"""Game routes: start, get card, guess, end, results."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header

from ..config import MIN_PLAYERS
from ..game_state import GuessRecord, store
from ..models import (
    ClueInfo,
    GamePhase,
    GuessRequest,
    GuessResponse,
    LeaderboardEntry,
    PlayerCardResponse,
    ResultsResponse,
    StartGameRequest,
)
from .ws import broadcast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/games", tags=["game"])


def _build_leaderboard(room) -> list[LeaderboardEntry]:
    """Build a sorted leaderboard: correct+fastest first, then incorrect, then no-guess."""
    entries: list[LeaderboardEntry] = []

    for player in room.players:
        guess = room.guesses.get(player.id)
        if guess:
            correct = guess.suspect_name == room.murderer_name
            time_taken = None
            if room.started_at:
                time_taken = (guess.guessed_at - room.started_at).total_seconds()
            entries.append(LeaderboardEntry(
                rank=0,
                player_name=player.name,
                suspect_guessed=guess.suspect_name,
                correct=correct,
                time_taken_seconds=time_taken,
            ))
        else:
            entries.append(LeaderboardEntry(
                rank=0,
                player_name=player.name,
                suspect_guessed="—",
                correct=False,
                time_taken_seconds=None,
            ))

    # Sort: correct+fastest first, then incorrect by time, then no-guess
    def sort_key(e: LeaderboardEntry):
        if e.correct:
            return (0, e.time_taken_seconds or 0)
        if e.time_taken_seconds is not None:
            return (1, e.time_taken_seconds)
        return (2, 0)

    entries.sort(key=sort_key)
    for i, e in enumerate(entries):
        e.rank = i + 1

    return entries


async def _finish_game(room) -> None:
    """End the game: set phase, cancel timer, broadcast leaderboard."""
    room.phase = GamePhase.FINISHED
    if room.timer_task and not room.timer_task.done():
        room.timer_task.cancel()
        room.timer_task = None

    leaderboard = _build_leaderboard(room)
    await broadcast(
        room,
        "game_over",
        {
            "murderer": room.murderer_name,
            "leaderboard": [e.model_dump() for e in leaderboard],
        },
    )


async def _timer_expire(room) -> None:
    """Sleep for the game duration, then finish the game."""
    try:
        await asyncio.sleep(room.duration_seconds)
        if room.phase == GamePhase.PLAYING:
            await _finish_game(room)
    except asyncio.CancelledError:
        pass


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

    if not store.is_host(room, x_player_id):
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
    room.duration_seconds = req.timer_minutes * 60

    await broadcast(room, "game_started", {
        "message": "The game has begun!",
        "murder_weapon": room.murder_weapon,
        "player_names": [p.name for p in room.players],
    })
    return {"status": "started"}


@router.post("/{code}/begin")
async def begin_game(code: str, x_player_id: str = Header(...)) -> dict:
    """Start the countdown timer. Called by the host after the intro sequence."""
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Only the host can begin the timer")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in playing phase")
    if room.started_at:
        raise HTTPException(status_code=400, detail="Timer already started")

    room.started_at = datetime.now(timezone.utc)
    room.timer_task = asyncio.create_task(_timer_expire(room))

    await broadcast(room, "timer_started", {
        "started_at": room.started_at.isoformat(),
        "duration_seconds": room.duration_seconds,
    })
    return {"status": "timer_started"}


@router.get("/{code}/card", response_model=PlayerCardResponse)
async def get_card(code: str, x_player_id: str = Header(...)) -> PlayerCardResponse:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase not in (GamePhase.PLAYING, GamePhase.FINISHED):
        raise HTTPException(status_code=400, detail="Game not in progress")

    # Host cannot get a card
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host does not have a character card")

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

    # Host cannot guess
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host cannot guess")

    player = store.get_player(room, x_player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    if player.id in room.guesses:
        raise HTTPException(status_code=400, detail="Already guessed")

    now = datetime.now(timezone.utc)
    room.guesses[player.id] = GuessRecord(suspect_name=req.suspect_name, guessed_at=now)

    await broadcast(
        room,
        "guess_made",
        {
            "player_name": player.name,
            "guesses_count": len(room.guesses),
            "total_players": len(room.players),
        },
    )

    # Auto-end if all players have guessed
    if len(room.guesses) >= len(room.players):
        await _finish_game(room)

    return GuessResponse(
        status="locked_in",
        guessed_at=now.isoformat(),
    )


@router.post("/{code}/end")
async def end_game(code: str, x_player_id: str = Header(...)) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Only the host can end the game")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")

    await _finish_game(room)
    return {"status": "finished"}


@router.get("/{code}/results", response_model=ResultsResponse)
async def get_results(code: str) -> ResultsResponse:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.FINISHED:
        raise HTTPException(status_code=400, detail="Game not finished yet")

    leaderboard = _build_leaderboard(room)
    return ResultsResponse(
        murderer_name=room.murderer_name or "",
        murder_weapon=room.murder_weapon or "",
        leaderboard=leaderboard,
        murder_clues=[
            ClueInfo(type=c["type"], text=c["text"])
            for c in (room.murder_clue_dicts or [])
        ],
    )


# Keep import at bottom to avoid circular import issues
from ..puzzle.pipeline import generate_puzzle  # noqa: E402
