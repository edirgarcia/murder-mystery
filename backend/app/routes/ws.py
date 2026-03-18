"""WebSocket route for real-time game events."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..game_state import GameRoom, store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])


@router.websocket("/api/games/{code}/ws")
async def game_websocket(websocket: WebSocket, code: str, player_id: str) -> None:
    room = store.get_room(code)
    if not room:
        await websocket.close(code=4004, reason="Game not found")
        return

    # Allow host or player to connect
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
            # Keep connection alive; handle pings
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        logger.info("%s disconnected from room %s", client_name, code)
    finally:
        room.connections.pop(player_id, None)
        if not is_host and player:
            await broadcast(
                room,
                "player_disconnected",
                {"player_id": player.id, "player_name": player.name},
            )


async def broadcast(
    room: GameRoom,
    event: str,
    data: dict,
    exclude: str | None = None,
) -> None:
    """Send an event to all connected clients in a room."""
    message = json.dumps({"event": event, "data": data})
    disconnected = []
    for pid, ws in room.connections.items():
        if pid == exclude:
            continue
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(pid)
    for pid in disconnected:
        room.connections.pop(pid, None)
