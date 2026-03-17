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

    player = store.get_player(room, player_id)
    if not player:
        await websocket.close(code=4004, reason="Player not found")
        return

    await websocket.accept()
    room.connections[player_id] = websocket
    logger.info("Player %s (%s) connected to room %s", player.name, player_id, code)

    # Notify others
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
        logger.info("Player %s disconnected from room %s", player.name, code)
    finally:
        room.connections.pop(player_id, None)
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
    """Send an event to all connected players in a room."""
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
