"""Shared application settings."""

from __future__ import annotations

import os

_extra = os.environ.get("CORS_ORIGINS", "")
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
] + [o.strip() for o in _extra.split(",") if o.strip()]

ROOM_CODE_LENGTH = 4
