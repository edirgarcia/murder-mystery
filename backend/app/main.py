"""FastAPI application entry point."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from dataclasses import dataclass
from typing import Callable

from fastapi import APIRouter

from .shared.config import CORS_ORIGINS
from .shared.game_state import GameStore
from .shared.routes.lobby import create_lobby_router
from .shared.routes.ws import create_ws_router
from .murder_mystery.config import MAX_PLAYERS as MM_MAX_PLAYERS
from .murder_mystery.game_state import store as mm_store
from .murder_mystery.info import build_game_info as mm_build_game_info
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
from .basta.config import MAX_PLAYERS as BA_MAX_PLAYERS
from .basta.game_state import store as ba_store
from .basta.info import build_game_info as ba_build_game_info
from .basta.routes import game as ba_game
from .trading_city.config import MAX_PLAYERS as TC_MAX_PLAYERS
from .trading_city.game_state import store as tc_store
from .trading_city.info import build_game_info as tc_build_game_info
from .trading_city.routes import game as tc_game


@dataclass(frozen=True)
class GameRegistration:
    """Everything the platform needs to mount one game."""

    slug: str  # URL path segment, e.g. "murder-mystery"
    api_prefix: str  # e.g. "/api/mm/games"
    store: GameStore
    max_players: int
    info_builder: Callable
    game_router: APIRouter

    @property
    def html_file(self) -> str:
        return f"{self.slug}.html"


GAMES: tuple[GameRegistration, ...] = (
    GameRegistration("murder-mystery", "/api/mm/games", mm_store, MM_MAX_PLAYERS, mm_build_game_info, mm_game.router),
    GameRegistration("funny-questions", "/api/fq/games", fq_store, FQ_MAX_PLAYERS, fq_build_game_info, fq_game.router),
    GameRegistration("werewolf", "/api/ww/games", ww_store, WW_MAX_PLAYERS, ww_build_game_info, ww_game.router),
    GameRegistration("prisoners-dilemma", "/api/pd/games", pd_store, PD_MAX_PLAYERS, pd_build_game_info, pd_game.router),
    GameRegistration("basta", "/api/ba/games", ba_store, BA_MAX_PLAYERS, ba_build_game_info, ba_game.router),
    GameRegistration("trading-city", "/api/tc/games", tc_store, TC_MAX_PLAYERS, tc_build_game_info, tc_game.router),
)

app = FastAPI(title="Party Games Platform", version="0.2.0")

# In production, the frontend sends requests like /murder-mystery/api/mm/games/...
# (Vite dev proxy strips the game prefix; this middleware does the same in prod.)
# Must be a raw ASGI middleware so it applies to both HTTP and WebSocket connections.
_GAME_PREFIX_RE = re.compile(
    r"^/(" + "|".join(re.escape(g.slug) for g in GAMES) + r")(/api/.*)"
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

for _g in GAMES:
    app.include_router(create_lobby_router(_g.store, _g.max_players, _g.info_builder, _g.api_prefix))
    app.include_router(_g.game_router)
    app.include_router(create_ws_router(_g.store, _g.api_prefix))


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


# --- Static file serving (production only) ---
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.is_dir():
    # SPA fallback: serve each game's HTML for its client-side routes
    _SPA_GAMES = {g.slug: g.html_file for g in GAMES}

    @app.get("/")
    async def root_index():
        return FileResponse(STATIC_DIR / "index.html")

    # Serve game-specific audio files before SPA catch-all
    for _game in _SPA_GAMES:
        _audio_dir = STATIC_DIR / _game / "audio"
        if _audio_dir.is_dir():
            app.mount(f"/{_game}/audio", StaticFiles(directory=_audio_dir), name=f"{_game}-audio")

    for _game, _html in _SPA_GAMES.items():

        def _make_handler(html_file: str):
            async def _handler():
                return FileResponse(STATIC_DIR / html_file)
            return _handler

        app.get(f"/{_game}/{{path:path}}")(_make_handler(_html))

    # Serve Vite build assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
