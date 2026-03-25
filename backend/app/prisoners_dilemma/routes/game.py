"""Prisoner's Dilemma game routes and loop."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException

from ..config import (
    ACCUSATION_SECONDS,
    MAX_PLAYERS,
    MIN_PLAYERS,
    REVEAL_SECONDS,
    TOTAL_ROUNDS,
    VOTE_SECONDS,
)
from ..game_logic import (
    assign_teams_and_spies,
    majority_choice,
    player_ids_for_team,
    resolve_team_accusation,
    score_choices,
    winner_for_scores,
)
from ..game_state import PDRoom, store
from ..models import (
    AccusationRequest,
    Decision,
    PDPrivateState,
    StartPDRequest,
    TeamColor,
    VoteRequest,
)
from ...shared.models import GamePhase
from ...shared.routes.ws import broadcast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pd/games", tags=["pd-game"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _set_vote_end(room: PDRoom) -> None:
    room.voting_ends_at = (_utc_now() + timedelta(seconds=room.voting_seconds)).isoformat()


def _set_accusation_end(room: PDRoom) -> None:
    room.accusation_ends_at = (_utc_now() + timedelta(seconds=room.accusation_seconds)).isoformat()


async def _send_to_player(room: PDRoom, player_id: str, event: str, data: dict) -> None:
    ws = room.connections.get(player_id)
    if not ws:
        return
    try:
        await ws.send_text(json.dumps({"event": event, "data": data}))
    except Exception:
        room.connections.pop(player_id, None)


def _team_public_players(room: PDRoom) -> list[dict]:
    public_players = []
    for player in room.players:
        game_player = room.game_players.get(player.id)
        public_players.append(
            {
                "id": player.id,
                "name": player.name,
                "team": game_player.team.value if game_player else None,
                "spy_exposed": game_player.spy_exposed if game_player else False,
            }
        )
    return public_players


def _player_private_state(room: PDRoom, player_id: str) -> PDPrivateState:
    game_player = room.game_players.get(player_id)
    if not game_player:
        raise HTTPException(status_code=404, detail="Player not found")
    return PDPrivateState(
        player_id=game_player.id,
        player_name=game_player.name,
        team=game_player.team,
        is_spy=game_player.is_spy,
        spy_active=game_player.spy_active,
        sabotage_charges=game_player.sabotage_charges,
    )


def _active_spy_id(room: PDRoom, team: TeamColor) -> str | None:
    for player in room.game_players.values():
        if player.team == team and player.is_spy and player.spy_active:
            return player.id
    return None


def _resolve_round(room: PDRoom) -> dict:
    round_number = room.current_round
    multiplier = 2 if round_number >= TOTAL_ROUNDS - 1 else 1
    result: dict[str, dict] = {"round": round_number, "multiplier": multiplier, "teams": {}}

    final_choices: dict[TeamColor, Decision] = {}
    for team in (TeamColor.RED, TeamColor.BLUE):
        team_player_ids = player_ids_for_team(room.game_players, team)
        team_votes = [
            Decision(room.current_votes[pid])
            for pid in team_player_ids
            if pid in room.current_votes
        ]
        majority, counts = majority_choice(team_votes)
        tampered = False
        sabotage_player_id = next(
            (
                pid
                for pid in team_player_ids
                if room.sabotage_requests.get(pid)
                and room.game_players[pid].is_spy
                and room.game_players[pid].spy_active
                and room.game_players[pid].sabotage_charges > 0
            ),
            None,
        )

        final_choice = majority
        if sabotage_player_id:
            final_choice = Decision.BETRAY if majority == Decision.TRUST else Decision.TRUST
            room.game_players[sabotage_player_id].sabotage_charges -= 1
            tampered = True

        final_choices[team] = final_choice
        result["teams"][team.value] = {
            "team": team.value,
            "majority_choice": majority.value,
            "final_choice": final_choice.value,
            "tampered": tampered,
            "trust_votes": counts[Decision.TRUST],
            "betray_votes": counts[Decision.BETRAY],
            "submitted_votes": len(team_votes),
            "team_size": len(team_player_ids),
        }

    deltas = score_choices(final_choices[TeamColor.RED], final_choices[TeamColor.BLUE], multiplier)
    for team, delta in deltas.items():
        room.team_scores[team] += delta
        result["teams"][team.value]["score_delta"] = delta
        result["teams"][team.value]["total_score"] = room.team_scores[team]

    result["team_scores"] = {
        team.value: score for team, score in room.team_scores.items()
    }
    return result


def _resolve_accusations(room: PDRoom) -> dict:
    result = {"round": room.current_round, "teams": {}, "team_scores": {}}

    for team in (TeamColor.RED, TeamColor.BLUE):
        team_player_ids = player_ids_for_team(room.game_players, team)
        team_accusations = {
            pid: target_id
            for pid, target_id in room.current_accusations.items()
            if pid in team_player_ids
        }
        active_spy_id = _active_spy_id(room, team)
        team_result = resolve_team_accusation(team_player_ids, team_accusations, active_spy_id)

        accused_player_name = None
        accused_player_id = team_result["accused_player_id"]
        if accused_player_id and accused_player_id in room.game_players:
            accused_player = room.game_players[accused_player_id]
            accused_player_name = accused_player.name
            if team_result["spy_neutralized"]:
                accused_player.spy_active = False
                accused_player.spy_exposed = True

        room.team_scores[team] += team_result["score_delta"]
        team_result["accused_player_name"] = accused_player_name
        team_result["total_score"] = room.team_scores[team]
        result["teams"][team.value] = team_result

    result["team_scores"] = {
        team.value: score for team, score in room.team_scores.items()
    }
    result["players"] = _team_public_players(room)
    return result


@router.post("/{code}/start")
async def start_game(
    code: str,
    req: StartPDRequest | None = None,
    x_player_id: str = Header(...),
) -> dict:
    if req is None:
        req = StartPDRequest(
            voting_seconds=VOTE_SECONDS,
            accusation_seconds=ACCUSATION_SECONDS,
        )

    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Only the host can start the game")
    if room.phase != GamePhase.LOBBY:
        raise HTTPException(status_code=400, detail="Game already started")
    if len(room.players) < MIN_PLAYERS:
        raise HTTPException(status_code=400, detail=f"Need at least {MIN_PLAYERS} players")

    room.game_players = assign_teams_and_spies(room.players)
    room.team_scores = {
        TeamColor.RED: 0,
        TeamColor.BLUE: 0,
    }
    room.current_round = 0
    room.total_rounds = TOTAL_ROUNDS
    room.round_phase = None
    room.current_votes = {}
    room.sabotage_requests = {}
    room.current_accusations = {}
    room.voting_ends_at = None
    room.accusation_ends_at = None
    room.winner = None
    room.voting_seconds = req.voting_seconds
    room.accusation_seconds = req.accusation_seconds
    room.phase = GamePhase.PLAYING

    for player in room.players:
        private_state = _player_private_state(room, player.id)
        await _send_to_player(room, player.id, "role_assigned", private_state.model_dump(mode="json"))

    await broadcast(room, "game_started", {
        "message": "Prisoner's Dilemma game started",
        "players": _team_public_players(room),
        "team_scores": {
            TeamColor.RED.value: 0,
            TeamColor.BLUE.value: 0,
        },
        "total_rounds": room.total_rounds,
        "voting_seconds": room.voting_seconds,
        "accusation_seconds": room.accusation_seconds,
        "max_players": MAX_PLAYERS,
    })

    room.game_task = asyncio.create_task(_run_intro(room))
    return {"status": "started"}


@router.get("/{code}/me", response_model=PDPrivateState)
async def get_private_state(code: str, x_player_id: str = Header(...)) -> PDPrivateState:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host does not have a private player state")
    if room.phase == GamePhase.LOBBY:
        raise HTTPException(status_code=400, detail="Game has not started yet")
    return _player_private_state(room, x_player_id)


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
    if x_player_id in room.current_votes:
        raise HTTPException(status_code=400, detail="Already voted")

    player = room.game_players.get(x_player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    if req.sabotage:
        if not player.is_spy or not player.spy_active:
            raise HTTPException(status_code=403, detail="Only the active spy can sabotage")
        if player.sabotage_charges <= 0:
            raise HTTPException(status_code=400, detail="No sabotage charges remaining")

    room.current_votes[x_player_id] = req.choice.value
    room.sabotage_requests[x_player_id] = req.sabotage

    await broadcast(room, "vote_cast", {
        "votes_in": len(room.current_votes),
        "total_players": len(room.players),
    })

    if len(room.current_votes) >= len(room.players) and room.vote_complete:
        room.vote_complete.set()

    return {"status": "voted"}


@router.post("/{code}/accuse")
async def submit_accusation(
    code: str,
    req: AccusationRequest,
    x_player_id: str = Header(...),
) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    if room.round_phase != "accusation":
        raise HTTPException(status_code=400, detail="Not in accusation phase")
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host cannot accuse")
    if x_player_id in room.current_accusations:
        raise HTTPException(status_code=400, detail="Already submitted accusation")

    player = room.game_players.get(x_player_id)
    if not player or player.team is None:
        raise HTTPException(status_code=404, detail="Player not found")

    target_id = req.target_id
    if req.accuse:
        if target_id == x_player_id:
            raise HTTPException(status_code=400, detail="Cannot accuse yourself")
        target = room.game_players.get(target_id or "")
        if not target or target.team != player.team:
            raise HTTPException(status_code=400, detail="Can only accuse a teammate")

    room.current_accusations[x_player_id] = target_id if req.accuse else None

    await broadcast(room, "accusation_cast", {
        "accusations_in": len(room.current_accusations),
        "total_players": len(room.players),
    })

    if len(room.current_accusations) >= len(room.players) and room.accusation_complete:
        room.accusation_complete.set()

    return {"status": "submitted"}


async def _pd_narrate(room: PDRoom, text: str, sound: str) -> None:
    """Broadcast a narration line and wait for dashboard audio to finish."""
    room.narration_ack = asyncio.Event()
    await broadcast(room, "intro_narration", {"text": text, "sound": sound})
    if room.connections:
        try:
            await asyncio.wait_for(room.narration_ack.wait(), timeout=15)
        except asyncio.TimeoutError:
            pass
    room.narration_ack = None


async def _run_intro(room: PDRoom) -> None:
    """Play intro narration, then hand off to the game loop."""
    try:
        # Give clients time to navigate and establish WS connections
        await asyncio.sleep(2)
        for _ in range(20):
            if room.connections:
                break
            await asyncio.sleep(0.25)

        narration = [
            ("Welcome to Double Trust.", "pd-welcome.mp3"),
            ("You'll be split into two teams: Red and Blue.", "pd-teams.mp3"),
            ("Each round, your team must decide: Trust or Betray.", "pd-decide.mp3"),
            ("If both teams trust, everyone gains points.", "pd-both-trust.mp3"),
            ("If both betray, everyone loses.", "pd-both-betray.mp3"),
            ("But if one team betrays while the other trusts, the betrayers win big.", "pd-one-betrays.mp3"),
            ("Here's the twist: there's a hidden spy on each team.", "pd-spy.mp3"),
            ("Spies can sabotage their own team's vote, flipping the outcome.", "pd-sabotage.mp3"),
            ("After each round, you can accuse a teammate of being the spy.", "pd-accuse.mp3"),
            ("Check your phone now to see your role.", "pd-check-role.mp3"),
            ("The game begins!", "pd-begin.mp3"),
        ]
        for text, sound in narration:
            await _pd_narrate(room, text, sound)

        await broadcast(room, "intro_done", {})
        await _run_game(room)
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("PD intro crashed for room %s", room.code)


async def _run_game(room: PDRoom) -> None:
    try:
        for round_number in range(1, room.total_rounds + 1):
            if room.phase != GamePhase.PLAYING:
                break

            room.current_round = round_number
            room.round_phase = "voting"
            room.current_votes = {}
            room.sabotage_requests = {}
            room.vote_complete = asyncio.Event()
            _set_vote_end(room)

            await broadcast(room, "round_started", {
                "round": room.current_round,
                "total_rounds": room.total_rounds,
                "round_phase": room.round_phase,
                "voting_ends_at": room.voting_ends_at,
                "team_scores": {
                    team.value: score for team, score in room.team_scores.items()
                },
                "players": _team_public_players(room),
            })

            try:
                remaining = (datetime.fromisoformat(room.voting_ends_at) - _utc_now()).total_seconds()
                if remaining > 0:
                    await asyncio.wait_for(room.vote_complete.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                pass

            room.vote_complete = None
            room.voting_ends_at = None
            room.round_phase = "reveal"
            round_result = _resolve_round(room)
            round_result["reveal_ends_at"] = (
                _utc_now() + timedelta(seconds=REVEAL_SECONDS)
            ).isoformat()
            await broadcast(room, "round_result", round_result)

            room.round_phase = "accusation"
            room.current_accusations = {}
            room.accusation_complete = asyncio.Event()
            _set_accusation_end(room)

            await broadcast(room, "accusation_started", {
                "round": room.current_round,
                "accusation_ends_at": room.accusation_ends_at,
                "players": _team_public_players(room),
            })

            try:
                remaining = (datetime.fromisoformat(room.accusation_ends_at) - _utc_now()).total_seconds()
                if remaining > 0:
                    await asyncio.wait_for(room.accusation_complete.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                pass

            room.accusation_complete = None
            room.accusation_ends_at = None
            room.round_phase = "reveal"
            accusation_result = _resolve_accusations(room)
            accusation_result["reveal_ends_at"] = (
                _utc_now() + timedelta(seconds=REVEAL_SECONDS)
            ).isoformat()
            await broadcast(room, "accusation_result", accusation_result)

            for player in room.players:
                await _send_to_player(
                    room,
                    player.id,
                    "private_state",
                    _player_private_state(room, player.id).model_dump(mode="json"),
                )

            await asyncio.sleep(REVEAL_SECONDS)

        room.phase = GamePhase.FINISHED
        room.round_phase = None
        room.winner = winner_for_scores(room.team_scores)
        await broadcast(room, "game_over", {
            "winner": room.winner,
            "team_scores": {
                team.value: score for team, score in room.team_scores.items()
            },
            "players": _team_public_players(room),
            "spies": {
                team.value: {
                    "player_id": spy.id,
                    "player_name": spy.name,
                    "exposed": spy.spy_exposed,
                }
                for team in (TeamColor.RED, TeamColor.BLUE)
                for spy in room.game_players.values()
                if spy.team == team and spy.is_spy
            },
        })
    finally:
        room.game_task = None
