"""Thin async client for the Trading City HTTP API, used by the browser scripts."""

from __future__ import annotations

import asyncio

import httpx


class TCClient:
    def __init__(self, client: httpx.AsyncClient, frontend: str) -> None:
        self.http = client
        self.base = f"{frontend}/trading-city/api/tc/games"
        self.code = ""

    async def create(self, host_name: str = "Host") -> str:
        data = (await self.http.post(self.base, json={"host_name": host_name})).json()
        self.code = data["code"]
        return data["host_id"]

    async def join(self, name: str) -> str:
        res = await self.http.post(f"{self.base}/{self.code}/join", json={"player_name": name})
        return res.json()["player_id"]

    async def post(self, path: str, player_id: str, body: dict | None = None) -> httpx.Response:
        return await self.http.post(
            f"{self.base}/{self.code}/{path}", json=body or {}, headers={"X-Player-Id": player_id}
        )

    async def public(self, player_id: str) -> dict:
        res = await self.http.get(f"{self.base}/{self.code}/state", headers={"X-Player-Id": player_id})
        return res.json()["public"]

    async def wait_for(self, player_id: str, predicate, timeout: float = 120.0) -> dict:
        loop = asyncio.get_running_loop()
        end = loop.time() + timeout
        while loop.time() < end:
            state = await self.public(player_id)
            if predicate(state):
                return state
            await asyncio.sleep(0.3)
        raise TimeoutError("Game did not reach the expected state in time")
