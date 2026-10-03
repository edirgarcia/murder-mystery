"""Trading City request models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .config import AIProjectPriority, AIStrategyKind
from .economy import Resource


class StartTCRequest(BaseModel):
    total_rounds: int = Field(default=8, ge=1, le=12)
    auction_seconds: int = Field(default=20, ge=8, le=90)
    lot_creation_seconds: int = Field(default=60, ge=15, le=300)
    project_turn_seconds: int = Field(default=30, ge=10, le=120)
    ai_strategy: AIStrategyKind = AIStrategyKind.HEURISTIC
    ai_project_priority: AIProjectPriority = AIProjectPriority.ROTATING


class ClaimCityRequest(BaseModel):
    slot: int = Field(..., ge=0, le=7)


class BundleRequest(BaseModel):
    contents: dict[Resource, int] = Field(default_factory=dict)


class BidRequest(BaseModel):
    amount: int = Field(..., ge=1)


class BuildRequest(BaseModel):
    slot_index: int = Field(..., ge=0)
