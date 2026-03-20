"""Werewolf game routes and game loop."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException

from ..config import (
    ANNOUNCEMENT_SECONDS,
    CUPID_SECONDS,
    DAY_VOTE_SECONDS,
    DISCUSSION_SECONDS,
    HUNTER_SECONDS,
    MIN_PLAYERS,
    SEER_SECONDS,
    WITCH_SECONDS,
    WEREWOLF_VOTE_SECONDS,
)
from ..game_logic import (
    check_win_condition,
    resolve_day_vote,
    resolve_night,
    resolve_werewolf_vote,
)
from ..game_state import WWPlayer, WerewolfRoom, store
from ..models import (
    DaySubPhase,
    DayVoteRequest,
    NightActionRequest,
    NightSubPhase,
    Role,
    StartWWRequest,
)
from ..roles import assign_roles
from ...shared.models import GamePhase
from ...shared.routes.ws import broadcast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ww/games", tags=["ww-game"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _set_phase_end(room: WerewolfRoom, seconds: int) -> None:
    room.phase_ends_at = (_utc_now() + timedelta(seconds=seconds)).isoformat()


async def _send_to_player(room: WerewolfRoom, player_id: str, event: str, data: dict) -> None:
    ws = room.connections.get(player_id)
    if not ws:
        return
    try:
        await ws.send_text(json.dumps({"event": event, "data": data}))
    except Exception:
        room.connections.pop(player_id, None)


def _alive_ids(room: WerewolfRoom) -> list[str]:
    return [pid for pid, p in room.game_players.items() if p.alive]


def _alive_non_host_players(room: WerewolfRoom) -> list[WWPlayer]:
    return [p for p in room.game_players.values() if p.alive]


def _alive_werewolves(room: WerewolfRoom) -> list[WWPlayer]:
    return [
        p
        for p in room.game_players.values()
        if p.alive and p.role == Role.WEREWOLF
    ]


def _public_players(room: WerewolfRoom) -> list[dict]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "alive": p.alive,
        }
        for p in room.game_players.values()
    ]


def _apply_deaths(
    room: WerewolfRoom,
    initial_deaths: list[str],
    initial_causes: dict[str, str],
) -> tuple[list[str], dict[str, str]]:
    """Mark deaths as dead and apply lover-chain deaths."""
    deaths: list[str] = []
    causes: dict[str, str] = {}
    queue = list(initial_deaths)

    while queue:
        pid = queue.pop(0)
        gp = room.game_players.get(pid)
        if not gp or not gp.alive:
            continue

        gp.alive = False
        deaths.append(pid)
        causes[pid] = initial_causes.get(pid, causes.get(pid, "unknown"))

        if gp.role == Role.HUNTER:
            room.hunter_pending = True
            room.hunter_shot_target = None

        # Lover chain
        if room.lovers and pid in room.lovers:
            lover_id = room.lovers[0] if room.lovers[1] == pid else room.lovers[1]
            lover = room.game_players.get(lover_id)
            if lover and lover.alive and lover_id not in queue:
                queue.append(lover_id)
                initial_causes.setdefault(lover_id, "lover")

    return deaths, causes


async def _check_and_finish(room: WerewolfRoom) -> bool:
    winner = check_win_condition(room.game_players, room.lovers)
    if not winner:
        return False

    room.winner = winner
    room.phase = GamePhase.FINISHED
    room.night_sub_phase = None
    room.day_sub_phase = None
    room.phase_ends_at = None
    room.game_task = None

    roles = {
        pid: gp.role.value
        for pid, gp in room.game_players.items()
    }

    await broadcast(room, "game_over", {
        "winner": winner.value,
        "roles": roles,
        "players": _public_players(room),
    })
    return True


async def _run_hunter_revenge(room: WerewolfRoom) -> None:
    if not room.hunter_pending:
        return

    hunter = next(
        (p for p in room.game_players.values() if p.role == Role.HUNTER),
        None,
    )
    if not hunter:
        room.hunter_pending = False
        return

    room.day_sub_phase = DaySubPhase.HUNTER_REVENGE
    room.hunter_action_complete = asyncio.Event()
    _set_phase_end(room, HUNTER_SECONDS)

    await broadcast(room, "phase_changed", {
        "phase": room.phase.value,
        "day_sub_phase": room.day_sub_phase.value,
        "phase_ends_at": room.phase_ends_at,
        "hunter_id": hunter.id,
    })

    alive_targets = [
        {"id": p.id, "name": p.name}
        for p in room.game_players.values()
        if p.alive
    ]
    await _send_to_player(room, hunter.id, "hunter_prompt", {"targets": alive_targets})

    try:
        await asyncio.wait_for(room.hunter_action_complete.wait(), timeout=HUNTER_SECONDS)
    except asyncio.TimeoutError:
        pass

    if room.hunter_shot_target:
        deaths, causes = _apply_deaths(
            room,
            [room.hunter_shot_target],
            {room.hunter_shot_target: "hunter"},
        )
        room.last_deaths = deaths
        room.last_death_causes = causes
        await broadcast(room, "death_announcement", {
            "deaths": deaths,
            "causes": causes,
            "players": _public_players(room),
        })

    room.hunter_pending = False
    room.hunter_shot_target = None
    room.hunter_action_complete = None


@router.post("/{code}/start")
async def start_game(
    code: str,
    req: StartWWRequest | None = None,
    x_player_id: str = Header(...),
) -> dict:
    if req is None:
        req = StartWWRequest(discussion_seconds=DISCUSSION_SECONDS)

    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if not store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Only the host can start the game")
    if room.phase != GamePhase.LOBBY:
        raise HTTPException(status_code=400, detail="Game already started")
    if len(room.players) < MIN_PLAYERS:
        raise HTTPException(status_code=400, detail=f"Need at least {MIN_PLAYERS} players")

    role_map = assign_roles([p.id for p in room.players])
    room.game_players = {
        p.id: WWPlayer(
            id=p.id,
            name=p.name,
            role=role_map[p.id],
            alive=True,
        )
        for p in room.players
    }
    room.night_number = 0
    room.day_number = 0
    room.night_sub_phase = None
    room.day_sub_phase = None
    room.werewolf_votes = {}
    room.werewolf_victim = None
    room.seer_target = None
    room.witch_heal_used = False
    room.witch_kill_used = False
    room.witch_healed_this_night = False
    room.witch_killed_target = None
    room.day_votes = {}
    room.lovers = None
    room.hunter_pending = False
    room.hunter_shot_target = None
    room.winner = None
    room.last_deaths = []
    room.last_death_causes = {}
    room.discussion_seconds = req.discussion_seconds
    room.phase = GamePhase.PLAYING

    # Private role reveals
    wolves = [
        {"id": p.id, "name": p.name}
        for p in room.game_players.values()
        if p.role == Role.WEREWOLF
    ]
    for pid, gp in room.game_players.items():
        payload = {
            "role": gp.role.value,
            "alive": gp.alive,
        }
        if gp.role == Role.WEREWOLF:
            payload["werewolves"] = wolves
        await _send_to_player(room, pid, "role_assigned", payload)

    await broadcast(room, "game_started", {
        "message": "Werewolf game started",
        "discussion_seconds": room.discussion_seconds,
        "players": _public_players(room),
    })

    room.game_task = asyncio.create_task(_run_game(room))
    return {"status": "started"}


@router.post("/{code}/night-action")
async def submit_night_action(
    code: str,
    req: NightActionRequest,
    x_player_id: str = Header(...),
) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host cannot submit actions")

    gp = room.game_players.get(x_player_id)
    if not gp:
        raise HTTPException(status_code=404, detail="Player not found")

    # Hunter can act while dead during revenge phase.
    is_hunter_revenge = room.day_sub_phase == DaySubPhase.HUNTER_REVENGE
    if not gp.alive and not (is_hunter_revenge and gp.role == Role.HUNTER):
        raise HTTPException(status_code=400, detail="Dead players cannot act")

    if room.night_sub_phase == NightSubPhase.CUPID:
        if gp.role != Role.CUPID:
            raise HTTPException(status_code=403, detail="Only cupid can act now")
        if req.action != "cupid_link":
            raise HTTPException(status_code=400, detail="Invalid cupid action")
        if not req.target or not req.target2 or req.target == req.target2:
            raise HTTPException(status_code=400, detail="Cupid must pick two different players")
        if req.target not in room.game_players or req.target2 not in room.game_players:
            raise HTTPException(status_code=400, detail="Invalid lover target")

        room.lovers = (req.target, req.target2)
        room.game_players[req.target].lover_id = req.target2
        room.game_players[req.target2].lover_id = req.target
        if room.night_action_complete:
            room.night_action_complete.set()
        return {"status": "accepted"}

    if room.night_sub_phase == NightSubPhase.WEREWOLVES:
        if gp.role != Role.WEREWOLF:
            raise HTTPException(status_code=403, detail="Only werewolves can act now")
        if req.action != "werewolf_vote":
            raise HTTPException(status_code=400, detail="Invalid werewolf action")
        if not req.target:
            raise HTTPException(status_code=400, detail="Missing target")
        target = room.game_players.get(req.target)
        if not target or not target.alive:
            raise HTTPException(status_code=400, detail="Target is not alive")

        room.werewolf_votes[x_player_id] = req.target
        alive_wolves = _alive_werewolves(room)
        if len(room.werewolf_votes) >= len(alive_wolves) and room.night_action_complete:
            room.night_action_complete.set()
        return {"status": "accepted"}

    if room.night_sub_phase == NightSubPhase.SEER:
        if gp.role != Role.SEER:
            raise HTTPException(status_code=403, detail="Only seer can act now")
        if req.action != "seer_investigate":
            raise HTTPException(status_code=400, detail="Invalid seer action")
        if not req.target:
            raise HTTPException(status_code=400, detail="Missing target")
        target = room.game_players.get(req.target)
        if not target or not target.alive:
            raise HTTPException(status_code=400, detail="Target is not alive")

        room.seer_target = req.target
        await _send_to_player(room, gp.id, "seer_result", {
            "target": target.id,
            "target_name": target.name,
            "is_werewolf": target.role == Role.WEREWOLF,
        })
        if room.night_action_complete:
            room.night_action_complete.set()
        return {"status": "accepted"}

    if room.night_sub_phase == NightSubPhase.WITCH:
        if gp.role != Role.WITCH:
            raise HTTPException(status_code=403, detail="Only witch can act now")

        if req.action == "witch_pass":
            if room.night_action_complete:
                room.night_action_complete.set()
            return {"status": "accepted"}

        if req.action == "witch_heal":
            if room.witch_heal_used:
                raise HTTPException(status_code=400, detail="Heal potion already used")
            if not room.werewolf_victim:
                raise HTTPException(status_code=400, detail="No werewolf victim to heal")
            room.witch_healed_this_night = True
            room.witch_heal_used = True
            if room.night_action_complete:
                room.night_action_complete.set()
            return {"status": "accepted"}

        if req.action == "witch_kill":
            if room.witch_kill_used:
                raise HTTPException(status_code=400, detail="Kill potion already used")
            if not req.target:
                raise HTTPException(status_code=400, detail="Missing target")
            target = room.game_players.get(req.target)
            if not target or not target.alive:
                raise HTTPException(status_code=400, detail="Target is not alive")
            room.witch_killed_target = req.target
            room.witch_kill_used = True
            if room.night_action_complete:
                room.night_action_complete.set()
            return {"status": "accepted"}

        raise HTTPException(status_code=400, detail="Invalid witch action")

    if is_hunter_revenge:
        if gp.role != Role.HUNTER:
            raise HTTPException(status_code=403, detail="Only hunter can act now")
        if req.action != "hunter_shoot":
            raise HTTPException(status_code=400, detail="Invalid hunter action")
        if not req.target:
            raise HTTPException(status_code=400, detail="Missing target")
        target = room.game_players.get(req.target)
        if not target or not target.alive:
            raise HTTPException(status_code=400, detail="Target is not alive")
        room.hunter_shot_target = target.id
        if room.hunter_action_complete:
            room.hunter_action_complete.set()
        return {"status": "accepted"}

    raise HTTPException(status_code=400, detail="Not accepting night actions right now")


@router.post("/{code}/vote")
async def submit_vote(
    code: str,
    req: DayVoteRequest,
    x_player_id: str = Header(...),
) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")
    if room.phase != GamePhase.PLAYING:
        raise HTTPException(status_code=400, detail="Game not in progress")
    if room.day_sub_phase != DaySubPhase.VOTING:
        raise HTTPException(status_code=400, detail="Not in voting phase")
    if store.is_host(room, x_player_id):
        raise HTTPException(status_code=403, detail="Host cannot vote")

    gp = room.game_players.get(x_player_id)
    if not gp:
        raise HTTPException(status_code=404, detail="Player not found")
    if not gp.alive:
        raise HTTPException(status_code=400, detail="Dead players cannot vote")
    if x_player_id in room.day_votes:
        raise HTTPException(status_code=400, detail="Already voted")

    target = req.target
    if not target:
        raise HTTPException(status_code=400, detail="Missing vote target")
    if target != "skip":
        tgt = room.game_players.get(target)
        if not tgt or not tgt.alive:
            raise HTTPException(status_code=400, detail="Invalid vote target")

    room.day_votes[x_player_id] = target
    await broadcast(room, "vote_cast", {
        "votes_in": len(room.day_votes),
        "total_alive": len(_alive_ids(room)),
    })

    if len(room.day_votes) >= len(_alive_ids(room)) and room.day_vote_complete:
        room.day_vote_complete.set()

    return {"status": "accepted"}


@router.get("/{code}/state")
async def get_player_state(code: str, x_player_id: str = Header(...)) -> dict:
    room = store.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Game not found")

    is_host = store.is_host(room, x_player_id)
    gp = None if is_host else room.game_players.get(x_player_id)
    if not is_host and not gp:
        raise HTTPException(status_code=404, detail="Player not found")

    state = {
        "code": room.code,
        "phase": room.phase.value,
        "night_number": room.night_number,
        "day_number": room.day_number,
        "night_sub_phase": room.night_sub_phase.value if room.night_sub_phase else None,
        "day_sub_phase": room.day_sub_phase.value if room.day_sub_phase else None,
        "phase_ends_at": room.phase_ends_at,
        "players": _public_players(room),
        "last_deaths": room.last_deaths,
        "winner": room.winner.value if room.winner else None,
    }

    if gp:
        state["me"] = {
            "id": gp.id,
            "name": gp.name,
            "role": gp.role.value,
            "alive": gp.alive,
            "lover_id": gp.lover_id,
        }

    if room.phase == GamePhase.FINISHED:
        state["roles"] = {pid: p.role.value for pid, p in room.game_players.items()}

    return state


async def _run_game(room: WerewolfRoom) -> None:
    try:
        # Night 0: Cupid
        room.night_sub_phase = NightSubPhase.CUPID
        room.day_sub_phase = None
        room.night_action_complete = asyncio.Event()
        _set_phase_end(room, CUPID_SECONDS)
        await broadcast(room, "phase_changed", {
            "phase": room.phase.value,
            "night_number": room.night_number,
            "night_sub_phase": room.night_sub_phase.value,
            "phase_ends_at": room.phase_ends_at,
        })
        cupid = next(
            (p for p in room.game_players.values() if p.alive and p.role == Role.CUPID),
            None,
        )
        if cupid:
            await _send_to_player(room, cupid.id, "cupid_prompt", {
                "players": [
                    {"id": p.id, "name": p.name}
                    for p in room.game_players.values()
                    if p.alive
                ],
            })
            try:
                await asyncio.wait_for(room.night_action_complete.wait(), timeout=CUPID_SECONDS)
            except asyncio.TimeoutError:
                alive = _alive_non_host_players(room)
                if len(alive) >= 2:
                    room.lovers = (alive[0].id, alive[1].id)
                    room.game_players[alive[0].id].lover_id = alive[1].id
                    room.game_players[alive[1].id].lover_id = alive[0].id

        if room.lovers:
            await broadcast(room, "lovers_linked", {"linked": True})

        while room.phase == GamePhase.PLAYING:
            room.night_number += 1
            room.last_deaths = []
            room.last_death_causes = {}

            # Werewolves
            room.night_sub_phase = NightSubPhase.WEREWOLVES
            room.werewolf_votes = {}
            room.night_action_complete = asyncio.Event()
            _set_phase_end(room, WEREWOLF_VOTE_SECONDS)
            await broadcast(room, "phase_changed", {
                "phase": room.phase.value,
                "night_number": room.night_number,
                "night_sub_phase": room.night_sub_phase.value,
                "phase_ends_at": room.phase_ends_at,
            })
            alive_wolves = _alive_werewolves(room)
            for w in alive_wolves:
                await _send_to_player(room, w.id, "werewolf_prompt", {
                    "targets": [
                        {"id": p.id, "name": p.name}
                        for p in room.game_players.values()
                        if p.alive and p.id != w.id
                    ],
                })
            try:
                await asyncio.wait_for(
                    room.night_action_complete.wait(),
                    timeout=WEREWOLF_VOTE_SECONDS,
                )
            except asyncio.TimeoutError:
                pass
            room.werewolf_victim = resolve_werewolf_vote(room.werewolf_votes)

            # Seer
            room.night_sub_phase = NightSubPhase.SEER
            room.seer_target = None
            room.night_action_complete = asyncio.Event()
            _set_phase_end(room, SEER_SECONDS)
            await broadcast(room, "phase_changed", {
                "phase": room.phase.value,
                "night_number": room.night_number,
                "night_sub_phase": room.night_sub_phase.value,
                "phase_ends_at": room.phase_ends_at,
            })
            seer = next(
                (p for p in room.game_players.values() if p.alive and p.role == Role.SEER),
                None,
            )
            if seer:
                await _send_to_player(room, seer.id, "seer_prompt", {
                    "targets": [
                        {"id": p.id, "name": p.name}
                        for p in room.game_players.values()
                        if p.alive and p.id != seer.id
                    ],
                })
                try:
                    await asyncio.wait_for(room.night_action_complete.wait(), timeout=SEER_SECONDS)
                except asyncio.TimeoutError:
                    pass

            # Witch
            room.night_sub_phase = NightSubPhase.WITCH
            room.night_action_complete = asyncio.Event()
            room.witch_healed_this_night = False
            room.witch_killed_target = None
            _set_phase_end(room, WITCH_SECONDS)
            await broadcast(room, "phase_changed", {
                "phase": room.phase.value,
                "night_number": room.night_number,
                "night_sub_phase": room.night_sub_phase.value,
                "phase_ends_at": room.phase_ends_at,
            })
            witch = next(
                (p for p in room.game_players.values() if p.alive and p.role == Role.WITCH),
                None,
            )
            if witch:
                await _send_to_player(room, witch.id, "witch_prompt", {
                    "werewolf_victim": room.werewolf_victim,
                    "heal_available": not room.witch_heal_used,
                    "kill_available": not room.witch_kill_used,
                    "targets": [
                        {"id": p.id, "name": p.name}
                        for p in room.game_players.values()
                        if p.alive and p.id != witch.id
                    ],
                })
                try:
                    await asyncio.wait_for(room.night_action_complete.wait(), timeout=WITCH_SECONDS)
                except asyncio.TimeoutError:
                    pass

            night_resolution = resolve_night(
                room.werewolf_victim,
                room.witch_healed_this_night,
                room.witch_killed_target,
                room.lovers,
                room.game_players,
            )
            deaths, causes = _apply_deaths(
                room,
                night_resolution.deaths,
                dict(night_resolution.death_causes),
            )
            room.last_deaths = deaths
            room.last_death_causes = causes

            room.night_sub_phase = None
            room.day_sub_phase = DaySubPhase.ANNOUNCEMENT
            _set_phase_end(room, ANNOUNCEMENT_SECONDS)
            await broadcast(room, "death_announcement", {
                "deaths": deaths,
                "causes": causes,
                "players": _public_players(room),
                "phase_ends_at": room.phase_ends_at,
            })

            await _run_hunter_revenge(room)
            if await _check_and_finish(room):
                return
            await asyncio.sleep(ANNOUNCEMENT_SECONDS)

            # Day discussion
            room.day_number += 1
            room.day_sub_phase = DaySubPhase.DISCUSSION
            _set_phase_end(room, room.discussion_seconds)
            await broadcast(room, "phase_changed", {
                "phase": room.phase.value,
                "day_number": room.day_number,
                "day_sub_phase": room.day_sub_phase.value,
                "phase_ends_at": room.phase_ends_at,
                "players": _public_players(room),
            })
            await asyncio.sleep(room.discussion_seconds)

            # Day voting
            room.day_sub_phase = DaySubPhase.VOTING
            room.day_votes = {}
            room.day_vote_complete = asyncio.Event()
            _set_phase_end(room, DAY_VOTE_SECONDS)
            await broadcast(room, "phase_changed", {
                "phase": room.phase.value,
                "day_number": room.day_number,
                "day_sub_phase": room.day_sub_phase.value,
                "phase_ends_at": room.phase_ends_at,
            })
            try:
                await asyncio.wait_for(room.day_vote_complete.wait(), timeout=DAY_VOTE_SECONDS)
            except asyncio.TimeoutError:
                pass

            voted_out = resolve_day_vote(room.day_votes, _alive_ids(room))
            deaths = []
            causes = {}
            if voted_out:
                deaths, causes = _apply_deaths(room, [voted_out], {voted_out: "vote"})

            room.day_sub_phase = DaySubPhase.VOTE_RESULT
            room.last_deaths = deaths
            room.last_death_causes = causes
            await broadcast(room, "vote_result", {
                "voted_out": voted_out,
                "deaths": deaths,
                "causes": causes,
                "players": _public_players(room),
            })

            await _run_hunter_revenge(room)
            if await _check_and_finish(room):
                return

            await asyncio.sleep(3)

    except asyncio.CancelledError:
        logger.info("Werewolf loop cancelled for room %s", room.code)
    except Exception:
        logger.exception("Werewolf loop crashed for room %s", room.code)
        room.phase = GamePhase.FINISHED
        room.night_sub_phase = None
        room.day_sub_phase = None
        room.phase_ends_at = None
    finally:
        room.game_task = None
