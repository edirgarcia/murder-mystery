"""Murder mystery game routes: start, get card, guess, end, results."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header

from ..config import LIVE_GENERATE, MIN_PLAYERS
from ..game_state import GuessRecord, store
from ..models import (
    ClueInfo,
    GuessRequest,
    GuessResponse,
    LeaderboardEntry,
    PlayerCardResponse,
    ResultsResponse,
    StartGameRequest,
)
from ...shared.models import GamePhase, PlayerInfo
from ...shared.routes.ws import broadcast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mm/games", tags=["mm-game"])


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
                suspect_guessed="\u2014",
                correct=False,
                time_taken_seconds=None,
            ))

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


async def _advance_round(room) -> None:
    """Advance to the next round, start its timer, and broadcast."""
    room.current_round += 1
    room.round_started_at = datetime.now(timezone.utc)
    room.timer_task = asyncio.create_task(_round_expire(room, room.current_round))

    await broadcast(room, "round_advanced", {
        "round": room.current_round,
        "started_at": room.round_started_at.isoformat(),
        "duration_seconds": room.round_durations[room.current_round - 1],
    })


async def _round_expire(room, expected_round: int) -> None:
    """Sleep for the current round's duration, then advance or finish."""
    try:
        await asyncio.sleep(room.round_durations[expected_round - 1])
        if room.phase != GamePhase.PLAYING:
            return
        # Guard against race with host-triggered advance
        if room.current_round != expected_round:
            return
        if room.current_round < 3:
            await _advance_round(room)
        else:
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

    n = len(room.players)
    player_names = [p.name for p in room.players]
    loop = asyncio.get_running_loop()

    if LIVE_GENERATE:
        logger.info("LIVE_GENERATE enabled, generating puzzle live")
        try:
            puzzle = await loop.run_in_executor(
                None, lambda: generate_puzzle(n, player_names=player_names, difficulty=difficulty)
            )
        except RuntimeError as e:
            room.phase = GamePhase.LOBBY
            await broadcast(room, "generation_failed", {"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Puzzle generation failed: {e}")
    else:
        puzzle = await loop.run_in_executor(
            None, lambda: load_puzzle(n, player_names, difficulty=difficulty)
        )
        if not puzzle:
            room.phase = GamePhase.LOBBY
            await broadcast(room, "generation_failed", {"error": "No pre-generated puzzle available"})
            raise HTTPException(
                status_code=500,
                detail=f"No pre-generated puzzle for n={n} difficulty={difficulty}",
            )

    room.solution = puzzle.solution
    room.murderer_name = puzzle.murderer_name
    room.murder_weapon = puzzle.murder_weapon
    room.cards = puzzle.cards
    room.murder_clue_dicts = [c.to_dict() for c in puzzle.murder_clues]
    room.clue_round_assignments = puzzle.clue_round_assignments
    room.phase = GamePhase.PLAYING
    room.round_durations = [req.round_minutes * 60] * 3

    await broadcast(room, "game_started", {
        "message": "The game has begun!",
        "murder_weapon": room.murder_weapon,
        "player_names": [p.name for p in room.players],
    })
    return {"status": "started"}


@router.post("/{code}/begin")
async def begin_game(code: str, x_player_id: str = Header(...)) -> dict:
    """Start round 1. Called by the host after the intro sequence."""
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Only the host can begin the timer")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in playing phase")
    if room.started_at:
        raise HTTPException(status_code=400, detail="Timer already started")

    now = datetime.now(timezone.utc)
    room.started_at = now
    room.current_round = 1
    room.round_started_at = now
    room.timer_task = asyncio.create_task(_round_expire(room, 1))

    await broadcast(room, "round_started", {
        "round": 1,
        "started_at": now.isoformat(),
        "duration_seconds": room.round_durations[0],
        "total_rounds": 3,
    })
    return {"status": "round_started"}


@router.post("/{code}/advance")
async def advance_round(code: str, x_player_id: str = Header(...)) -> dict:
    """Host advances to next round early, or ends game if on round 3."""
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Only the host can advance rounds")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in playing phase")
    if room.current_round < 1:
        raise HTTPException(status_code=400, detail="Game not started yet")

    # Cancel current round timer
    if room.timer_task and not room.timer_task.done():
        room.timer_task.cancel()
        room.timer_task = None

    if room.current_round < 3:
        await _advance_round(room)
        return {"status": "advanced", "round": room.current_round}
    else:
        await _finish_game(room)
        return {"status": "finished"}


@router.get("/{code}/card", response_model=PlayerCardResponse)
async def get_card(code: str, x_player_id: str = Header(...)) -> PlayerCardResponse:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase not in (GamePhase.PLAYING, GamePhase.FINISHED):
        raise HTTPException(status_code=400, detail="Game not in progress")

    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host does not have a character card")

    card = store.get_player_card(room, x_player_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Get round assignments for this player's card
    player = store.get_player(room, x_player_id)
    player_idx = room.players.index(player)
    round_assignments = (
        room.clue_round_assignments[player_idx]
        if room.clue_round_assignments and player_idx < len(room.clue_round_assignments)
        else None
    )

    # Show at least round 1 clues (even before begin is called)
    visible_round = max(1, room.current_round)
    # In finished phase, show all clues
    if room.phase == GamePhase.FINISHED:
        visible_round = 3

    clue_dicts = card.to_dict()["clues"]
    clues = []
    for i, c in enumerate(clue_dicts):
        clue_round = round_assignments[i] if round_assignments else 1
        if clue_round <= visible_round:
            clues.append(ClueInfo(type=c["type"], text=c["text"], round=clue_round))

    return PlayerCardResponse(
        character_name=card.character_name,
        clues=clues,
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

    if room.current_round < 2:
        raise HTTPException(status_code=400, detail="Accusations are not allowed until Round 2")

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
from ...puzzle.pipeline import generate_puzzle  # noqa: E402
from ...puzzle.relabel import load_puzzle  # noqa: E402
