"""Tests for the Trading City game."""

from __future__ import annotations

import dataclasses
from collections import Counter
import random
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.trading_city.ai import HeuristicStrategy
from app.trading_city.config import (
    DEFAULT_CONFIG,
    AIProjectPriority,
    AIStrategyKind,
    DisplacedCardPolicy,
    EffectTiming,
)
from app.trading_city.economy import RESOURCES, Resource, build_slots
from app.trading_city.engine import Auction, Bid, Lot, Phase, RuleError, TradingGame
from app.trading_city.game_state import store
from app.trading_city.projects import (
    CITY_PROJECTS,
    MARKET_PROJECTS,
    PRESTIGE_PROJECTS,
    MAX_NON_PRESTIGE_VP,
    MarketAxis,
    MarketLevel,
    ProjectCard,
)
from app.trading_city.views import private_view, public_view

G, L, T, I, C, O, W, S = RESOURCES


def _game(n_players: int = 2, **overrides) -> TradingGame:
    # Rule tests use passive AI so only the humans move; AI tests opt in explicitly.
    overrides.setdefault("ai_strategy", AIStrategyKind.PASSIVE)
    config = dataclasses.replace(DEFAULT_CONFIG, **overrides)
    players = [(f"p{i}", f"Player {i}") for i in range(n_players)]
    return TradingGame(players, config=config, rng=random.Random(42))


def _started(n_players: int = 2, **overrides) -> TradingGame:
    """Players claim slots 0..n-1 in order, then round 1 starts."""
    game = _game(n_players, **overrides)
    for i in range(n_players):
        game.claim_city(f"p{i}", i)
    game.finish_city_selection()
    game.start_round()
    return game


def _card(game: TradingGame, card_id: str) -> int:
    """Force a specific card into project slot 0 (as if drawn) and return its index."""
    for card in CITY_PROJECTS + MARKET_PROJECTS + PRESTIGE_PROJECTS:
        if card.id == card_id:
            for deck in game.decks.values():
                if card in deck:
                    deck.remove(card)
            game.project_slots[0] = card
            return 0
    raise KeyError(card_id)


def _pass_all(game: TradingGame) -> None:
    while (pid := game.current_project_player()) is not None:
        game.pass_project(pid)


def _finish_round(game: TradingGame) -> None:
    _pass_all(game)
    game.run_upkeep()
    game.start_cleanup()
    game.finish_cleanup()


def _to_projects(game: TradingGame) -> None:
    game.open_lot_creation()
    game.start_auctions()
    game.start_projects()


# --- Economy data ---


def test_profiles_match_spec_tables() -> None:
    # The original spec v0.1 economy is still reproducible from config.
    SLOTS = build_slots((4, 3, 2, 1), upkeep_size=4)
    assert SLOTS[0].production == {G: 4, L: 3, T: 2, I: 1}
    assert SLOTS[5].production == {O: 4, W: 3, S: 2, G: 1}
    assert set(SLOTS[0].upkeep) == {L, T, I, C}
    assert set(SLOTS[5].upkeep) == {W, S, G, L}
    for slot in SLOTS:
        assert sum(slot.production.values()) == 10
        # Three produced upkeep resources and exactly one never produced.
        assert sum(1 for r in slot.upkeep if slot.production.get(r, 0) == 0) == 1
    for r in RESOURCES:
        assert sum(s.production.get(r, 0) for s in SLOTS) == 10


def test_project_catalog_matches_cost_philosophy() -> None:
    assert len(MARKET_PROJECTS) == 32
    for card in MARKET_PROJECTS:
        assert sum(card.cost.values()) == 3
        assert 2 <= len(card.cost) <= 3
    for card in CITY_PROJECTS:
        if not card.vp:
            expected = 2 if card.id.startswith("small-") else 3
            assert sum(card.cost.values()) == expected, card.id
    tiers = {"small": (3, 3, 2, 3), "medium": (4, 5, 4, 5), "major": (6, 8, 6, 8)}
    for card in PRESTIGE_PROJECTS:
        lo, hi, tlo, thi = tiers[card.tier]
        assert lo <= sum(card.cost.values()) <= hi, card.id
        assert tlo <= len(card.cost) <= thi, card.id
    ids = [c.id for c in CITY_PROJECTS + MARKET_PROJECTS + PRESTIGE_PROJECTS]
    assert len(ids) == len(set(ids))


def test_non_prestige_vp_caps_and_grand_variants() -> None:
    for card in CITY_PROJECTS + MARKET_PROJECTS:
        assert card.vp <= MAX_NON_PRESTIGE_VP, card.id
    assert all(card.vp == 0 for card in MARKET_PROJECTS)
    by_id = {c.id: c for c in CITY_PROJECTS}
    for card in CITY_PROJECTS:
        if card.id.startswith("grand-"):
            continue
        assert card.vp == 0
        if card.id.startswith("small-"):
            assert f"grand-{card.id}" not in by_id  # the cheap option has no Grand version
            continue
        grand = by_id[f"grand-{card.id}"]
        assert grand.effect == card.effect
        assert grand.vp >= 1
        assert sum(grand.cost.values()) == sum(card.cost.values()) + 2
        assert len(grand.cost) == len(card.cost) + 2  # VP is paid for in diversity


# --- Setup ---


def test_city_selection_first_come_and_ai_fill() -> None:
    game = _game(3)
    game.claim_city("p0", 2)
    with pytest.raises(RuleError):
        game.claim_city("p1", 2)
    with pytest.raises(RuleError):
        game.claim_city("p0", 3)
    game.claim_city("p1", 5)
    assert not game.all_claimed()
    game.finish_city_selection()  # p2 never picked -> auto-assigned

    humans = game.human_cities()
    assert {c.owner_id for c in humans} == {"p0", "p1", "p2"}
    assert len([c for c in game.cities if c.is_ai]) == 5
    assert sorted(game.seat_order) == list(range(8))


def test_starting_state_and_round_one_production() -> None:
    game = _game(2)
    game.claim_city("p0", 0)
    game.claim_city("p1", 1)
    game.finish_city_selection()
    grain_city = game.cities[0]  # makes G2 L1 T1 I1; upkeep L T + Cloth (imported)
    assert grain_city.inventory == {L: 1, T: 1, C: 1}
    assert grain_city.cash == game.config.starting_cash

    game.start_round()
    assert grain_city.cash == game.config.starting_cash + game.config.income_per_round
    assert grain_city.inventory == {G: 2, L: 2, T: 2, I: 1, C: 1}


def test_priority_rotates_through_all_cities_by_default() -> None:
    game = _started(3)
    first = list(game.priority)
    assert sorted(first) == list(range(8))  # AI cities share the rotation
    _to_projects(game)
    _finish_round(game)
    game.start_round()
    assert game.priority == first[1:] + first[:1]


def test_after_humans_priority_mode() -> None:
    game = _started(3, ai_project_priority=AIProjectPriority.AFTER_HUMANS)
    humans = {c.index for c in game.human_cities()}
    first = list(game.priority)
    assert set(first[:3]) == humans and len(first) == 8
    _to_projects(game)
    _finish_round(game)
    game.start_round()
    assert game.priority[:3] == first[1:3] + first[:1]  # humans rotate among themselves


def test_every_city_gets_first_pick_once_in_eight_rounds() -> None:
    game = _game(2, ai_strategy=AIStrategyKind.PASSIVE)
    game.claim_city("p0", 0)
    game.claim_city("p1", 1)
    game.finish_city_selection()
    firsts = []
    for _ in range(8):
        game.start_round()
        firsts.append(game.priority[0])
        game.open_lot_creation()
        game.start_auctions()
        game.start_projects()
        _finish_round(game)
    assert sorted(firsts) == list(range(8))


# --- Lots & auctions ---


def test_lots_are_locked_and_hidden() -> None:
    game = _started(2)
    game.open_lot_creation()
    game.submit_lot("p0", {G: 2})
    assert game.cities[0].inventory.get(G, 0) == 0
    with pytest.raises(RuleError):
        game.submit_lot("p0", {G: 1})
    with pytest.raises(RuleError):
        game.submit_lot("p1", {G: 99})

    public = public_view(game, None, time.time())
    assert "grain" not in str(public["lots_ready"])
    assert public["lots_ready"] == [0]
    assert private_view(game, "p0")["lot"] == {"grain": 2}
    assert private_view(game, "p1")["lot"] is None


def test_auction_bidding_rules_and_resolution() -> None:
    game = _started(3)
    game.open_lot_creation()
    game.submit_lot("p0", {G: 2, L: 1})
    game.submit_lot("p1", {})
    game.submit_lot("p2", {})
    game.start_auctions()
    now = 1000.0
    auction = game.reveal_next_lot(now)
    assert auction.lot.seller == 0

    with pytest.raises(RuleError):
        game.place_bid(0, 5, now)  # seller can't bid
    with pytest.raises(RuleError):
        game.place_bid(1, 0, now)  # below minimum
    game.place_bid(1, 3, now)
    with pytest.raises(RuleError):
        game.place_bid(2, 3, now)  # must exceed high bid
    with pytest.raises(RuleError):
        game.place_bid(1, 4, now)  # already high bidder
    cash = game.config.starting_cash + game.config.income_per_round
    with pytest.raises(RuleError):
        game.place_bid(2, cash + 1, now)  # more than they have
    game.place_bid(2, 8, now)

    record = game.resolve_auction()
    assert record.winner == 2 and record.price == 8
    assert game.cities[2].cash == cash - 8
    assert game.cities[0].cash == cash + 8
    assert game.cities[2].inventory[G] >= 2


def test_unsold_lot_returns_to_seller() -> None:
    game = _started(2)
    game.open_lot_creation()
    before = dict(game.cities[0].inventory)
    game.submit_lot("p0", {G: 2})
    game.start_auctions()
    game.reveal_next_lot(0.0)
    record = game.resolve_auction()
    assert record.winner is None
    assert game.cities[0].inventory == before
    assert game.cities[0].cash == game.config.starting_cash + game.config.income_per_round


def test_anti_sniping_extends_timer() -> None:
    game = _started(3, auction_seconds=20)
    game.open_lot_creation()
    game.submit_lot("p0", {G: 1})
    game.start_auctions()
    auction = game.reveal_next_lot(0.0)
    game.place_bid(1, 2, 10.0)  # 10s left: no extension
    assert auction.ends_at == 20.0
    game.place_bid(2, 3, 16.0)  # 4s left: +5
    assert auction.ends_at == 25.0
    game.place_bid(1, 4, 24.5)  # 0.5s left: +5 again
    assert auction.ends_at == 30.0
    with pytest.raises(RuleError):
        game.place_bid(2, 5, 30.0)  # closed


def test_auction_settles_when_nobody_else_can_act() -> None:
    game = _started(3)
    game.open_lot_creation()
    game.submit_lot("p0", {G: 1})
    game.start_auctions()
    game.reveal_next_lot(0.0)
    assert not game.auction_settled()
    game.place_bid(1, 2, 1.0)
    assert not game.auction_settled()  # p2 can still outbid
    game.pass_auction(2, 2.0)
    assert game.auction_settled()


def test_purchased_resources_cannot_be_resold_same_round() -> None:
    game = _started(2)
    game.open_lot_creation()
    game.submit_lot("p0", {G: 1})
    game.start_auctions()
    with pytest.raises(RuleError):
        game.submit_lot("p1", {G: 1})


# --- Projects ---


def test_build_city_project_consumes_and_applies() -> None:
    game = _started(2)
    idx = _card(game, "sawmill")  # 3 Timber + 1 Tools -> +1 Timber
    _to_projects(game)
    actor = game.current_project_player()
    other = next(p for p in game.players if p != actor)
    with pytest.raises(RuleError):
        game.build_project(other, idx)  # not their turn
    city = game.city_of(actor)
    city.add(game.project_slots[idx].cost)
    timber_before = game.production_for(city).get(T, 0)
    game.build_project(actor, idx)
    assert game.project_slots[idx] is None
    assert game.production_for(city).get(T, 0) == timber_before + 1
    # One project per round: turn moved on.
    assert game.current_project_player() == other


def test_empty_slots_refill_next_round_only() -> None:
    game = _started(2)
    idx = _card(game, "market-square")
    _to_projects(game)
    actor = game.current_project_player()
    game.city_of(actor).add(game.project_slots[idx].cost)
    game.build_project(actor, idx)
    game.pass_project(game.current_project_player())
    assert game.project_slots[idx] is None
    game.run_upkeep()
    game.start_cleanup()
    game.finish_cleanup()
    game.start_round()
    assert game.project_slots[idx] is not None


def test_market_projects_replace_slot_and_respect_production_floor() -> None:
    game = _started(2)
    # Grain city (slot 0) produces 1 Iron, Iron city (slot 3, AI) produces 4.
    idx = _card(game, "iron-supply-down")
    _to_projects(game)
    actor = game.current_project_player()
    city = game.city_of(actor)
    city.add({r: 5 for r in RESOURCES})
    game.build_project(actor, idx)
    assert game.market_level(I, MarketAxis.SUPPLY) == MarketLevel.DOWN
    assert I not in game.production_for(game.cities[0])  # 1 - 1 = 0
    assert game.production_for(game.cities[3])[I] == 1  # Iron city: 2 - 1
    # A non-producer never gains production from Supply Up.
    game.market[I][MarketAxis.SUPPLY].level = MarketLevel.UP
    assert I not in game.production_for(game.cities[7])  # Spices city: 0 Iron


def test_displaced_market_card_policy() -> None:
    for policy, in_pool in ((DisplacedCardPolicy.DISCARD, False), (DisplacedCardPolicy.RETURN_TO_POOL, True)):
        game = _started(2, displaced_market_card=policy)
        _to_projects(game)
        for pid in game.players:
            game.city_of(pid).add({r: 5 for r in RESOURCES})
        _card(game, "iron-supply-down")
        game.build_project(game.current_project_player(), 0)
        _card(game, "iron-supply-up")
        game.build_project(game.current_project_player(), 0)
        assert game.market_level(I, MarketAxis.SUPPLY) == MarketLevel.UP
        pool_ids = {c.id for c in game.decks["market"]}
        assert ("iron-supply-down" in pool_ids) == in_pool
        assert ("iron-supply-down" in {c.id for c in game.discarded_cards}) == (not in_pool)


def test_demand_modifier_timing() -> None:
    for timing, expected in ((EffectTiming.IMMEDIATE, 2), (EffectTiming.NEXT_ROUND, 1)):
        game = _started(2, upkeep_effect_timing=timing)
        _to_projects(game)
        actor = game.current_project_player()
        game.city_of(actor).add({r: 5 for r in RESOURCES})
        _card(game, "cloth-demand-up")
        game.build_project(actor, 0)
        grain_city = game.cities[0]  # needs 1 Cloth
        assert game.upkeep_for(grain_city)[C] == expected


# --- Upkeep, shortages, storage ---


def test_shortage_accumulates_penalises_primary_and_clears() -> None:
    game = _started(2)
    city = game.cities[0]  # Grain: needs L, T, I, C; makes no Cloth
    city.remove({C: city.inventory.get(C, 0)})
    _to_projects(game)
    _pass_all(game)
    result = game.run_upkeep()[0]
    assert result.missing == 1 and city.shortage == 1

    game.start_cleanup()
    game.finish_cleanup()
    game.start_round()
    assert game.last_production[0][G] == 1  # 2 - 1 shortage

    city.add({C: 1})
    _to_projects(game)
    _pass_all(game)
    game.run_upkeep()
    assert city.shortage == 0


def test_storage_enforced_only_at_cleanup() -> None:
    game = _started(2, storage_capacity=10)
    city = game.cities[0]
    city.add({G: 10})
    _to_projects(game)
    _pass_all(game)
    game.run_upkeep()
    pending = game.start_cleanup()
    excess = pending[0]
    assert excess == sum(city.inventory.values()) - 10
    with pytest.raises(RuleError):
        game.discard("p0", {G: excess + 1})
    game.discard("p0", {G: excess})
    assert sum(city.inventory.values()) == 10


def test_storage_can_be_disabled() -> None:
    game = _started(2, storage_capacity=None)
    game.cities[0].add({G: 50})
    _to_projects(game)
    _pass_all(game)
    game.run_upkeep()
    assert game.start_cleanup() == {}


def test_full_game_reaches_finished_with_standings() -> None:
    game = _game(2, total_rounds=3)
    game.claim_city("p0", 0)
    game.claim_city("p1", 4)
    game.finish_city_selection()
    for _ in range(3):
        game.start_round()
        game.open_lot_creation()
        game.start_auctions()
        game.start_projects()
        _pass_all(game)
        game.run_upkeep()
        game.start_cleanup()
        game.finish_cleanup()
    assert game.phase == Phase.FINISHED
    assert [c.owner_id for c in game.standings()] and len(game.standings()) == 2
    with pytest.raises(RuleError):
        game.start_round()


def test_private_view_hides_other_inventories() -> None:
    game = _started(2)
    public = public_view(game, None, time.time())
    assert "inventory" not in public["cities"][0]
    assert private_view(game, "p0")["inventory"]
    assert private_view(game, "p1")["slot"] == 1


# --- API ---


def _cancel_room_tasks() -> None:
    for room in list(store._rooms.values()):
        if room.game_task:
            room.game_task.cancel()


def setup_function() -> None:
    _cancel_room_tasks()
    store._rooms.clear()


def teardown_function() -> None:
    _cancel_room_tasks()
    store._rooms.clear()


def test_api_start_claim_and_lot() -> None:
    client = TestClient(app)
    res = client.post("/api/tc/games", json={"host_name": "Host"}).json()
    code, host_id = res["code"], res["host_id"]
    ids = [
        client.post(f"/api/tc/games/{code}/join", json={"player_name": n}).json()["player_id"]
        for n in ("Ana", "Ben")
    ]
    assert client.post(f"/api/tc/games/{code}/start", headers={"X-Player-Id": ids[0]}).status_code == 403
    assert client.post(f"/api/tc/games/{code}/start", headers={"X-Player-Id": host_id}).status_code == 200

    room = store.get_room(code)
    # Drive the engine directly instead of the timed loop.
    if room.game_task:
        room.game_task.cancel()
    game = room.game

    r = client.post(f"/api/tc/games/{code}/claim", json={"slot": 3}, headers={"X-Player-Id": ids[0]})
    assert r.status_code == 200
    r = client.post(f"/api/tc/games/{code}/claim", json={"slot": 3}, headers={"X-Player-Id": ids[1]})
    assert r.status_code == 400
    client.post(f"/api/tc/games/{code}/claim", json={"slot": 6}, headers={"X-Player-Id": ids[1]})

    game.finish_city_selection()
    game.start_round()
    game.open_lot_creation()
    r = client.post(
        f"/api/tc/games/{code}/lot",
        json={"contents": {"iron": 2}},
        headers={"X-Player-Id": ids[0]},
    )
    assert r.status_code == 200, r.text

    state = client.get(f"/api/tc/games/{code}/state", headers={"X-Player-Id": ids[0]}).json()
    assert state["private"]["lot"] == {"iron": 2}
    host_state = client.get(f"/api/tc/games/{code}/state", headers={"X-Player-Id": host_id}).json()
    assert host_state["private"] is None
    assert host_state["public"]["lots_ready"] == [3]


def test_existing_games_still_mounted() -> None:
    client = TestClient(app)
    for prefix in ("mm", "fq", "ww", "pd", "ba", "tc"):
        res = client.post(f"/api/{prefix}/games", json={"host_name": "Host"})
        assert res.status_code == 200, prefix


@pytest.mark.asyncio
async def test_game_loop_runs_to_completion_with_fast_timers() -> None:
    from app.shared.models import GamePhase
    from app.trading_city.routes.game import _run_game

    fast = dataclasses.replace(
        DEFAULT_CONFIG,
        total_rounds=2,
        city_selection_seconds=0,
        lot_creation_seconds=0,
        auction_seconds=0.05,
        project_turn_seconds=0,
        discard_seconds=0,
        production_display_seconds=0,
        lot_result_display_seconds=0,
        upkeep_display_seconds=0,
        anti_snipe_extension_seconds=0.01,
    )
    room = store.create_room()
    room.players = []
    room.game = TradingGame([("p0", "A"), ("p1", "B")], config=fast, rng=random.Random(1))
    room.phase = GamePhase.PLAYING
    # Nobody acts: every phase advances on its timer.
    await _run_game(room)
    assert room.phase == GamePhase.FINISHED
    assert room.game.phase == Phase.FINISHED
    assert room.game.round == 2


# --- AI ---


def _ai_game(**overrides) -> TradingGame:
    overrides.setdefault("ai_strategy", AIStrategyKind.HEURISTIC)
    return _started(2, **overrides)


def test_what_if_helpers_do_not_mutate_state() -> None:
    game = _started(2)
    iron_city = game.cities[3]
    before = game.production_for(iron_city)
    what_if = game.production_for(iron_city, market_override=(I, MarketAxis.SUPPLY, MarketLevel.DOWN))
    assert what_if[I] == before[I] - 1
    assert game.market_level(I, MarketAxis.SUPPLY) == MarketLevel.NEUTRAL
    assert game.production_for(iron_city) == before


def test_ai_lot_keeps_upkeep_target_and_import_spare() -> None:
    game = _ai_game()
    slot = 2  # Timber AI: makes T4 I3 C2 O1, upkeep I C O W (imports Wine)
    strategy = game.strategies[slot]
    game.cities[slot].inventory = {T: 6, I: 4, C: 3, O: 2, W: 2}
    lot = strategy.choose_lot(game, slot) or {}
    keep = strategy._reserve(game, game.cities[slot])
    for r, n in game.cities[slot].inventory.items():
        assert n - lot.get(r, 0) >= min(n, keep.get(r, 0))
    assert lot.get(W, 0) == 0  # 2 Wine = upkeep 1 + spare 1


def _reveal(game: TradingGame, seller: int, contents: dict) -> Auction:
    game.phase = Phase.AUCTION
    game.auction = Auction(lot=Lot(id=99, seller=seller, contents=contents), ends_at=1e12)
    return game.auction


def test_ai_bids_for_upkeep_gap_and_drops_worthless_lots() -> None:
    game = _ai_game()
    slot = 2  # Timber AI imports Wine
    city, strategy = game.cities[slot], game.strategies[slot]
    city.inventory = {}
    strategy.target_id = None
    auction = _reveal(game, seller=5, contents={W: 1})
    assert strategy.choose_bid(game, slot) == game.config.min_bid
    auction.bids.append(Bid(bidder=6, amount=50, at=0))  # priced far above its worth
    assert strategy.choose_bid(game, slot) is None


def test_ai_never_bids_into_cash_reserve() -> None:
    game = _ai_game()
    slot = 2
    game.cities[slot].cash = 3
    _reveal(game, seller=5, contents={r: 3 for r in RESOURCES})
    assert game.strategies[slot].choose_bid(game, slot) is None


def test_ai_auction_step_drops_uninterested_ai_so_lot_settles() -> None:
    game = _ai_game()
    _reveal(game, seller=0, contents={})  # an empty lot is worth nothing to anyone
    game.auction.passed.add(1)  # the other human is out
    assert game.run_ai_auction_step(0.0) is False
    assert game.auction_settled()


def test_market_targeting_prefers_hurting_others_not_itself() -> None:
    game = _ai_game()
    strategy = HeuristicStrategy()
    by_id = {c.id: c for c in MARKET_PROJECTS}
    wine_city, spices_city, iron_city = game.cities[6], game.cities[7], game.cities[3]
    iron_down = by_id["iron-supply-down"]
    # Wine city neither makes nor needs Iron: squeezing Iron producers is a pure win.
    assert strategy.project_worth(game, wine_city, iron_down, 5) > 0
    # Spices city must import Iron: it won't choke its own supply.
    assert strategy.project_worth(game, spices_city, iron_down, 5) <= 0
    # Iron city never cuts its own main export.
    assert strategy.project_worth(game, iron_city, iron_down, 5) <= 0
    # Supply Up on your main export helps you.
    assert strategy.project_worth(game, iron_city, by_id["iron-supply-up"], 5) > 0


def test_ai_target_is_sticky_and_replaced_when_taken() -> None:
    game = _ai_game()
    slot = next(c.index for c in game.cities if c.is_ai)
    strategy = game.strategies[slot]
    game.open_lot_creation()
    target = strategy.target_id
    if target is None:
        pytest.skip("no viable target on this board")
    strategy._update_target(game, game.cities[slot])
    assert strategy.target_id == target
    index = strategy._target_index(game)
    game.project_slots[index] = None  # someone else built it
    strategy._update_target(game, game.cities[slot])
    assert strategy.target_id != target


def test_heuristic_ai_trades_and_builds_over_a_full_game() -> None:
    game = _game(2, ai_strategy=AIStrategyKind.HEURISTIC, total_rounds=8)
    game.claim_city("p0", 0)
    game.claim_city("p1", 4)
    game.finish_city_selection()
    now = 0.0
    for _ in range(8):
        game.start_round()
        game.open_lot_creation()
        game.start_auctions()
        while game.reveal_next_lot(now) is not None:
            for _ in range(200):
                if not game.run_ai_auction_step(now):
                    break
            game.auction.passed.update(c.index for c in game.human_cities())
            assert game.auction_settled()
            game.resolve_auction()
        game.start_projects()
        _finish_round(game)  # humans always pass; AI turns resolve automatically
    assert game.phase == Phase.FINISHED
    ai_slots = {c.index for c in game.cities if c.is_ai}
    sold = [h for h in game.history if h.seller in ai_slots]
    bought = [h for h in game.history if h.winner in ai_slots]
    built = [e for e in game.project_log if e.city in ai_slots]
    assert sold and bought and built
    assert all(c.cash >= 0 for c in game.cities)


@pytest.mark.asyncio
async def test_busy_room_cannot_starve_ai_bidders() -> None:
    import asyncio

    from app.shared.models import GamePhase
    from app.trading_city.routes.game import _run_auctions

    cfg = dataclasses.replace(
        DEFAULT_CONFIG, auction_seconds=5, ai_bid_delay_seconds=0.1, lot_result_display_seconds=0
    )
    room = store.create_room()
    room.game = TradingGame([("p0", "A"), ("p1", "B")], config=cfg, rng=random.Random(3))
    room.phase = GamePhase.PLAYING
    game = room.game
    game.claim_city("p0", 0)
    game.claim_city("p1", 4)
    game.finish_city_selection()
    game.start_round()
    game.open_lot_creation()
    for pid in ("p0", "p1"):
        game.submit_lot(pid, {})

    async def humans_out_and_noisy() -> None:
        # Humans drop out of each lot, then keep poking the room.
        while True:
            if game.auction:
                game.auction.passed.update({0, 4})
            room.changed.set()
            await asyncio.sleep(0.05)

    noise = asyncio.create_task(humans_out_and_noisy())
    started = time.time()
    try:
        await _run_auctions(room, game)
    finally:
        noise.cancel()
    assert game.history and any(h.bids for h in game.history)
    # Every lot closed early instead of running its full 5s timer.
    assert time.time() - started < cfg.auction_seconds * len(game.history)


# --- Cash costs & cash scoring ---


def test_only_prestige_projects_cost_cash() -> None:
    game = _started(2)
    by_id = {c.id: c for c in CITY_PROJECTS + MARKET_PROJECTS + PRESTIGE_PROJECTS}
    assert game.cash_cost(by_id["cathedral"]) == 2 * by_id["cathedral"].vp  # $2 per VP
    assert game.cash_cost(by_id["sawmill"]) == 0
    assert game.cash_cost(by_id["grand-warehouse"]) == 0  # scores, but isn't Prestige
    assert game.cash_cost(by_id["iron-supply-down"]) == 0

    idx = _card(game, "feast-hall")
    price = game.cash_cost(by_id["feast-hall"])
    _to_projects(game)
    actor = game.current_project_player()
    city = game.city_of(actor)
    city.add(by_id["feast-hall"].cost)
    cash = city.cash
    game.build_project(actor, idx)
    assert city.cash == cash - price
    assert city.vp == by_id["feast-hall"].vp


def test_vp_project_blocked_without_cash_even_with_resources() -> None:
    game = _started(2)
    idx = _card(game, "cathedral")
    _to_projects(game)
    actor = game.current_project_player()
    city = game.city_of(actor)
    city.add(game.project_slots[idx].cost)
    price = game.cash_cost(game.project_slots[idx])
    city.cash = price - 1
    assert not game.can_afford(city, game.project_slots[idx])
    with pytest.raises(RuleError, match=rf"\${price}"):
        game.build_project(actor, idx)
    assert game.project_slots[idx] is not None  # nothing consumed


def test_leftover_cash_scores_at_configured_rate() -> None:
    game = _started(2, cash_per_vp=8)
    city = game.cities[0]
    city.cash = 23
    assert game.score_for(city) == city.vp + 2
    off = _started(2, cash_per_vp=None)
    off.cities[0].cash = 23
    assert off.score_for(off.cities[0]) == off.cities[0].vp


def test_grand_city_cards_only_appear_from_configured_round() -> None:
    game = _game(2, grand_city_from_round=4)
    game.claim_city("p0", 0)
    game.claim_city("p1", 1)
    game.finish_city_selection()
    city_slots = [i for i, cat in enumerate(game.config.project_slot_mix) if cat == "city"]
    for round_number in range(1, 9):
        # Empty the City slots each round so they are redrawn.
        for i in city_slots:
            game.project_slots[i] = None
        game.start_round()
        drawn = [game.project_slots[i] for i in city_slots if game.project_slots[i]]
        if round_number < 4:
            assert all(c.vp == 0 for c in drawn)
            assert all(c.vp == 0 for c in game.decks["city"])
        else:
            assert any(c.vp > 0 for c in game.decks["city"] + drawn)
        game.open_lot_creation()
        game.start_auctions()
        game.start_projects()
        _finish_round(game)


@pytest.mark.asyncio
async def test_summary_screen_advances_once_everyone_continues() -> None:
    import asyncio

    from app.shared.game_state import Player
    from app.shared.models import GamePhase
    from app.trading_city.routes.game import _summary

    room = store.create_room()
    room.players = [Player(id="p0", name="A"), Player(id="p1", name="B")]
    room.game = _started(2)
    room.phase = GamePhase.PLAYING

    async def players_continue() -> None:
        await asyncio.sleep(0.05)
        for pid in ("p0", "p1"):
            room.ready.add(pid)
            room.changed.set()

    started = time.time()
    await asyncio.gather(_summary(room, 30), players_continue())
    assert time.time() - started < 5  # didn't wait for the 30s timer
    assert room.ready is None and room.deadline is None


def test_ready_rejected_outside_summary_screens() -> None:
    client = TestClient(app)
    res = client.post("/api/tc/games", json={"host_name": "Host"}).json()
    code, host_id = res["code"], res["host_id"]
    pid = client.post(f"/api/tc/games/{code}/join", json={"player_name": "Ana"}).json()["player_id"]
    client.post(f"/api/tc/games/{code}/join", json={"player_name": "Ben"})
    client.post(f"/api/tc/games/{code}/start", headers={"X-Player-Id": host_id})
    r = client.post(f"/api/tc/games/{code}/ready", headers={"X-Player-Id": pid})
    assert r.status_code == 400  # city selection isn't a summary screen


def test_cleanup_preview_reflects_next_round_effects() -> None:
    # A Demand Up built with NEXT_ROUND timing doesn't count this round but shows in the preview.
    game = _started(2, upkeep_effect_timing=EffectTiming.NEXT_ROUND)
    _to_projects(game)
    actor = game.current_project_player()
    game.city_of(actor).add({r: 5 for r in RESOURCES})
    _card(game, "cloth-demand-up")
    game.build_project(actor, 0)
    grain_city = game.cities[0]  # needs Cloth
    assert game.upkeep_for(grain_city)[C] == 1
    assert game.upkeep_for(grain_city, at_round=game.round + 1)[C] == 2
    view = private_view(game, "p0")
    assert view["next_upkeep"]["cloth"] == 2
    assert view["next_production"] == {r.value: n for r, n in game.production_for(grain_city).items()}


# --- Narration ---


async def _run_fast_game_capturing_sounds(monkeypatch, skip_after: str | None = None) -> list[str]:
    from app.shared.models import GamePhase
    from app.trading_city.routes import game as routes

    sounds: list[str] = []
    room = store.create_room()

    async def fake_broadcast(_room, event, data, exclude=None):
        if event == "intro_narration":
            sounds.append(data["sound"])
            if data["sound"] == skip_after:
                room.skip_intro.set()

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(routes, "broadcast", fake_broadcast)
    monkeypatch.setattr(routes.asyncio, "sleep", no_sleep)
    fast = dataclasses.replace(
        DEFAULT_CONFIG,
        total_rounds=2,
        storage_capacity=0,  # force a Cleanup discard so its explanation plays
        city_selection_seconds=0,
        lot_creation_seconds=0,
        auction_seconds=0.01,
        project_turn_seconds=0,
        discard_seconds=0,
        production_display_seconds=0,
        lot_result_display_seconds=0,
        upkeep_display_seconds=0,
        ai_bid_delay_seconds=0,
        anti_snipe_extension_seconds=0.01,  # every bid is "late" with a 0.01s timer
    )
    room.game = TradingGame([("p0", "A"), ("p1", "B")], config=fast, rng=random.Random(1))
    room.phase = GamePhase.PLAYING
    await routes._run_game(room)
    assert room.phase == GamePhase.FINISHED
    return sounds


@pytest.mark.asyncio
async def test_narration_intro_then_each_phase_explained_once(monkeypatch) -> None:
    from app.trading_city.routes.game import INTRO, TUTORIAL

    sounds = await _run_fast_game_capturing_sounds(monkeypatch)
    assert sounds[: len(INTRO)] == [s for _, s in INTRO]
    for lines in TUTORIAL.values():
        for _, sound in lines:
            assert sounds.count(sound) == 1, sound
    assert sounds.count("tc-final-round.mp3") == 1
    assert sounds[-1] == "tc-game-over.mp3"


@pytest.mark.asyncio
async def test_skipping_intro_skips_tutorial_but_not_milestones(monkeypatch) -> None:
    sounds = await _run_fast_game_capturing_sounds(monkeypatch, skip_after="tc-welcome.mp3")
    assert sounds == ["tc-welcome.mp3", "tc-final-round.mp3", "tc-game-over.mp3"]


def test_every_narration_file_exists() -> None:
    from pathlib import Path

    from app.trading_city.routes.game import FINAL_ROUND, GAME_OVER, INTRO, TUTORIAL

    audio = Path(__file__).resolve().parents[2] / "frontend" / "public" / "trading-city" / "audio"
    lines = INTRO + [FINAL_ROUND, GAME_OVER] + [line for ls in TUTORIAL.values() for line in ls]
    missing = [sound for _, sound in lines if not (audio / sound).is_file()]
    assert not missing, missing


def test_smaller_economy_keeps_structure() -> None:
    from app.trading_city.economy import build_slots

    slots = build_slots((2, 1, 1, 1), upkeep_size=3)
    assert slots[0].production == {G: 2, L: 1, T: 1, I: 1}
    assert slots[0].upkeep == {L: 1, T: 1, C: 1}  # two it makes + Cloth it never makes
    for slot in slots:
        assert sum(slot.production.values()) == 5
        assert sum(slot.upkeep.values()) == 3
        assert slot.primary_resource not in slot.upkeep  # main export always sellable
        assert sum(1 for r in slot.upkeep if r not in slot.production) == 1
    for r in RESOURCES:
        assert sum(s.production.get(r, 0) for s in slots) == 5
        assert sum(1 for s in slots if r in s.upkeep) == 3
    game = _started(2, production_pattern=(2, 1, 1, 1), upkeep_size=3)
    assert game.last_production[0] == {G: 2, L: 1, T: 1, I: 1}


def test_city_view_lists_market_projects_and_whether_still_active() -> None:
    game = _started(2)
    _to_projects(game)
    first, second = game.current_project_player(), None
    for pid in game.players:
        game.city_of(pid).add({r: 5 for r in RESOURCES})
    _card(game, "iron-supply-down")
    game.build_project(first, 0)
    second = game.current_project_player()
    _card(game, "iron-supply-up")
    game.build_project(second, 0)

    cities = public_view(game, None, time.time())["cities"]
    built_first = cities[game.city_of(first).index]["market_projects"]
    built_second = cities[game.city_of(second).index]["market_projects"]
    assert [p["id"] for p in built_first] == ["iron-supply-down"] and not built_first[0]["active"]
    assert [p["id"] for p in built_second] == ["iron-supply-up"] and built_second[0]["active"]


@pytest.mark.parametrize("split", ["even", "gentle", "strong"])
def test_generated_catalog_spreads_demand_evenly(split: str) -> None:
    from app.trading_city.projects import BASIC, RESOURCE_SPLITS, build_catalog

    city, _, prestige = build_catalog(split)
    shares = RESOURCE_SPLITS[split]
    groups = {
        "city": [c for c in city if not c.vp],
        "grand": [c for c in city if c.vp],
        **{tier: [c for c in prestige if c.tier == tier] for tier in ("small", "medium", "major")},
    }
    for name, cards in groups.items():
        units = Counter()
        for card in cards:
            units.update(card.cost)
        total = sum(units.values())
        # A card needing k > 4 resource types must use at least k - 4 basic ones, so
        # very diverse cards (major Prestige) can't go below this basic share.
        basic_floor = sum(max(0, len(c.cost) - 4) for c in cards)
        basic_total = max(total * shares[name], basic_floor)
        for r in RESOURCES:
            expected = (basic_total if r in BASIC else total - basic_total) / 4
            assert abs(units[r] - expected) <= 1.5, (split, name, r.value, units[r], expected)
    # Shapes, effects and VP are preserved from the hand-written cards.
    handwritten, _, hw_prestige = build_catalog("handwritten")
    for new, old in zip(city + prestige, handwritten + hw_prestige):
        assert (new.id, new.vp, new.effect) == (old.id, old.vp, old.effect)
        assert sorted(new.cost.values()) == sorted(old.cost.values()) or new.id.startswith("grand-")


def test_storage_cards() -> None:
    storage = {c.name: c for c in CITY_PROJECTS if c.effect.kind.value == "storage"}
    for name in ("Warehouse", "Granary", "Depot"):
        assert storage[name].effect.amount == 5 and sum(storage[name].cost.values()) == 3
        assert storage[f"Grand {name}"].effect.amount == 5 and storage[f"Grand {name}"].vp == 1
    for name in ("Warehouse", "Cellar", "Granary", "Barn", "Depot"):
        small = storage[f"Small {name}"]
        assert small.effect.amount == 3 and sum(small.cost.values()) == 2 and len(small.cost) == 2
    assert "Cellar" not in storage and "Barn" not in storage and "Deep Cellars" not in storage
    assert len(storage) == 11  # 3 regular + 3 Grand + 5 Small


def test_small_storage_shows_early_then_retires() -> None:
    game = _game(2, small_city_until_round=4)
    game.claim_city("p0", 0)
    game.claim_city("p1", 1)
    game.finish_city_selection()
    city_slots = [i for i, cat in enumerate(game.config.project_slot_mix) if cat == "city"]
    assert len(game.project_slots) == 12 and len(city_slots) == 5
    seen_small_early = False
    for round_number in range(1, 7):
        game.start_round()
        board = [game.project_slots[i] for i in city_slots]
        small_now = [c for c in board if c and c.id.startswith("small-")]
        if round_number < 4:
            seen_small_early |= bool(small_now)
        else:
            assert not small_now
            assert not any(c.id.startswith("small-") for c in game.decks["city"])
        for i in city_slots:  # empty the City slots so they redraw next round
            game.project_slots[i] = None
        game.open_lot_creation()
        game.start_auctions()
        game.start_projects()
        _finish_round(game)
    assert seen_small_early


def test_ai_falls_back_to_affordable_card_using_only_spare_goods() -> None:
    game = _ai_game()
    slot = 2
    city, strategy = game.cities[slot], game.strategies[slot]
    by_id = {c.id: c for c in CITY_PROJECTS + PRESTIGE_PROJECTS}
    target, small = by_id["grand-exhibition"], by_id["small-granary"]
    game.project_slots = [None] * len(game.project_slots)
    game.project_slots[0], game.project_slots[1] = target, small
    strategy.target_id = target.id  # far out of reach
    upkeep = game.upkeep_for(city)

    # Only the goods reserved for upkeep/target: nothing spare -> pass.
    city.inventory = dict(upkeep)
    assert strategy.choose_project(game, slot) is None

    # Spare goods that cover the Small card (and aren't needed elsewhere) -> build it.
    spare = {r: n for r, n in small.cost.items()}
    city.inventory = {r: upkeep.get(r, 0) + target.cost.get(r, 0) + spare.get(r, 0) + 1 for r in RESOURCES}
    assert strategy.choose_project(game, slot) == 1


def test_market_study_sits_between_production_and_lots() -> None:
    game = _started(2)
    with pytest.raises(RuleError):
        game.start_auctions()  # nothing to do during production
    game.open_market_study()
    assert game.phase == Phase.MARKET_STUDY
    with pytest.raises(RuleError):
        game.submit_lot("p0", {G: 1})  # no lots while studying
    game.open_lot_creation()
    assert game.phase == Phase.LOT_CREATION
