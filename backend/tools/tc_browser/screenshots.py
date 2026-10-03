"""Screenshot tour of a Trading City game — WORK IN PROGRESS, not product code.

Creates a 3-player game through the API and captures the phone (player) and TV
(host dashboard) views at each phase: lobby, city selection, production,
market study,
lot building, auction, projects and (round 2) the Cleanup discard screen. Needs Chrome + backend + Vite running; see tools/README.md.

    uv run python -m tools.tc_browser.screenshots [--out DIR]

Known rough edges: fixed sleeps instead of waiting for render; long phase
timers are used so the game holds still while screenshots are taken.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import httpx

from .cdp import DEFAULT_CHROME, DEFAULT_FRONTEND, Tab, check_services
from .game_api import TCClient

DEFAULT_OUT = Path(__file__).parent / "output" / "screenshots"


async def tour(chrome: str, frontend: str, out: Path) -> None:
    await check_services(chrome, frontend)
    async with httpx.AsyncClient() as http:
        api = TCClient(http, frontend)
        host = await api.create()
        players = [await api.join(n) for n in ("Ana", "Ben", "Cleo")]
        phone = await Tab(chrome, frontend).open(400, 860, mobile=True)
        tv = await Tab(chrome, frontend).open(1600, 1000, mobile=False)
        await phone.open_as("lobby", api.code, players[0], is_host=False)
        await tv.open_as("lobby", api.code, host, is_host=True)
        await tv.screenshot(out / "01-lobby-tv.png", full_page=False)

        await api.post("start", host, {
            "total_rounds": 8, "auction_seconds": 60, "lot_creation_seconds": 120,
            "project_turn_seconds": 60,
        })
        await api.wait_for(host, lambda s: s["phase"] == "city_selection")
        await api.post("claim", players[1], {"slot": 4})
        await phone.screenshot(out / "02-city-selection-phone.png")
        await tv.screenshot(out / "03-city-selection-tv.png", full_page=False)
        await api.post("claim", players[0], {"slot": 0})
        await api.post("claim", players[2], {"slot": 6})

        await api.wait_for(host, lambda s: s["phase"] == "production")
        await api.post("ready", players[1])  # one player already tapped Continue
        await phone.screenshot(out / "03b-production-phone.png", full_page=False)
        await tv.screenshot(out / "03c-production-tv.png", full_page=False)
        for p in (players[0], players[2]):
            await api.post("ready", p)  # everyone continued -> moves on immediately

        await api.wait_for(host, lambda s: s["phase"] == "market_study", timeout=10)
        await phone.screenshot(out / "03d-market-study-phone.png")
        await tv.screenshot(out / "03e-market-study-tv.png", full_page=False)
        for p in players:
            await api.post("ready", p)

        await api.wait_for(host, lambda s: s["phase"] == "lot_creation", timeout=10)
        await phone.screenshot(out / "04-lot-phone.png")
        await api.post("lot", players[0], {"contents": {"grain": 3, "livestock": 1}})
        await api.post("lot", players[1], {"contents": {"cloth": 2, "tools": 1}})
        await tv.screenshot(out / "05-lot-tv.png", full_page=False)
        await api.post("lot", players[2], {"contents": {"wine": 2}})

        state = await api.wait_for(host, lambda s: s["auction"] is not None)
        seller = state["auction"]["seller"]
        bidders = [p for p, slot in zip(players, (0, 4, 6)) if slot != seller]
        await api.post("bid", bidders[0], {"amount": 3})
        await api.post("bid", bidders[1], {"amount": 5})
        await phone.screenshot(out / "06-auction-phone.png", full_page=False)
        await tv.screenshot(out / "07-auction-tv.png", full_page=False)

        # Everyone drops out of each remaining lot to reach Projects fast.
        await drop_out_of_auctions(api, host, players)
        await api.wait_for(host, lambda s: s["phase"] == "projects")
        await phone.screenshot(out / "08-projects-phone.png")
        await tv.screenshot(out / "09-projects-tv.png", full_page=False)

        # Round 2: keep everything (no lots, no bids) so storage overflows at Cleanup.
        await finish_projects_and_upkeep(api, host, players)
        await api.wait_for(host, lambda s: s["phase"] == "production" and s["round"] == 2)
        for phase in ("production", "market_study"):
            await api.wait_for(host, lambda s, ph=phase: s["phase"] == ph)
            for p in players:
                await api.post("ready", p)
        await api.wait_for(host, lambda s: s["phase"] == "lot_creation" and s["round"] == 2)
        for p in players:
            await api.post("lot", p, {"contents": {}})
        await drop_out_of_auctions(api, host, players)
        await finish_projects_and_upkeep(api, host, players)
        state = await api.wait_for(host, lambda s: s["phase"] in ("cleanup", "production"))
        if state["phase"] == "cleanup":
            await phone.screenshot(out / "10-discard-phone.png")
        else:
            print("nobody was over storage this run; no discard screenshot")
        print("game code", api.code)


async def drop_out_of_auctions(api: TCClient, host: str, players: list[str]) -> None:
    """Everyone drops out of each lot once, so auctions close quickly."""
    passed: set[int] = set()
    while (state := await api.public(host))["phase"] in ("lot_creation", "auction"):
        lot = state["auction"]
        if lot and lot["lot_id"] not in passed:
            passed.add(lot["lot_id"])
            for p in players:
                await api.post("auction-pass", p)
        await asyncio.sleep(0.5)


async def finish_projects_and_upkeep(api: TCClient, host: str, players: list[str]) -> None:
    """Pass every project turn, then tap Continue on the upkeep summary."""
    while (state := await api.public(host))["phase"] == "projects":
        turn = state["project_turn_player"]
        if turn:
            await api.post("project-pass", turn)
        await asyncio.sleep(0.3)
    await api.wait_for(host, lambda s: s["phase"] != "projects")
    if (await api.public(host))["phase"] == "upkeep":
        for p in players:
            await api.post("ready", p)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output directory (default {DEFAULT_OUT})")
    parser.add_argument("--chrome", default=DEFAULT_CHROME, help="Chrome DevTools URL")
    parser.add_argument("--frontend", default=DEFAULT_FRONTEND, help="Vite dev server URL")
    args = parser.parse_args()
    asyncio.run(tour(args.chrome, args.frontend, args.out))


if __name__ == "__main__":
    main()
