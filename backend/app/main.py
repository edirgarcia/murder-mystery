"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .routes import game, lobby, ws

app = FastAPI(title="Murder Mystery Party Game", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lobby.router)
app.include_router(game.router)
app.include_router(ws.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
