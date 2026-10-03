"""Watch a live game against the AI — WORK IN PROGRESS, not product code.

Plays one round through the real timed game loop with two scripted humans:
one opens every AI lot at the minimum bid, so you can see AI cities answer and
outbid each other. Prints every auction (bids, winner, price) and the project
turn order, and screenshots the TV dashboard. Needs Chrome + backend + Vite
running; see tools/README.md. Takes about 2-3 minutes (real timers).

    uv run python -m tools.tc_browser.live_ai_game [--ai-priority after_humans]
"""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

import httpx

from .cdp import DEFAULT_CHROME, DEFAULT_FRONTEND, Tab, check_services
from .game_api import TCClient

DEFAULT_OUT = Path(__file__).parent / "output" / "live_ai_game"


async def watch(chrome: str, frontend: str, out: Path, ai_priority: str, ai_strategy: str) -> None:
    await check_services(chrome, frontend)
    async with httpx.AsyncClient() as http:
        api = TCClient(http, frontend)
        host = await api.create()
        ana, ben = await api.join("Ana"), await api.join("Ben")
        tv = await Tab(chrome, frontend).open(1600, 1000, mobile=False)
        await tv.open_as("lobby", api.code, host, is_host=True)
        await tv.screenshot(out / "01-lobby.png")

        await api.post("start", host, {
            "total_rounds": 8, "auction_seconds": 15, "lot_creation_seconds": 15,
            "project_turn_seconds": 20, "ai_strategy": ai_strategy, "ai_project_priority": ai_priority,
        })
        await api.wait_for(host, lambda s: s["phase"] == "city_selection")
        await api.post("claim", ana, {"slot": 0})
        await api.post("claim", ben, {"slot": 4})

        state = await api.wait_for(host, lambda s: s["phase"] == "lot_creation")
        print("priority:", ", ".join(f"{p['name']}{' (AI)' if p['is_ai'] else ''}" for p in state["priority"]))
        for pid in (ana, ben):
            await api.post("lot", pid, {"contents": {}})

        opened: set[int] = set()
        screenshot_taken = False
        started = time.time()
        while (state := await api.public(host))["phase"] in ("lot_creation", "auction"):
            lot = state["auction"]
            if lot and lot["lot_id"] not in opened and state["cities"][lot["seller"]]["is_ai"]:
                opened.add(lot["lot_id"])
                await api.post("bid", ana, {"amount": lot["min_next_bid"]})
            if lot and len(lot["bids"]) >= 3 and not screenshot_taken:
                await tv.screenshot(out / "02-auction-ai-bidding.png", full_page=False)
                screenshot_taken = True
            await asyncio.sleep(0.25)

        name = lambda slot: state["cities"][slot]["name"]  # noqa: E731
        print(f"auctions took {time.time() - started:.0f}s")
        for h in state["history"]:
            winner = f"{name(h['winner'])} ${h['price']}" if h["winner"] is not None else "unsold"
            bids = " -> ".join(f"{name(b['bidder'])} ${b['amount']}" for b in h["bids"])
            print(f"  {name(h['seller']):12s} {h['contents']} => {winner}   [{bids}]")

        state = await api.wait_for(host, lambda s: s["phase"] == "projects")
        await tv.screenshot(out / "03-projects.png", full_page=False)
        print("built so far:", [(name(e["city"]), e["card"]["name"]) for e in state["project_log"]] or "nothing yet")
        print("game code", api.code)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output directory (default {DEFAULT_OUT})")
    parser.add_argument("--ai-priority", choices=["rotating", "after_humans"], default="rotating")
    parser.add_argument("--ai-strategy", choices=["heuristic", "passive"], default="heuristic")
    parser.add_argument("--chrome", default=DEFAULT_CHROME, help="Chrome DevTools URL")
    parser.add_argument("--frontend", default=DEFAULT_FRONTEND, help="Vite dev server URL")
    args = parser.parse_args()
    asyncio.run(watch(args.chrome, args.frontend, args.out, args.ai_priority, args.ai_strategy))


if __name__ == "__main__":
    main()
