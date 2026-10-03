"""Trading City routes and the async game loop.

The loop owns pacing (timers, phase transitions); every rule lives in
``engine.TradingGame``. Player actions mutate the engine synchronously (so the
first valid bid wins, spec §22), then wake the loop and push fresh state.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
from typing import Callable

from fastapi import APIRouter, Header, HTTPException

from ..config import MIN_PLAYERS
from ..engine import RuleError, TradingGame
from ..game_state import TCRoom, store
from ..models import BidRequest, BuildRequest, BundleRequest, ClaimCityRequest, StartTCRequest
from ..views import private_view, public_view
from ...shared.models import GamePhase
from ...shared.routes.ws import broadcast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tc/games", tags=["tc-game"])


# --- Helpers ---


def _get_room(code: str) -> TCRoom:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    return room


def _get_game(room: TCRoom) -> TradingGame:
    if room.game is None or room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    return room.game


def _require_player(room: TCRoom, player_id: str) -> None:
    if store.get_player(room, player_id) is None:
        raise HTTPException(status_code=403, detail="Only players can do that")


def _rule(fn: Callable[[], object]) -> object:
    try:
        return fn()
    except RuleError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


async def _send_to_player(room: TCRoom, player_id: str, event: str, data: dict) -> None:
    ws = room.connections.get(player_id)
    if not ws:
        return
    try:
        await ws.send_text(json.dumps({"event": event, "data": data}))
    except Exception:
        room.connections.pop(player_id, None)


async def _push(room: TCRoom) -> None:
    """Broadcast public state and send each player their private state."""
    game = room.game
    if game is None:
        return
    await broadcast(room, "state", public_view(game, room.deadline, time.time(), room.ready))
    for player in room.players:
        await _send_to_player(room, player.id, "private_state", private_view(game, player.id))


async def _after_action(room: TCRoom) -> None:
    room.changed.set()
    await _push(room)


async def _wait_until(
    room: TCRoom, done: Callable[[], bool], deadline: Callable[[], float | None]
) -> bool:
    """Wait until ``done()`` or the (possibly moving) deadline passes. Returns done()."""
    while True:
        room.changed.clear()
        if done():
            return True
        end = deadline()
        remaining = None if end is None else end - time.time()
        if remaining is not None and remaining <= 0:
            return False
        try:
            await asyncio.wait_for(room.changed.wait(), timeout=remaining)
        except asyncio.TimeoutError:
            pass


async def _timed_phase(room: TCRoom, seconds: int, done: Callable[[], bool]) -> bool:
    room.deadline = time.time() + seconds
    await _push(room)
    finished = await _wait_until(room, done, lambda: room.deadline)
    room.deadline = None
    return finished


async def _summary(room: TCRoom, seconds: int) -> None:
    """A read-only screen: wait until every player taps Continue, or the timer runs out."""
    room.ready = set()
    try:
        await _timed_phase(room, seconds, lambda: len(room.ready) >= len(room.players))
    finally:
        room.ready = None


async def _pause(room: TCRoom, seconds: int) -> None:
    room.deadline = time.time() + seconds
    await _push(room)
    await asyncio.sleep(seconds)
    room.deadline = None


# --- Narration ---
# Audio lives in frontend/public/trading-city/audio/ (voice: Emmanuel Matte, see docs/audio.md).
# The host dashboard plays each line and acks when done; lines are text + file.

INTRO = [
    ("Welcome to Trading City.", "tc-welcome.mp3"),
    ("Each of you runs a city. Every city produces some goods, and lacks others.", "tc-cities.mp3"),
    ("Every round, your city must pay its upkeep. Fall short, and your city makes less.", "tc-upkeep.mp3"),
    ("No city can feed itself alone. You'll have to trade.", "tc-trade.mp3"),
    ("Build projects to earn victory points. The highest score at the end wins.", "tc-goal.mp3"),
    ("Now pick your city on your phone. First come, first served.", "tc-choose.mp3"),
]

# Just-in-time tutorial: played the first time each phase happens.
TUTORIAL = {
    "production": [
        ("Your city has produced its goods and collected its income. Check your phone.", "tc-production.mp3"),
    ],
    "market_study": [
        ("Your goods can also build projects. Before you sell, check the project board, "
         "and keep what you'll need.", "tc-lots-projects.mp3"),
    ],
    "lot_creation": [
        ("Choose what to sell. Put your extra goods into a secret lot. "
         "Nobody sees it until it's up for auction.", "tc-lots.mp3"),
    ],
    "auction": [
        ("Lots are revealed one at a time. Bid on your phone. "
         "The highest bid takes the whole lot.", "tc-auction.mp3"),
        ("Late bids add time to the clock, so there's no sniping.", "tc-auction-clock.mp3"),
    ],
    "projects": [
        ("Time to build. Taking turns, each city may build one project.", "tc-projects.mp3"),
        ("City projects grow your economy. Market projects change supply and demand for everyone. "
         "Prestige projects earn victory points, but also cost gold.", "tc-project-types.mp3"),
    ],
    "upkeep": [
        ("Upkeep is due. Pay it in full, and any shortage is cleared.", "tc-upkeep-due.mp3"),
    ],
    "cleanup": [
        ("Your storehouse can only hold so much. Anything over the limit must be thrown away.", "tc-storage.mp3"),
    ],
}

FINAL_ROUND = ("Final round. Make it count.", "tc-final-round.mp3")
GAME_OVER = ("The markets are closed. Let's see who built the greatest city.", "tc-game-over.mp3")

NARRATION_TIMEOUT_SECONDS = 15


async def _narrate(room: TCRoom, lines: list[tuple[str, str]], *, skippable: bool) -> None:
    """Play lines on the dashboard one at a time, then clear the caption."""
    for text, sound in lines:
        if skippable and room.skip_intro is not None and room.skip_intro.is_set():
            break
        room.narration_ack = asyncio.Event()
        await broadcast(room, "intro_narration", {"text": text, "sound": sound})
        if room.connections:
            try:
                await asyncio.wait_for(room.narration_ack.wait(), timeout=NARRATION_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                pass
        room.narration_ack = None
    await broadcast(room, "intro_done", {})


async def _explain(room: TCRoom, phase: str) -> None:
    """Explain a phase the first time it happens (unless the host skipped the tutorial)."""
    if phase in room.explained or (room.skip_intro is not None and room.skip_intro.is_set()):
        return
    room.explained.add(phase)
    await _narrate(room, TUTORIAL[phase], skippable=True)


# --- Game loop ---


async def _run_auctions(room: TCRoom, game: TradingGame) -> None:
    game.start_auctions()
    if game.auction_queue:
        await _push(room)
        await _explain(room, "auction")
    delay = game.config.ai_bid_delay_seconds
    while game.reveal_next_lot(time.time()) is not None:
        await _push(room)
        # AI cities answer `delay` seconds after the first change they haven't seen yet.
        # Further changes don't push that back, so a busy room can't starve them.
        ai_due: float | None = time.time() + delay
        while True:
            room.changed.clear()
            now = time.time()
            # No await between this check and resolution, so no bid can slip in.
            if game.auction_settled() or now >= game.auction.ends_at:
                break
            if ai_due is not None and now >= ai_due:
                # Keep answering each other until no AI raises.
                ai_due = now + delay if game.run_ai_auction_step(now) else None
                await _push(room)
                continue
            wake_at = game.auction.ends_at if ai_due is None else min(ai_due, game.auction.ends_at)
            try:
                await asyncio.wait_for(room.changed.wait(), timeout=wake_at - now)
                if ai_due is None:
                    ai_due = time.time() + delay  # a human acted: give AI a chance to answer
            except asyncio.TimeoutError:
                pass
        game.resolve_auction()
        await _pause(room, game.config.lot_result_display_seconds)


async def _run_projects(room: TCRoom, game: TradingGame) -> None:
    game.start_projects()
    await _push(room)
    await _explain(room, "projects")
    while not game.projects_done():
        actor = game.current_project_player()
        acted = await _timed_phase(
            room,
            game.config.project_turn_seconds,
            lambda: game.current_project_player() != actor,
        )
        if not acted:
            game.pass_project(actor)


async def _run_game(room: TCRoom) -> None:
    game = room.game
    cfg = game.config
    try:
        # Give clients time to navigate and connect.
        await asyncio.sleep(2)
        for _ in range(20):
            if room.connections:
                break
            await asyncio.sleep(0.25)

        # Stays set for the whole game: "Skip intro" also skips later tutorial lines.
        room.skip_intro = asyncio.Event()
        await _push(room)
        await _narrate(room, INTRO, skippable=True)
        await _timed_phase(room, cfg.city_selection_seconds, game.all_claimed)
        game.finish_city_selection()

        for _ in range(cfg.total_rounds):
            game.start_round()
            await _push(room)
            if game.round == cfg.total_rounds and cfg.total_rounds > 1:
                await _narrate(room, [FINAL_ROUND], skippable=False)
            await _explain(room, "production")
            await _summary(room, cfg.production_display_seconds)

            game.open_market_study()
            await _push(room)
            await _explain(room, "market_study")
            await _summary(room, cfg.market_study_seconds)

            game.open_lot_creation()
            await _push(room)
            await _explain(room, "lot_creation")
            await _timed_phase(room, cfg.lot_creation_seconds, game.all_lots_submitted)

            await _run_auctions(room, game)
            await _run_projects(room, game)

            game.run_upkeep()
            await _push(room)
            await _explain(room, "upkeep")
            await _summary(room, cfg.upkeep_display_seconds)

            if game.start_cleanup():
                await _push(room)
                await _explain(room, "cleanup")
                await _timed_phase(room, cfg.discard_seconds, lambda: not game.pending_discards)
            game.finish_cleanup()

        await _narrate(room, [GAME_OVER], skippable=False)
        room.phase = GamePhase.FINISHED
        await _push(room)
        await broadcast(room, "game_over", {})
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Trading City loop crashed for room %s", room.code)
    finally:
        room.deadline = None
        room.game_task = None


# --- Endpoints ---


@router.post("/{code}/start")
async def start_game(
    code: str,
    req: StartTCRequest | None = None,
    x_player_id: str = Header(...),
) -> dict:
    req = req or StartTCRequest()
    room = _get_room(code)
    if not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Only the host can start the game")
    if room.phase != GamePhase.LOBBY:
        raise HTTPException(status_code=400, detail="Game already started")
    if len(room.players) < MIN_PLAYERS:
        raise HTTPException(status_code=400, detail=f"Need at least {MIN_PLAYERS} players")

    room.config = dataclasses.replace(
        room.config,
        total_rounds=req.total_rounds,
        auction_seconds=req.auction_seconds,
        lot_creation_seconds=req.lot_creation_seconds,
        project_turn_seconds=req.project_turn_seconds,
        ai_strategy=req.ai_strategy,
        ai_project_priority=req.ai_project_priority,
    )
    room.game = TradingGame([(p.id, p.name) for p in room.players], config=room.config)
    room.phase = GamePhase.PLAYING

    await broadcast(room, "game_started", {})
    room.game_task = asyncio.create_task(_run_game(room))
    return {"status": "started"}


@router.get("/{code}/state")
async def get_state(code: str, x_player_id: str = Header(...)) -> dict:
    room = _get_room(code)
    if room.game is None:
        raise HTTPException(status_code=400, detail="Game has not started yet")
    is_player = store.get_player(room, x_player_id) is not None
    if not is_player and not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Not part of this game")
    return {
        "public": public_view(room.game, room.deadline, time.time(), room.ready),
        "private": private_view(room.game, x_player_id) if is_player else None,
    }


@router.post("/{code}/claim")
async def claim_city(code: str, req: ClaimCityRequest, x_player_id: str = Header(...)) -> dict:
    room = _get_room(code)
    game = _get_game(room)
    _require_player(room, x_player_id)
    _rule(lambda: game.claim_city(x_player_id, req.slot))
    await _after_action(room)
    return {"status": "claimed"}


@router.post("/{code}/lot")
async def submit_lot(code: str, req: BundleRequest, x_player_id: str = Header(...)) -> dict:
    room = _get_room(code)
    game = _get_game(room)
    _require_player(room, x_player_id)
    _rule(lambda: game.submit_lot(x_player_id, req.contents))
    await _after_action(room)
    return {"status": "locked"}


@router.post("/{code}/bid")
async def place_bid(code: str, req: BidRequest, x_player_id: str = Header(...)) -> dict:
    room = _get_room(code)
    game = _get_game(room)
    _require_player(room, x_player_id)
    slot = _rule(lambda: game.city_of(x_player_id).index)
    _rule(lambda: game.place_bid(slot, req.amount, time.time()))
    await _after_action(room)
    return {"status": "bid"}


@router.post("/{code}/auction-pass")
async def pass_auction(code: str, x_player_id: str = Header(...)) -> dict:
    room = _get_room(code)
    game = _get_game(room)
    _require_player(room, x_player_id)
    slot = _rule(lambda: game.city_of(x_player_id).index)
    _rule(lambda: game.pass_auction(slot, time.time()))
    await _after_action(room)
    return {"status": "passed"}


@router.post("/{code}/build")
async def build_project(code: str, req: BuildRequest, x_player_id: str = Header(...)) -> dict:
    room = _get_room(code)
    game = _get_game(room)
    _require_player(room, x_player_id)
    _rule(lambda: game.build_project(x_player_id, req.slot_index))
    await _after_action(room)
    return {"status": "built"}


@router.post("/{code}/project-pass")
async def pass_project(code: str, x_player_id: str = Header(...)) -> dict:
    room = _get_room(code)
    game = _get_game(room)
    _require_player(room, x_player_id)
    _rule(lambda: game.pass_project(x_player_id))
    await _after_action(room)
    return {"status": "passed"}


@router.post("/{code}/ready")
async def mark_ready(code: str, x_player_id: str = Header(...)) -> dict:
    room = _get_room(code)
    _get_game(room)
    _require_player(room, x_player_id)
    if room.ready is None:
        raise HTTPException(status_code=400, detail="Nothing to continue from")
    room.ready.add(x_player_id)
    await _after_action(room)
    return {"status": "ready"}


@router.post("/{code}/discard")
async def discard(code: str, req: BundleRequest, x_player_id: str = Header(...)) -> dict:
    room = _get_room(code)
    game = _get_game(room)
    _require_player(room, x_player_id)
    _rule(lambda: game.discard(x_player_id, req.contents))
    await _after_action(room)
    return {"status": "discarded"}
