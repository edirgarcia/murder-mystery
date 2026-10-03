"""Public / private projections of game state (spec §50).

This is the only place that decides what clients may see. Public state goes
to everyone (including the host dashboard); exact inventories and unrevealed
lot contents only ever appear in a player's own private view.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .engine import AuctionRecord, City, Phase, RuleError, TradingGame, UpkeepResult
from .economy import Resource
from .projects import MarketAxis, ProjectCard, ProjectCategory


def iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _bundle(bundle: dict[Resource, int]) -> dict[str, int]:
    return {r.value: n for r, n in bundle.items()}


def _card(game: TradingGame, card: ProjectCard) -> dict:
    return {**card.to_dict(), "cash_cost": game.cash_cost(card)}


def _city_view(game: TradingGame, city: City) -> dict:
    started = game.phase != Phase.CITY_SELECTION
    return {
        "slot": city.index,
        "profile": city.slot.profile,
        "name": city.name if started else city.slot.city_name,
        "city_name": city.slot.city_name,
        "ai_city_name": city.slot.ai_city_name,
        "owner_id": city.owner_id,
        "owner_name": city.owner_name,
        "is_ai": started and city.is_ai,
        "primary_resource": city.slot.primary_resource.value,
        "base_production": _bundle(city.slot.production),
        "base_upkeep": _bundle(city.slot.upkeep),
        "production": _bundle(game.production_for(city)),
        "upkeep": _bundle(game.upkeep_for(city)),
        "income": game.income_for(city),
        "storage": game.storage_for(city),
        "cash": city.cash,
        "shortage": city.shortage,
        "vp": city.vp,
        "score": game.score_for(city),
        "projects": [
            {**_card(game, p.card), "round_built": p.round_built} for p in city.projects
        ],
        # Market projects live on the global board; listed here so each city's builds are complete.
        "market_projects": [
            {
                **_card(game, e.card),
                "round_built": e.round,
                "active": game.market[e.card.effect.resource][e.card.effect.axis].card is e.card,
            }
            for e in game.project_log
            if e.city == city.index and e.card.category == ProjectCategory.MARKET
        ],
    }


def _record_view(record: AuctionRecord) -> dict:
    return {
        "round": record.round,
        "lot_id": record.lot_id,
        "seller": record.seller,
        "contents": _bundle(record.contents),
        "winner": record.winner,
        "price": record.price,
        "bids": [{"bidder": b.bidder, "amount": b.amount} for b in record.bids],
    }


def _public_upkeep(result: UpkeepResult) -> dict:
    return {
        "missing": result.missing,
        "shortage_before": result.shortage_before,
        "shortage_after": result.shortage_after,
    }


def public_view(
    game: TradingGame, deadline: float | None, now: float, ready: set[str] | None = None
) -> dict:
    auction = None
    if game.auction is not None:
        a = game.auction
        high = a.high_bid
        auction = {
            "lot_id": a.lot.id,
            "number": game.auctions_total - len(game.auction_queue),
            "total": game.auctions_total,
            "seller": a.lot.seller,
            "contents": _bundle(a.lot.contents),
            "high_bid": high.amount if high else None,
            "high_bidder": high.bidder if high else None,
            "min_next_bid": game.min_next_bid(),
            "ends_at": iso(a.ends_at),
            "bids": [{"bidder": b.bidder, "amount": b.amount} for b in a.bids],
            "passed": sorted(a.passed),
        }

    return {
        "phase": game.phase.value,
        "round": game.round,
        "total_rounds": game.config.total_rounds,
        "deadline": iso(deadline),
        # Slots that tapped Continue on a summary screen; None when not on one.
        "ready": None if ready is None else sorted(game.city_of(p).index for p in ready),
        "server_time": iso(now),
        "cities": [_city_view(game, c) for c in game.cities],
        "priority": [
            {
                "slot": slot,
                "player_id": game.cities[slot].owner_id,
                "name": game.cities[slot].owner_name or game.cities[slot].name,
                "is_ai": game.cities[slot].is_ai,
            }
            for slot in game.priority
        ],
        "project_turn_slot": game.current_project_slot(),
        "project_turn_player": game.current_project_player(),
        "project_actions": game.project_actions,
        "project_slots": [
            {"index": i, "category": category, "card": _card(game, card) if card else None}
            for i, (category, card) in enumerate(
                zip(game.config.project_slot_mix, game.project_slots)
            )
        ],
        "prestige_tier": game.prestige_tier(),
        "market": {
            r.value: {
                axis.value: {
                    "level": game.market_level(r, axis).value,
                    "pending_level": slots[axis].level.value,
                    "card_name": slots[axis].card.name if slots[axis].card else None,
                    "built_by": slots[axis].built_by,
                }
                for axis in MarketAxis
            }
            for r, slots in game.market.items()
        },
        "lots_ready": sorted(
            c.index for c in game.cities if not c.is_ai and c.index in game.lots
        )
        if game.phase == Phase.LOT_CREATION
        else [],
        "auction": auction,
        "history": [_record_view(r) for r in game.history],
        "project_log": [
            {
                "round": e.round,
                "city": e.city,
                "card": _card(game, e.card),
                "displaced": e.displaced.name if e.displaced else None,
            }
            for e in game.project_log
        ],
        "last_production": {
            slot: _bundle(p) for slot, p in game.last_production.items()
        },
        "last_upkeep": {slot: _public_upkeep(u) for slot, u in game.last_upkeep.items()},
        "discards_pending": len(game.pending_discards),
        "standings": [
            {"slot": c.index, "owner_name": c.owner_name, "score": game.score_for(c), "vp": c.vp, "cash": c.cash}
            for c in game.standings()
        ]
        if game.phase == Phase.FINISHED
        else [],
        "rules": {
            "min_bid": game.config.min_bid,
            "min_increment": game.config.min_increment,
            "auction_seconds": game.config.auction_seconds,
            "anti_snipe_window_seconds": game.config.anti_snipe_window_seconds,
            "anti_snipe_extension_seconds": game.config.anti_snipe_extension_seconds,
            "cash_per_vp": game.config.cash_per_vp,
            "upkeep_effect_timing": game.config.upkeep_effect_timing.value,
            "ai_strategy": game.config.ai_strategy.value,
            "ai_project_priority": game.config.ai_project_priority.value,
        },
    }


def private_view(game: TradingGame, player_id: str) -> dict:
    try:
        city = game.city_of(player_id)
    except RuleError:
        return {"player_id": player_id, "slot": None}

    lot = game.lots.get(city.index) if game.phase == Phase.LOT_CREATION else None
    upkeep = game.last_upkeep.get(city.index)
    return {
        "player_id": player_id,
        "slot": city.index,
        "inventory": _bundle(city.inventory),
        "lot_submitted": game.phase == Phase.LOT_CREATION and city.index in game.lots,
        "lot": _bundle(lot.contents) if lot else None,
        "affordable_projects": [
            i
            for i, card in enumerate(game.project_slots)
            if card is not None and game.can_afford(city, card)
        ],
        "discard_required": game.pending_discards.get(city.index, 0),
        # What next round looks like, so Cleanup discards don't cut into next upkeep.
        "next_production": _bundle(game.production_for(city, at_round=game.round + 1)),
        "next_upkeep": _bundle(game.upkeep_for(city, at_round=game.round + 1)),
        "last_upkeep": {
            "required": _bundle(upkeep.required),
            "paid": _bundle(upkeep.paid),
            "missing": upkeep.missing,
            "shortage_after": upkeep.shortage_after,
        }
        if upkeep
        else None,
        "last_discards": _bundle(game.last_discards.get(city.index, {})),
    }
