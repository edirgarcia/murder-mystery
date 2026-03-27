"""Funny questions game routes: start, vote, scores."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Header

from ..config import MIN_PLAYERS, VOTE_SECONDS, REVEAL_SECONDS
from ..game_state import store
from ..models import (
    PlayerScoreEntry,
    RoundResultResponse,
    StartFQRequest,
    VoteRequest,
)
from ..questions import draw_questions
from ..scoring import score_round
from ...shared.models import GamePhase
from ...shared.routes.ws import broadcast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fq/games", tags=["fq-game"])


async def _fq_narrate(room, text: str, sound: str) -> None:
    """Broadcast a narration line and wait for dashboard audio to finish."""
    room.narration_ack = asyncio.Event()
    await broadcast(room, "intro_narration", {"text": text, "sound": sound})
    if room.connections:
        try:
            await asyncio.wait_for(room.narration_ack.wait(), timeout=15)
        except asyncio.TimeoutError:
            pass
    room.narration_ack = None


@router.post("/{code}/reset")
async def reset_game(
    code: str,
    x_player_id: str = Header(...),
) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Only the host can reset")
    if room.phase != GamePhase.FINISHED:
        raise HTTPException(status_code=400, detail="Game is not finished")

    # Cancel running tasks
    if room.game_task and not room.game_task.done():
        room.game_task.cancel()
    room.game_task = None

    # Reset game state, keep players and room info
    room.phase = GamePhase.LOBBY
    room.scores = {}
    room.current_round = 0
    room.round_phase = None
    room.shame_holder = None
    room.questions = []
    room.question_index = 0
    room.current_votes = {}
    room.vote_complete = None
    room.next_round = None
    room.narration_ack = None
    room.voting_ends_at = None
    room.winner = None

    await broadcast(room, "game_reset", {})
    return {"status": "reset"}


async def _run_fq_intro(room) -> None:
    """Run intro narration explaining the rules, then start the game loop."""
    try:
        # Give clients time to navigate from lobby to dashboard/vote pages
        # and establish new WS connections
        await asyncio.sleep(2)
        # Then wait for at least one WS connection
        for _ in range(20):
            if room.connections:
                break
            await asyncio.sleep(0.25)

        narration = [
            ("Welcome to Silly Questions!", "fq-welcome.mp3"),
            ("Here's how it works.", "fq-how.mp3"),
            (
                "A question will appear on the big screen.",
                "fq-question.mp3",
            ),
            (
                "Vote on your phone for who in the group it fits best.",
                "fq-vote.mp3",
            ),
            (
                "If you vote with the majority, you earn a point.",
                "fq-scoring.mp3",
            ),
            (
                "Vote for yourself and get the most votes? That's three points!",
                "fq-selfvote.mp3",
            ),
            (
                "If you vote for yourself and nobody else does, you get the mark of Shame.",
                "fq-shame.mp3",
            ),
            (
                "While holding the mark of Shame, you can't earn any points.",
                "fq-no-points.mp3",
            ),
            (
                "To clear it, vote for yourself and hope someone else does too, or wait for someone else to get the mark.",
                "fq-clear-shame.mp3",
            ),
            (
                "First to reach the target score wins!",
                "fq-win.mp3",
            ),
            ("Let the games begin!", "fq-begin.mp3"),
        ]
        for text, sound in narration:
            await _fq_narrate(room, text, sound)

        # Clear the overlay before starting gameplay
        await broadcast(room, "intro_done", {})

        # Now start the actual game loop
        await _run_game(room)
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("FQ intro crashed for room %s", room.code)


@router.post("/{code}/start")
async def start_game(
    code: str,
    req: StartFQRequest | None = None,
    x_player_id: str = Header(...),
) -> dict:
    if req is None:
        req = StartFQRequest()

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

    # Draw enough questions for a full game (generous upper bound)
    room.questions = draw_questions(
        count=50,
        categories=req.categories,
        max_spice=req.max_spice,
    )
    if not room.questions:
        raise HTTPException(status_code=400, detail="No questions match the selected filters")

    room.points_to_win = req.points_to_win
    room.host_paced = req.host_paced
    room.scores = {p.id: 0 for p in room.players}
    room.phase = GamePhase.PLAYING

    # Start intro → game loop (intro narration then auto-starts game loop)
    room.game_task = asyncio.create_task(_run_fq_intro(room))
    print(f"[FQ] Intro+game task created for room {code}, players={len(room.players)}")

    await broadcast(room, "game_started", {
        "message": "Game is starting!",
        "points_to_win": room.points_to_win,
        "host_paced": room.host_paced,
    })

    return {"status": "started"}


@router.post("/{code}/vote")
async def submit_vote(
    code: str,
    req: VoteRequest,
    x_player_id: str = Header(...),
) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    if room.round_phase != "voting":
        raise HTTPException(status_code=400, detail="Not in voting phase")
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host cannot vote")

    player = store.get_player(room, x_player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    if player.id in room.current_votes:
        raise HTTPException(status_code=400, detail="Already voted")

    # Validate target is a player in this room
    valid_targets = {p.id for p in room.players}
    if req.voted_for not in valid_targets:
        raise HTTPException(status_code=400, detail="Invalid vote target")

    room.current_votes[player.id] = req.voted_for
    print(f"[FQ] Vote from {player.id}: {len(room.current_votes)}/{len(room.players)} votes, vote_complete={room.vote_complete is not None}")

    await broadcast(room, "vote_cast", {
        "votes_in": len(room.current_votes),
        "total_players": len(room.players),
    })

    # If all players have voted, signal early completion
    if len(room.current_votes) >= len(room.players) and room.vote_complete:
        print(f"[FQ] All voted! Signaling early completion")
        room.vote_complete.set()

    return {"status": "voted"}


@router.get("/{code}/scores")
async def get_scores(code: str) -> list[PlayerScoreEntry]:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")

    entries = []
    for p in room.players:
        entries.append(PlayerScoreEntry(
            player_id=p.id,
            player_name=p.name,
            score=room.scores.get(p.id, 0),
            has_shame=room.shame_holder == p.id,
        ))
    entries.sort(key=lambda e: e.score, reverse=True)
    return entries


@router.post("/{code}/next")
async def next_question(
    code: str,
    x_player_id: str = Header(...),
) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Only the host can advance")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    if room.next_round:
        room.next_round.set()
    return {"status": "ok"}


async def _run_game(room) -> None:
    """Main game loop: question → vote → score → reveal → repeat."""
    print(f"[FQ] _run_game STARTED for room {room.code}")
    try:
        while room.phase == GamePhase.PLAYING:
            # Check if we've run out of questions
            if room.question_index >= len(room.questions):
                print(f"[FQ] Room {room.code}: out of questions")
                break

            question = room.questions[room.question_index]
            room.current_round += 1
            room.current_votes = {}
            room.round_phase = "voting"
            room.vote_complete = asyncio.Event()

            # Calculate voting deadline
            voting_ends_at = datetime.now(timezone.utc) + timedelta(seconds=VOTE_SECONDS)
            room.voting_ends_at = voting_ends_at.isoformat()

            print(f"[FQ] Room {room.code}: round {room.current_round} VOTING ({VOTE_SECONDS}s), connections={len(room.connections)}")

            # Broadcast new question
            await broadcast(room, "new_question", {
                "round": room.current_round,
                "question": question.text,
                "voting_ends_at": room.voting_ends_at,
                "players": [{"id": p.id, "name": p.name} for p in room.players],
            })

            # Wait for timer or all votes
            try:
                remaining = (voting_ends_at - datetime.now(timezone.utc)).total_seconds()
                print(f"[FQ] Room {room.code}: waiting for votes (remaining={remaining:.1f}s)")
                if remaining > 0:
                    await asyncio.wait_for(room.vote_complete.wait(), timeout=remaining)
                print(f"[FQ] Room {room.code}: round {room.current_round} ALL VOTED")
            except asyncio.TimeoutError:
                print(f"[FQ] Room {room.code}: round {room.current_round} TIMED OUT ({len(room.current_votes)}/{len(room.players)} votes)")

            print(f"[FQ] Room {room.code}: round {room.current_round} → REVEAL")
            room.round_phase = "reveal"
            room.voting_ends_at = None

            # Score the round
            player_ids = [p.id for p in room.players]
            result = score_round(room.current_votes, player_ids, room.shame_holder)

            # Apply points
            for pid, delta in result.points.items():
                room.scores[pid] = room.scores.get(pid, 0) + delta

            # Update shame
            prev_shame_holder = room.shame_holder
            if result.shame_cleared:
                room.shame_holder = None
            if result.new_shame:
                room.shame_holder = result.new_shame

            # Build name-based breakdown for display
            id_to_name = {p.id: p.name for p in room.players}
            name_vote_breakdown = {}
            for target_id, voter_ids in result.vote_breakdown.items():
                target_name = id_to_name.get(target_id, target_id)
                name_vote_breakdown[target_name] = [id_to_name.get(v, v) for v in voter_ids]

            name_deltas = {id_to_name.get(pid, pid): delta for pid, delta in result.points.items()}
            name_scores = {id_to_name.get(pid, pid): score for pid, score in room.scores.items()}

            most_voted_name = id_to_name.get(result.most_voted, None) if result.most_voted else None
            shame_name = id_to_name.get(room.shame_holder, None) if room.shame_holder else None
            prev_shame_name = id_to_name.get(prev_shame_holder, None) if prev_shame_holder else None

            # Check for winner
            winner_name = None
            for pid, score in room.scores.items():
                if score >= room.points_to_win:
                    room.winner = pid
                    winner_name = id_to_name.get(pid, pid)
                    break

            # Broadcast round result
            print(f"[FQ] Room {room.code}: broadcasting round_result, connections={len(room.connections)}")
            await broadcast(room, "round_result", {
                "question": question.text,
                "most_voted": result.most_voted,
                "most_voted_name": most_voted_name,
                "vote_breakdown": name_vote_breakdown,
                "point_deltas": name_deltas,
                "scores": name_scores,
                "shame_holder_name": shame_name,
                "shame_cleared_name": prev_shame_name if result.shame_cleared else None,
                "winner_name": winner_name,
            })

            # If winner, end game
            if room.winner:
                await asyncio.sleep(REVEAL_SECONDS)
                room.phase = GamePhase.FINISHED
                room.round_phase = None
                await broadcast(room, "game_over", {
                    "winner": room.winner,
                    "winner_name": winner_name,
                    "scores": name_scores,
                })
                return

            # Reveal pause — host-paced waits for host to advance, auto falls back after timeout
            if room.host_paced:
                room.next_round = asyncio.Event()
                try:
                    await asyncio.wait_for(room.next_round.wait(), timeout=300)
                except asyncio.TimeoutError:
                    pass
                room.next_round = None
            else:
                await asyncio.sleep(REVEAL_SECONDS)

            room.question_index += 1

        # Ran out of questions — end game, highest score wins
        if room.phase == GamePhase.PLAYING:
            room.phase = GamePhase.FINISHED
            room.round_phase = None
            id_to_name = {p.id: p.name for p in room.players}
            best_pid = max(room.scores, key=lambda pid: room.scores[pid]) if room.scores else None
            room.winner = best_pid
            name_scores = {id_to_name.get(pid, pid): score for pid, score in room.scores.items()}
            winner_name = id_to_name.get(best_pid, None) if best_pid else None
            await broadcast(room, "game_over", {
                "winner": best_pid,
                "winner_name": winner_name,
                "scores": name_scores,
            })

    except asyncio.CancelledError:
        print(f"[FQ] Room {room.code}: game loop CANCELLED")
    except Exception as e:
        print(f"[FQ] Room {room.code}: game loop CRASHED: {e}")
        import traceback
        traceback.print_exc()
        room.phase = GamePhase.FINISHED
        room.round_phase = None
