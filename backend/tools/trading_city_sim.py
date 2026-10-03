"""Trading City economy simulator — a BALANCE TOOL, not product code and not a test.

Plays seeded games entirely through the rules engine (no server, no timers) and
prints aggregate economy metrics, so balance changes can be compared before a
playtest. Humans are simulated as idle (no lots, no bids, always pass projects);
every other city is played by the configured AI strategy. Results therefore
describe an AI-driven economy — real humans bid differently.

Usage (from ``backend/``):

    uv run python -m tools.trading_city_sim
    uv run python -m tools.trading_city_sim --games 50 --humans 3
    uv run python -m tools.trading_city_sim prestige_cash_per_vp=3 cash_per_vp=12
    uv run python -m tools.trading_city_sim --compare grand_city_from_round=1
    uv run python -m tools.trading_city_sim --sweep resource_split=handwritten,even,gentle --detail

Positional ``key=value`` arguments override any ``BalanceConfig`` field.
``--compare`` runs the defaults and the overridden config side by side.
``--sweep key=a,b,c`` runs one column per value. ``--detail`` adds per-city
scores, per-resource selling rates and basic-vs-refined prices. Human seats
rotate between games so every city is played by the AI equally often.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import random
import statistics as st
from enum import Enum

from app.trading_city.config import DEFAULT_CONFIG, BalanceConfig
from app.trading_city.engine import TradingGame
from app.trading_city.economy import CITY_NAMES, RESOURCES
from app.trading_city.projects import BASIC


def parse_overrides(pairs: list[str]) -> dict:
    """Turn ``key=value`` strings into typed ``BalanceConfig`` overrides."""
    fields = {f.name: f for f in dataclasses.fields(BalanceConfig)}
    overrides = {}
    for pair in pairs:
        key, _, raw = pair.partition("=")
        if key not in fields:
            raise SystemExit(f"Unknown config field: {key}. Options: {', '.join(sorted(fields))}")
        current = getattr(DEFAULT_CONFIG, key)
        if isinstance(current, str):
            value = raw
        elif raw.lower() == "none":
            value = None
        elif isinstance(current, Enum):
            value = type(current)(raw)
        elif isinstance(current, tuple):
            parts = raw.split(",")
            value = tuple(parts if current and isinstance(current[0], str) else (int(x) for x in parts))
        elif isinstance(current, bool):
            value = raw.lower() in ("1", "true", "yes")
        elif isinstance(current, (int, float)) or current is None:
            value = float(raw) if "." in raw else int(raw)
        else:
            raise SystemExit(f"Can't override {key} from the command line")
        overrides[key] = value
    return overrides


def play(config: BalanceConfig, seed: int, humans: int) -> tuple[TradingGame, dict]:
    players = [(f"p{i}", f"Human {i}") for i in range(humans)]
    game = TradingGame(players, config=config, rng=random.Random(seed))
    # Spread humans across the slots, rotating per game, so every city is AI-played equally.
    for i in range(humans):
        game.claim_city(f"p{i}", (seed + i * len(CITY_NAMES) // humans) % len(CITY_NAMES))
    game.finish_city_selection()
    humans_slots = {c.index for c in game.human_cities()}
    ai = [c for c in game.cities if c.is_ai]
    tracked = {
        "discarded": 0,
        "stock_after_production": [],
        "produced": collections.Counter(),
        "lotted": collections.Counter(),
        "stuck": [],
    }
    for _ in range(config.total_rounds):
        game.start_round()
        tracked["stock_after_production"] += [sum(c.inventory.values()) for c in ai]
        for c in ai:
            tracked["produced"].update(game.last_production[c.index])
        game.open_lot_creation()
        for c in ai:
            if game.lots.get(c.index):
                tracked["lotted"].update(game.lots[c.index].contents)
        game.start_auctions()
        while game.reveal_next_lot(0.0) is not None:
            while game.run_ai_auction_step(0.0):
                pass
            game.auction.passed.update(humans_slots)
            game.resolve_auction()
        for c in ai:  # could this city afford anything on the board?
            tracked["stuck"].append(
                not any(card and game.can_afford(c, card) for card in game.project_slots)
            )
        game.start_projects()
        while (pid := game.current_project_player()) is not None:
            game.pass_project(pid)
        game.run_upkeep()
        game.start_cleanup()
        game.finish_cleanup()
        tracked["discarded"] += sum(sum(game.last_discards.get(c.index, {}).values()) for c in ai)
    return game, tracked


def metrics(game: TradingGame, tracked: dict) -> dict:
    cfg = game.config
    ai = [c for c in game.cities if c.is_ai]
    sold = [h for h in game.history if h.winner is not None]
    units = sum(sum(h.contents.values()) for h in sold)
    cats = collections.Counter(e.card.category.value for e in game.project_log)
    late = cfg.total_rounds - 2
    city_timing = collections.Counter(
        ("grand" if e.card.vp else "plain", "late" if e.round >= late else "early")
        for e in game.project_log
        if e.card.category.value == "city"
    )
    # Money ever created: starting cash + base income (income projects add a little more).
    minted = len(game.cities) * (cfg.starting_cash + cfg.income_per_round * cfg.total_rounds)
    scores = [game.score_for(c) for c in ai] or [0]
    # $ per unit for lots made only of basic or only of refined goods, early vs late.
    prices: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for h in sold:
        kinds = {r in BASIC for r in h.contents}
        if len(kinds) == 1:
            key = f"{'basic' if kinds.pop() else 'refined'}_{'early' if h.round <= 3 else 'late' if h.round >= late else 'mid'}"
            prices[key][0] += h.price
            prices[key][1] += sum(h.contents.values())
    detail = {
        **{f"price_{k}": p / n for k, (p, n) in prices.items() if n},
        **{f"city_score_{c.index}": game.score_for(c) for c in ai},
        **{
            f"sold_{r.value}": tracked["lotted"][r] / tracked["produced"][r]
            for r in RESOURCES
            if tracked["produced"][r]
        },
    }
    return {
        **detail,
        "lots_sold": len(sold) / max(len(game.history), 1),
        "price_per_unit": sum(h.price for h in sold) / max(units, 1),
        "projects": len(game.project_log),
        "prestige": cats["prestige"],
        "city": cats["city"],
        "market": cats["market"],
        "ai_vp": st.mean(c.vp for c in ai) if ai else 0,
        "ai_score": st.mean(scores),
        "score_spread": max(scores) - min(scores),
        "ai_end_cash": st.mean(c.cash for c in ai) if ai else 0,
        "money_sunk": (minted - sum(c.cash for c in game.cities)) / minted,
        "end_shortages": st.mean(c.shortage for c in ai) if ai else 0,
        "discarded": tracked["discarded"] / max(len(ai), 1),
        "stuck": st.mean(tracked["stuck"]) if tracked["stuck"] else 0,
        "stock": st.mean(tracked["stock_after_production"]) if ai else 0,
        **{f"city_{kind}_{when}": city_timing[(kind, when)] for kind in ("plain", "grand") for when in ("early", "late")},
    }


ROWS = [
    ("Lots sold", "lots_sold", "{:.0%}"),
    ("$ per unit at auction", "price_per_unit", "{:.2f}"),
    ("Nothing affordable at turn", "stuck", "{:.0%}"),
    ("Projects / game", "projects", "{:.1f}"),
    ("  Prestige", "prestige", "{:.1f}"),
    ("  City", "city", "{:.1f}"),
    ("  Market", "market", "{:.1f}"),
    ("City plain, early rounds", "city_plain_early", "{:.1f}"),
    ("City plain, last 3 rounds", "city_plain_late", "{:.1f}"),
    ("City grand, early rounds", "city_grand_early", "{:.1f}"),
    ("City grand, last 3 rounds", "city_grand_late", "{:.1f}"),
    ("AI VP", "ai_vp", "{:.1f}"),
    ("AI score (VP + cash)", "ai_score", "{:.1f}"),
    ("AI score spread", "score_spread", "{:.1f}"),
    ("AI end cash", "ai_end_cash", "${:.0f}"),
    ("Money removed", "money_sunk", "{:.0%}"),
    ("End shortages / AI city", "end_shortages", "{:.2f}"),
    ("Discarded / AI city / game", "discarded", "{:.1f}"),
    ("Stock after production", "stock", "{:.1f}"),
]


def summarize(config: BalanceConfig, games: int, seed: int, humans: int) -> dict:
    runs = [metrics(*play(config, seed + i, humans)) for i in range(games)]
    keys = {key for r in runs for key in r}
    # Some keys only exist in some games (e.g. a city's score when it was AI-played).
    return {key: st.mean(r[key] for r in runs if key in r) for key in keys}


def detail_rows() -> list[tuple[str, str, str]]:
    rows = [("Score by city (when AI-played)", "", "")]
    for i, (profile, city, _) in enumerate(CITY_NAMES):
        rows.append((f"  {city} ({profile})", f"city_score_{i}", "{:.1f}"))
    rows.append(("Share of production put in lots", "", ""))
    for r in RESOURCES:
        rows.append((f"  {r.value}{' (basic)' if r in BASIC else ''}", f"sold_{r.value}", "{:.0%}"))
    rows.append(("$ per unit, pure basic / refined lots", "", ""))
    for kind in ("basic", "refined"):
        for when, label in (("early", "rounds 1-3"), ("late", "last 3 rounds")):
            rows.append((f"  {kind}, {label}", f"price_{kind}_{when}", "{:.2f}"))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("overrides", nargs="*", help="BalanceConfig overrides, e.g. cash_per_vp=12")
    parser.add_argument("--games", type=int, default=20, help="games per configuration (default 20)")
    parser.add_argument("--seed", type=int, default=0, help="first RNG seed (default 0)")
    parser.add_argument("--humans", type=int, default=2, help="idle human seats, 1-8 (default 2)")
    parser.add_argument("--compare", action="store_true", help="also run the defaults, side by side")
    parser.add_argument("--sweep", help="one column per value, e.g. resource_split=even,gentle,strong")
    parser.add_argument("--detail", action="store_true", help="per-city scores, selling rates, prices")
    args = parser.parse_args()

    overrides = parse_overrides(args.overrides)
    base = dataclasses.replace(DEFAULT_CONFIG, **overrides)
    if args.sweep:
        key, _, values = args.sweep.partition("=")
        columns = {
            value: dataclasses.replace(base, **parse_overrides([f"{key}={value}"]))
            for value in values.split(",")
        }
    else:
        columns = {"overrides" if overrides else "defaults": base}
        if args.compare and overrides:
            columns = {"defaults": DEFAULT_CONFIG, **columns}

    results = {name: summarize(cfg, args.games, args.seed, args.humans) for name, cfg in columns.items()}
    print(f"{args.games} games each, {args.humans} idle humans, {8 - args.humans} AI cities")
    if overrides:
        print("overrides:", ", ".join(f"{k}={v}" for k, v in overrides.items()))
    print()
    width = 38 if args.detail else 28
    print(f"{'':{width}s}" + "".join(f"{name:>14s}" for name in results))
    rows = ROWS + (detail_rows() if args.detail else [])
    for label, key, fmt in rows:
        cells = "".join(
            f"{(fmt.format(r[key]) if key in r else '-') if key else '':>14s}" for r in results.values()
        )
        print(f"{label:38s}{cells}" if args.detail else f"{label:28s}{cells}")


if __name__ == "__main__":
    main()
