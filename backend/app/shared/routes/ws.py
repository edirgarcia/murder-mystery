"""Shared WebSocket route factory for real-time game events."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..game_state import BaseGameRoom, GameStore

logger = logging.getLogger(__name__)

# Grace period after the host disconnects before the room is torn down.
# Long enough to survive a dashboard refresh or brief network blip, since
# the host reconnects from localStorage.
HOST_DISCONNECT_GRACE_SECONDS = 20


async def _teardown_room(store: GameStore, room: BaseGameRoom) -> None:
    """End the game for everyone after the host has been gone for a grace period."""
    try:
        await asyncio.sleep(HOST_DISCONNECT_GRACE_SECONDS)
    except asyncio.CancelledError:
        return  # Host reconnected — abort teardown.

    logger.info("Host did not return to room %s; tearing down", room.code)

    # Cancel any running game/timer tasks so they don't outlive the room.
    for attr in ("game_task", "timer_task"):
        task = getattr(room, attr, None)
        if task is not None and not task.done():
            task.cancel()

    await broadcast(room, "host_left", {})
    for ws in list(room.connections.values()):
        try:
            await ws.close(code=4000, reason="Host left")
        except Exception:
            pass
    room.connections.clear()
    store.delete_room(room.code)


def create_ws_router(store: GameStore, prefix: str) -> APIRouter:
    """Create a WebSocket router bound to a specific game store."""
    router = APIRouter(tags=["ws"])

    @router.websocket(f"{prefix}/{{code}}/ws")
    async def game_websocket(websocket: WebSocket, code: str, player_id: str) -> None:
        room = store.get_room(code)
        if not room:
            await websocket.close(code=4004, reason="Game not found")
            return

        is_host = store.is_host(room, player_id)
        player = None if is_host else store.get_player(room, player_id)

        if not is_host and not player:
            await websocket.close(code=4004, reason="Player not found")
            return

        await websocket.accept()
        room.connections[player_id] = websocket

        # Host came back before the grace period elapsed — abort teardown.
        if is_host and room.host_teardown_task is not None:
            if not room.host_teardown_task.done():
                room.host_teardown_task.cancel()
            room.host_teardown_task = None

        client_name = room.host_name if is_host else player.name
        logger.info("%s (%s) connected to room %s", client_name, player_id, code)

        # Notify others only for player connections (not host)
        if not is_host and player:
            await broadcast(
                room,
                "player_joined",
                {"player_id": player.id, "player_name": player.name},
                exclude=player_id,
            )

        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"event": "pong"}))
                elif msg.get("type") == "narration_ack":
                    ack = getattr(room, "narration_ack", None)
                    if ack is not None:
                        ack.set()
                elif msg.get("type") == "skip_intro":
                    skip = getattr(room, "skip_intro", None)
                    if skip is not None:
                        skip.set()
                    # Unblock the line currently being awaited so the
                    # intro loop can see the skip flag and stop.
                    ack = getattr(room, "narration_ack", None)
                    if ack is not None:
                        ack.set()
        except WebSocketDisconnect:
            logger.info("%s disconnected from room %s", client_name, code)
        finally:
            # Only act if this is still the active connection (not replaced by a newer one)
            was_active = room.connections.get(player_id) is websocket
            if was_active:
                room.connections.pop(player_id, None)
            if not is_host and player:
                await broadcast(
                    room,
                    "player_disconnected",
                    {"player_id": player.id, "player_name": player.name},
                )
            elif is_host and was_active:
                # Host left — give them a grace period to reconnect, then
                # tear the room down for all players if they don't return.
                if room.host_teardown_task is None or room.host_teardown_task.done():
                    room.host_teardown_task = asyncio.create_task(
                        _teardown_room(store, room)
                    )

    return router


async def broadcast(
    room: BaseGameRoom,
    event: str,
    data: dict,
    exclude: str | None = None,
) -> None:
    """Send an event to all connected clients in a room."""
    message = json.dumps({"event": event, "data": data})
    targets = list(room.connections.items())
    failed: list[tuple[str, WebSocket]] = []
    sent = 0
    for pid, ws in targets:
        if pid == exclude:
            continue
        try:
            await ws.send_text(message)
            sent += 1
        except Exception as e:
            print(f"[WS] broadcast {event} FAILED for {pid}: {e}")
            failed.append((pid, ws))
    if event not in ("pong",):
        print(f"[WS] broadcast '{event}' → sent={sent}, failed={len(failed)}, total_conns={len(targets)}")
    for pid, ws in failed:
        # Only remove if this is still the active connection
        if room.connections.get(pid) is ws:
            room.connections.pop(pid, None)
