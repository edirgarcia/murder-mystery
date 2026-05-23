"""Basta game routes: start, submit answers, scores."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException

from ...shared.models import GamePhase
from ...shared.routes.ws import broadcast
from ..config import (
    DEFAULT_CATEGORIES,
    DEFAULT_LETTERS,
    MIN_PLAYERS,
    REVEAL_SECONDS,
    REVIEW_SECONDS,
    VETOES_REQUIRED,
)
from ..game_state import BastaRoom, store
from ..models import (
    PlayerScoreEntry,
    StartBastaRequest,
    SubmitAnswersRequest,
    VetoRequest,
)
from ..scoring import (
    RoundScore,
    answer_starts_with_letter,
    normalize_text,
    score_round,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ba/games", tags=["basta-game"])


def _clean_categories(categories: list[str] | None) -> list[str]:
    if not categories:
        return list(DEFAULT_CATEGORIES)
    return categories


def _choose_letter(room: BastaRoom) -> str:
    available = [letter for letter in DEFAULT_LETTERS if letter not in room.used_letters]
    if not available:
        room.used_letters = []
        available = list(DEFAULT_LETTERS)
    letter = random.choice(available)
    room.used_letters.append(letter)
    return letter


def _name_maps(room: BastaRoom) -> tuple[dict[str, str], dict[str, str]]:
    id_to_name = {p.id: p.name for p in room.players}
    name_to_id = {p.name: p.id for p in room.players}
    return id_to_name, name_to_id


def _winner_name(room: BastaRoom) -> str | None:
    if not room.scores:
        return None

    best_score = max(room.scores.values())
    winners = [
        player.name
        for player in room.players
        if room.scores.get(player.id, 0) == best_score
    ]
    if not winners:
        return None
    return " / ".join(winners)


def _review_payload(room: BastaRoom) -> dict:
    category_index = room.review_category_index or 0
    category = room.categories[category_index]
    veto_counts = _word_veto_counts(room, category)
    return {
        "round": room.current_round,
        "letter": room.current_letter,
        "category_index": category_index,
        "category_count": len(room.categories),
        "category": category,
        "review_seconds": REVIEW_SECONDS,
        "vetoes_required": VETOES_REQUIRED,
        "answers": [
            {
                "player_id": player.id,
                "player_name": player.name,
                "answer": room.current_answers.get(player.id, {}).get(category, ""),
                "veto_count": veto_counts.get(
                    normalize_text(
                        room.current_answers.get(player.id, {}).get(category, "")
                    ),
                    0,
                ),
            }
            for player in room.players
        ],
    }


def _word_veto_counts(room: BastaRoom, category: str) -> dict[str, int]:
    word_voters: dict[str, set[str]] = {}
    for target_pid, voter_ids in room.current_vetoes.get(category, {}).items():
        answer = room.current_answers.get(target_pid, {}).get(category, "")
        normalized_answer = normalize_text(answer)
        if normalized_answer:
            word_voters.setdefault(normalized_answer, set()).update(voter_ids)
    return {word: len(voters) for word, voters in word_voters.items()}


def _vetoed_answers(room: BastaRoom) -> dict[str, set[str]]:
    vetoed: dict[str, set[str]] = {}
    for category in room.current_vetoes:
        vetoed_words = {
            word
            for word, veto_count in _word_veto_counts(room, category).items()
            if veto_count >= VETOES_REQUIRED
        }
        if not vetoed_words:
            continue

        for player in room.players:
            answer = room.current_answers.get(player.id, {}).get(category, "")
            if normalize_text(answer) in vetoed_words:
                vetoed.setdefault(category, set()).add(player.id)
    return vetoed


def _flush_missing_drafts(room: BastaRoom) -> None:
    for player in room.players:
        if player.id not in room.current_answers:
            draft = room.current_drafts.get(player.id, {})
            room.current_answers[player.id] = {
                category: draft.get(category, "").strip()[:80]
                for category in room.categories
            }


def _serialize_round_result(
    room: BastaRoom,
    result: RoundScore,
) -> dict:
    id_to_name, _ = _name_maps(room)
    category_results = []

    for category_result in result.category_results:
        category_results.append(
            {
                "category": category_result.category,
                "answers": {
                    id_to_name.get(pid, pid): answer
                    for pid, answer in category_result.answers.items()
                },
                "points": {
                    id_to_name.get(pid, pid): points
                    for pid, points in category_result.points.items()
                },
                "invalid_players": [
                    id_to_name.get(pid, pid) for pid in category_result.invalid_players
                ],
                "vetoed_players": [
                    id_to_name.get(pid, pid) for pid in category_result.vetoed_players
                ],
            }
        )

    return {
        "letter": room.current_letter,
        "categories": room.categories,
        "category_results": category_results,
        "round_points": {
            id_to_name.get(pid, pid): points for pid, points in result.points.items()
        },
        "scores": {
            id_to_name.get(pid, pid): score for pid, score in room.scores.items()
        },
        "winner_name": _winner_name(room) if room.current_round >= room.rounds_to_play else None,
    }


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

    if room.game_task and not room.game_task.done():
        room.game_task.cancel()
    room.game_task = None

    room.phase = GamePhase.LOBBY
    room.scores = {}
    room.current_round = 0
    room.round_phase = None
    room.categories = list(DEFAULT_CATEGORIES)
    room.current_letter = None
    room.used_letters = []
    room.current_answers = {}
    room.current_drafts = {}
    room.current_vetoes = {}
    room.review_category_index = None
    room.round_complete = None
    room.round_timer_started = None
    room.review_advance = None
    room.next_round = None
    room.round_ends_at = None
    room.last_round_result = None
    room.winner = None

    await broadcast(room, "game_reset", {})
    return {"status": "reset"}


@router.post("/{code}/start")
async def start_game(
    code: str,
    req: StartBastaRequest | None = None,
    x_player_id: str = Header(...),
) -> dict:
    if req is None:
        req = StartBastaRequest()

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

    room.categories = _clean_categories(req.categories)
    room.rounds_to_play = req.rounds_to_play
    room.round_seconds = req.round_seconds
    room.host_paced = req.host_paced
    room.scores = {p.id: 0 for p in room.players}
    room.current_round = 0
    room.used_letters = []
    room.current_answers = {}
    room.current_drafts = {}
    room.current_vetoes = {}
    room.review_category_index = None
    room.review_advance = None
    room.last_round_result = None
    room.winner = None
    room.phase = GamePhase.PLAYING

    room.game_task = asyncio.create_task(_run_game(room))

    await broadcast(
        room,
        "game_started",
        {
            "categories": room.categories,
            "rounds_to_play": room.rounds_to_play,
            "round_seconds": room.round_seconds,
            "host_paced": room.host_paced,
        },
    )

    return {"status": "started"}


@router.post("/{code}/answers")
async def submit_answers(
    code: str,
    req: SubmitAnswersRequest,
    x_player_id: str = Header(...),
) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    if room.round_phase != "answering":
        raise HTTPException(status_code=400, detail="Not in answering phase")
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host cannot submit answers")

    player = store.get_player(room, x_player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if player.id in room.current_answers:
        raise HTTPException(status_code=400, detail="Answers already submitted")

    missing_categories = [
        category
        for category in room.categories
        if not req.answers.get(category, "").strip()
    ]
    if missing_categories and not req.auto_submit:
        raise HTTPException(
            status_code=400,
            detail="Answer every category before calling Basta",
        )

    wrong_letter_categories = [
        category
        for category in room.categories
        if not answer_starts_with_letter(
            req.answers.get(category, ""),
            room.current_letter or "",
        )
    ]
    if wrong_letter_categories and not req.auto_submit:
        raise HTTPException(
            status_code=400,
            detail=f"Every answer must start with {room.current_letter}",
        )

    if req.auto_submit and room.round_ends_at is None:
        raise HTTPException(
            status_code=400,
            detail="Auto-submit is only available after Basta is called",
        )

    room.current_answers[player.id] = {
        category: req.answers.get(category, "").strip()[:80]
        for category in room.categories
    }

    if room.round_ends_at is None and not req.auto_submit:
        round_ends_at = datetime.now(timezone.utc) + timedelta(
            seconds=room.round_seconds
        )
        room.round_ends_at = round_ends_at.isoformat()
        if room.round_timer_started:
            room.round_timer_started.set()
        await broadcast(
            room,
            "basta_called",
            {
                "player_id": player.id,
                "player_name": player.name,
                "round_ends_at": room.round_ends_at,
                "round_seconds": room.round_seconds,
            },
        )

    await broadcast(
        room,
        "answers_submitted",
        {
            "player_id": player.id,
            "player_name": player.name,
            "submissions_in": len(room.current_answers),
            "total_players": len(room.players),
        },
    )

    if len(room.current_answers) >= len(room.players) and room.round_complete:
        room.round_complete.set()

    return {"status": "submitted"}


@router.post("/{code}/draft")
async def save_draft(
    code: str,
    req: SubmitAnswersRequest,
    x_player_id: str = Header(...),
) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    if room.round_phase != "answering":
        raise HTTPException(status_code=400, detail="Not in answering phase")
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host cannot save answers")

    player = store.get_player(room, x_player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if player.id in room.current_answers:
        return {"status": "ignored"}

    room.current_drafts[player.id] = {
        category: req.answers.get(category, "").strip()[:80]
        for category in room.categories
    }
    return {"status": "saved"}


@router.post("/{code}/veto")
async def veto_answer(
    code: str,
    req: VetoRequest,
    x_player_id: str = Header(...),
) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    if room.round_phase != "review":
        raise HTTPException(status_code=400, detail="Not in review phase")
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host cannot veto answers")

    voter = store.get_player(room, x_player_id)
    if not voter:
        raise HTTPException(status_code=404, detail="Player not found")
    target = store.get_player(room, req.target_player_id)
    if not target:
        raise HTTPException(status_code=400, detail="Invalid answer target")
    if target.id == voter.id:
        raise HTTPException(status_code=400, detail="You cannot veto your own answer")

    if room.review_category_index is None:
        raise HTTPException(status_code=400, detail="No category is being reviewed")
    category = room.categories[room.review_category_index]
    if req.category != category:
        raise HTTPException(status_code=400, detail="That category is not being reviewed")

    answer = room.current_answers.get(target.id, {}).get(category, "").strip()
    if not answer:
        raise HTTPException(status_code=400, detail="There is no answer to veto")

    category_vetoes = room.current_vetoes.setdefault(category, {})
    voter_ids = category_vetoes.setdefault(target.id, set())
    voter_ids.add(voter.id)
    normalized_answer = normalize_text(answer)
    veto_count = _word_veto_counts(room, category).get(normalized_answer, 0)
    affected_player_ids = [
        player.id
        for player in room.players
        if normalize_text(room.current_answers.get(player.id, {}).get(category, ""))
        == normalized_answer
    ]

    await broadcast(
        room,
        "veto_update",
        {
            "category": category,
            "target_player_id": target.id,
            "target_player_name": target.name,
            "affected_player_ids": affected_player_ids,
            "veto_count": veto_count,
        },
    )

    return {"status": "vetoed", "veto_count": veto_count}


@router.post("/{code}/next")
async def next_round(
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
    if room.round_phase == "review" and room.review_advance:
        room.review_advance.set()
        return {"status": "ok"}
    if room.next_round:
        room.next_round.set()
    return {"status": "ok"}


@router.get("/{code}/scores")
async def get_scores(code: str) -> list[PlayerScoreEntry]:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")

    entries = [
        PlayerScoreEntry(
            player_id=p.id,
            player_name=p.name,
            score=room.scores.get(p.id, 0),
        )
        for p in room.players
    ]
    entries.sort(key=lambda entry: entry.score, reverse=True)
    return entries


async def _run_game(room: BastaRoom) -> None:
    """Main game loop: letter/category answers -> score -> reveal -> repeat."""
    try:
        while room.phase == GamePhase.PLAYING and room.current_round < room.rounds_to_play:
            room.current_round += 1
            room.current_letter = _choose_letter(room)
            room.current_answers = {}
            room.current_drafts = {}
            room.current_vetoes = {}
            room.review_category_index = None
            room.review_advance = None
            room.last_round_result = None
            room.round_phase = "answering"
            room.round_complete = asyncio.Event()
            room.round_timer_started = asyncio.Event()
            room.round_ends_at = None

            await broadcast(
                room,
                "new_round",
                {
                    "round": room.current_round,
                    "rounds_to_play": room.rounds_to_play,
                    "letter": room.current_letter,
                    "categories": room.categories,
                    "round_ends_at": None,
                    "players": [{"id": p.id, "name": p.name} for p in room.players],
                    "scores": {
                        p.name: room.scores.get(p.id, 0) for p in room.players
                    },
                },
            )

            await room.round_timer_started.wait()

            if room.round_complete and not room.round_complete.is_set():
                try:
                    if room.round_ends_at:
                        round_ends_at = datetime.fromisoformat(room.round_ends_at)
                        remaining = (
                            round_ends_at - datetime.now(timezone.utc)
                        ).total_seconds()
                        if remaining > 0:
                            await asyncio.wait_for(
                                room.round_complete.wait(),
                                timeout=remaining,
                            )
                except asyncio.TimeoutError:
                    pass

            _flush_missing_drafts(room)

            room.round_phase = "reveal"
            room.round_ends_at = None
            room.round_complete = None
            room.round_timer_started = None

            room.round_phase = "review"
            for category_index in range(len(room.categories)):
                room.review_category_index = category_index
                room.review_advance = asyncio.Event() if room.host_paced else None
                await broadcast(room, "review_category", _review_payload(room))
                if room.host_paced and room.review_advance:
                    try:
                        await asyncio.wait_for(room.review_advance.wait(), timeout=300)
                    except asyncio.TimeoutError:
                        pass
                else:
                    await asyncio.sleep(REVIEW_SECONDS)
            room.review_category_index = None
            room.review_advance = None

            room.round_phase = "reveal"

            player_ids = [p.id for p in room.players]
            result = score_round(
                room.current_answers,
                player_ids,
                room.categories,
                room.current_letter or "",
                _vetoed_answers(room),
            )

            for pid, delta in result.points.items():
                room.scores[pid] = room.scores.get(pid, 0) + delta

            if room.current_round >= room.rounds_to_play:
                best_score = max(room.scores.values()) if room.scores else 0
                for player in room.players:
                    if room.scores.get(player.id, 0) == best_score:
                        room.winner = player.id
                        break

            room.last_round_result = _serialize_round_result(room, result)

            await broadcast(room, "round_result", room.last_round_result)

            if room.current_round >= room.rounds_to_play:
                await asyncio.sleep(REVEAL_SECONDS)
                room.phase = GamePhase.FINISHED
                room.round_phase = None
                await broadcast(
                    room,
                    "game_over",
                    {
                        "winner": room.winner,
                        "winner_name": _winner_name(room),
                        "scores": room.last_round_result["scores"],
                    },
                )
                return

            if room.host_paced:
                room.next_round = asyncio.Event()
                try:
                    await asyncio.wait_for(room.next_round.wait(), timeout=300)
                except asyncio.TimeoutError:
                    pass
                room.next_round = None
            else:
                await asyncio.sleep(REVEAL_SECONDS)

    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Basta game loop crashed for room %s", room.code)
        room.phase = GamePhase.FINISHED
        room.round_phase = None
