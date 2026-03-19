"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(title="Party Games Platform", version="0.2.0")

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


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
