"""Minimal Chrome DevTools Protocol client (WORK IN PROGRESS).

Talks to a Chrome started with ``--remote-debugging-port``. Deliberately tiny:
open a tab, emulate a screen size, seed a player session, take screenshots.
"""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

import httpx
import websockets

DEFAULT_CHROME = "http://localhost:9222"
DEFAULT_FRONTEND = "http://localhost:5173"

CHROME_HELP = """\
Can't reach Chrome's DevTools endpoint at {url}.
Start Chrome headless first, e.g. on macOS:

  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\
      --headless=new --remote-debugging-port=9222 \\
      --user-data-dir=/tmp/tc-chrome --no-first-run --hide-scrollbars about:blank
"""


async def check_services(chrome: str, frontend: str) -> None:
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{chrome}/json/version")
        except httpx.HTTPError:
            raise SystemExit(CHROME_HELP.format(url=chrome)) from None
        try:
            (await client.get(f"{frontend}/trading-city/")).raise_for_status()
        except httpx.HTTPError:
            raise SystemExit(
                f"Can't reach the frontend at {frontend}. Start the backend and Vite "
                "(./run.sh from the repo root)."
            ) from None


class Tab:
    """One Chrome tab with a fixed viewport."""

    def __init__(self, chrome: str = DEFAULT_CHROME, frontend: str = DEFAULT_FRONTEND) -> None:
        self.chrome = chrome
        self.frontend = frontend
        self._id = 0

    async def open(self, width: int, height: int, mobile: bool) -> Tab:
        async with httpx.AsyncClient() as client:
            target = (await client.put(f"{self.chrome}/json/new?about:blank")).json()
        self.ws = await websockets.connect(target["webSocketDebuggerUrl"], max_size=50_000_000)
        await self.cmd(
            "Emulation.setDeviceMetricsOverride",
            width=width, height=height, deviceScaleFactor=1, mobile=mobile,
        )
        return self

    async def cmd(self, method: str, **params) -> dict:
        self._id += 1
        msg_id = self._id
        await self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == msg_id:
                return msg.get("result", {})

    async def open_as(self, page: str, code: str, player_id: str, is_host: bool) -> None:
        """Load a game page as a given player by seeding the app's localStorage session."""
        await self.cmd("Page.navigate", url=f"{self.frontend}/trading-city/")
        await asyncio.sleep(1.5)
        session = (
            f"localStorage.setItem('tc_player_id','{player_id}');"
            f"localStorage.setItem('tc_game_code','{code}');"
            f"localStorage.setItem('tc_is_host','{str(is_host).lower()}')"
        )
        await self.cmd("Runtime.evaluate", expression=session)
        await self.cmd("Page.navigate", url=f"{self.frontend}/trading-city/{page}/{code}")

    async def screenshot(self, path: Path, full_page: bool = True, settle: float = 1.2) -> None:
        await asyncio.sleep(settle)  # WIP: fixed wait for React to render
        result = await self.cmd("Page.captureScreenshot", format="png", captureBeyondViewport=full_page)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(result["data"]))
        print("saved", path)
