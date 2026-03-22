"""FastAPI application entry point."""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .shared.config import CORS_ORIGINS
from .shared.routes.lobby import create_lobby_router
from .shared.routes.ws import create_ws_router
from .murder_mystery.config import MAX_PLAYERS
from .murder_mystery.game_state import store as mm_store
from .murder_mystery.info import build_game_info
from .murder_mystery.routes import game as mm_game
from .funny_questions.config import MAX_PLAYERS as FQ_MAX_PLAYERS
from .funny_questions.game_state import store as fq_store
from .funny_questions.info import build_game_info as fq_build_game_info
from .funny_questions.routes import game as fq_game
from .werewolf.config import MAX_PLAYERS as WW_MAX_PLAYERS
from .werewolf.game_state import store as ww_store
from .werewolf.info import build_game_info as ww_build_game_info
from .werewolf.routes import game as ww_game
from .prisoners_dilemma.config import MAX_PLAYERS as PD_MAX_PLAYERS
from .prisoners_dilemma.game_state import store as pd_store
from .prisoners_dilemma.info import build_game_info as pd_build_game_info
from .prisoners_dilemma.routes import game as pd_game

app = FastAPI(title="Party Games Platform", version="0.2.0")

# In production, the frontend sends requests like /murder-mystery/api/mm/games/...
# (Vite dev proxy strips the game prefix; this middleware does the same in prod.)
# Must be a raw ASGI middleware so it applies to both HTTP and WebSocket connections.
_GAME_PREFIX_RE = re.compile(
    r"^/(murder-mystery|funny-questions|werewolf|prisoners-dilemma)(/api/.*)"
)


class StripGamePrefixMiddleware:
    """Strip game path prefix for both HTTP and WebSocket requests."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            m = _GAME_PREFIX_RE.match(scope["path"])
            if m:
                scope["path"] = m.group(2)
        await self.app(scope, receive, send)


app.add_middleware(StripGamePrefixMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Murder Mystery ---
mm_lobby = create_lobby_router(mm_store, MAX_PLAYERS, build_game_info, "/api/mm/games")
mm_ws = create_ws_router(mm_store, "/api/mm/games")
app.include_router(mm_lobby)
app.include_router(mm_game.router)
app.include_router(mm_ws)


# --- Funny Questions ---
fq_lobby = create_lobby_router(fq_store, FQ_MAX_PLAYERS, fq_build_game_info, "/api/fq/games")
fq_ws = create_ws_router(fq_store, "/api/fq/games")
app.include_router(fq_lobby)
app.include_router(fq_game.router)
app.include_router(fq_ws)

# --- Werewolf ---
ww_lobby = create_lobby_router(ww_store, WW_MAX_PLAYERS, ww_build_game_info, "/api/ww/games")
ww_ws = create_ws_router(ww_store, "/api/ww/games")
app.include_router(ww_lobby)
app.include_router(ww_game.router)
app.include_router(ww_ws)

# --- Prisoner's Dilemma ---
pd_lobby = create_lobby_router(pd_store, PD_MAX_PLAYERS, pd_build_game_info, "/api/pd/games")
pd_ws = create_ws_router(pd_store, "/api/pd/games")
app.include_router(pd_lobby)
app.include_router(pd_game.router)
app.include_router(pd_ws)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


# --- Static file serving (production only) ---
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.is_dir():
    # SPA fallback: serve each game's HTML for its client-side routes
    _SPA_GAMES = {
        "murder-mystery": "murder-mystery.html",
        "funny-questions": "funny-questions.html",
        "werewolf": "werewolf.html",
        "prisoners-dilemma": "prisoners-dilemma.html",
    }

    @app.get("/")
    async def root_index():
        return FileResponse(STATIC_DIR / "index.html")

    for _game, _html in _SPA_GAMES.items():

        def _make_handler(html_file: str):
            async def _handler():
                return FileResponse(STATIC_DIR / html_file)
            return _handler

        app.get(f"/{_game}/{{path:path}}")(_make_handler(_html))

    # Serve Vite build assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
