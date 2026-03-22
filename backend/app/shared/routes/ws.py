"""Shared WebSocket route factory for real-time game events."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..game_state import BaseGameRoom, GameStore

logger = logging.getLogger(__name__)


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
        except WebSocketDisconnect:
            logger.info("%s disconnected from room %s", client_name, code)
        finally:
            # Only remove if this is still the active connection (not replaced by a newer one)
            if room.connections.get(player_id) is websocket:
                room.connections.pop(player_id, None)
            if not is_host and player:
                await broadcast(
                    room,
                    "player_disconnected",
                    {"player_id": player.id, "player_name": player.name},
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
