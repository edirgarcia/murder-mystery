"""Trading City room state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from ..shared.game_state import BaseGameRoom, GameStore
from .config import DEFAULT_CONFIG, BalanceConfig
from .engine import TradingGame


@dataclass
class TCRoom(BaseGameRoom):
    config: BalanceConfig = DEFAULT_CONFIG
    game: TradingGame | None = None
    # Wall-clock timestamp when the current timed phase/turn ends (None = untimed).
    deadline: float | None = None
    # Players who tapped Continue on the current summary screen (None = not a summary).
    ready: set[str] | None = None
    # Set whenever a player action may let the game loop advance early.
    changed: asyncio.Event = field(default_factory=asyncio.Event)
    # Set by the dashboard when the current narration line finished playing.
    narration_ack: asyncio.Event | None = None
    # Tutorial lines already played this game (each phase is explained once).
    explained: set[str] = field(default_factory=set)
    game_task: asyncio.Task | None = None


class TCStore(GameStore[TCRoom]):
    def __init__(self) -> None:
        super().__init__(TCRoom)


store = TCStore()
