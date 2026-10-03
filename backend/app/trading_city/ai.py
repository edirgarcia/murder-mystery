"""AI city decision-making (spec §5, §57).

The spec leaves AI behaviour open, so the engine only talks to AI cities
through ``CityStrategy``. Two implementations:

- ``PassiveStrategy``: never sells, bids or builds (the city still produces,
  earns income and pays upkeep).
- ``HeuristicStrategy``: a deliberately simple merchant. Each round it picks
  one visible project to work towards, protects upkeep + that project's cost,
  sells the rest, and bids up to what a lot is worth *to it*. When it can't
  afford its target, it builds the best card its spare goods can pay for.

Strategies must only read public state plus their own city's inventory —
never other inventories or unrevealed lots — so AI cities play by the same
information rules as humans (spec §50).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from .config import AIStrategyKind
from .economy import Resource
from .projects import EffectKind, MarketAxis, MarketLevel, ProjectCard, ProjectCategory

if TYPE_CHECKING:
    from .engine import City, TradingGame

Bundle = dict[Resource, int]


class CityStrategy(Protocol):
    # When False the engine treats this city as having passed every auction,
    # so auctions can close early once all humans are done.
    bids_in_auctions: bool

    def choose_lot(self, game: TradingGame, slot: int) -> Bundle | None:
        """Surplus lot to commit this round, or None for no lot."""
        ...

    def choose_bid(self, game: TradingGame, slot: int) -> int | None:
        """Bid amount on the current auction, or None to drop out of it."""
        ...

    def choose_project(self, game: TradingGame, slot: int) -> int | None:
        """Index of a visible project slot to build, or None to pass."""
        ...

    def choose_discards(self, game: TradingGame, slot: int, excess: int) -> Bundle | None:
        """Resources to discard at Cleanup, or None to use the engine default."""
        ...


class PassiveStrategy:
    bids_in_auctions = False

    def choose_lot(self, game: TradingGame, slot: int) -> Bundle | None:
        return None

    def choose_bid(self, game: TradingGame, slot: int) -> int | None:
        return None

    def choose_project(self, game: TradingGame, slot: int) -> int | None:
        return None

    def choose_discards(self, game: TradingGame, slot: int, excess: int) -> Bundle | None:
        return None


@dataclass(frozen=True)
class AITuning:
    # Project worth is in VP-equivalents. One extra unit per round for one round:
    unit_vp: float = 0.5
    # How much hurting rivals counts compared to helping itself (market projects).
    rival_weight: float = 0.5
    income_vp_per_dollar: float = 0.3
    storage_vp: float = 0.5
    # Ignore targets needing more than this many missing units per remaining round.
    max_gap_per_round: int = 3
    # Only switch targets if the new one scores this much better.
    switch_margin: float = 1.5
    # Spare units of each never-produced upkeep resource to hold back from lots.
    import_spare: int = 1
    # Lots contain only the N resources with the biggest surplus (plus storage overflow),
    # so buyers who need that resource value most of the lot.
    lot_resource_types: int = 2

    # Bidding: per-unit values as multiples of the recent market price per unit.
    default_unit_price: float = 2.0
    min_unit_price: float = 1.5  # floor so cheap sales can't spiral prices to zero
    price_window: int = 10
    # Idle cash buys nothing at game end, so richer AIs bid more freely:
    # valuations scale by cash / comfortable_cash, between 1x and max_wealth_mult.
    comfortable_cash: int = 15
    max_wealth_mult: float = 3.0
    upkeep_gap_mult: float = 2.0
    upkeep_gap_min: float = 3.0
    target_mult: float = 1.5
    buffer_mult: float = 1.0
    other_value: float = 0.5
    cash_reserve: int = 3
    bid_jitter: int = 1


@dataclass
class HeuristicStrategy:
    rng: random.Random = field(default_factory=random.Random)
    tuning: AITuning = field(default_factory=AITuning)
    bids_in_auctions: bool = True
    target_id: str | None = None
    _lot_jitter: dict[int, int] = field(default_factory=dict)

    # --- Hooks ---

    def choose_lot(self, game: TradingGame, slot: int) -> Bundle | None:
        city = game.cities[slot]
        self._update_target(game, city)  # first hook each round
        keep = self._reserve(game, city)
        surplus = {r: n - keep.get(r, 0) for r, n in city.inventory.items() if n > keep.get(r, 0)}
        biggest = sorted(surplus, key=lambda r: surplus[r], reverse=True)
        lot = {r: surplus[r] for r in biggest[: self.tuning.lot_resource_types]}
        # Anything that would be discarded at Cleanup is better sold for any price.
        capacity = game.storage_for(city)
        overflow = 0 if capacity is None else sum(city.inventory.values()) - sum(lot.values()) - capacity
        for r in biggest[self.tuning.lot_resource_types :]:
            if overflow <= 0:
                break
            extra = min(surplus[r], overflow)
            lot[r] = extra
            overflow -= extra
        return lot or None

    def choose_bid(self, game: TradingGame, slot: int) -> int | None:
        auction = game.auction
        city = game.cities[slot]
        value = self._lot_value(game, city, auction.lot.contents)
        if value < 1:
            return None  # jitter must never make a worthless lot look biddable
        jitter = self._lot_jitter.setdefault(
            auction.lot.id, self.rng.randint(-self.tuning.bid_jitter, self.tuning.bid_jitter)
        )
        spendable = city.cash - self.tuning.cash_reserve - self._target_cash(game)
        max_bid = min(math.floor(value) + jitter, spendable)
        minimum = game.min_next_bid()
        return minimum if minimum <= max_bid else None

    def choose_project(self, game: TradingGame, slot: int) -> int | None:
        city = game.cities[slot]
        index = self._target_index(game)
        if index is not None and game.can_afford(city, game.project_slots[index]):
            return index
        return self._fallback_project(game, city, skip=index)

    def _fallback_project(self, game: TradingGame, city: City, skip: int | None) -> int | None:
        """Can't afford the target yet: build the most useful *City* card paid for only
        with goods and cash that aren't being saved (upkeep, target, spare import).
        Avoids wasted turns — this is what the cheap Small storage cards are for.

        Market and Prestige cards are only ever built as deliberate targets: letting
        the fallback grab cheap Market cards doubled global manipulation and shortages
        in simulation."""
        reserve = self._reserve(game, city)
        cash_floor = self.tuning.cash_reserve + self._target_cash(game)
        rounds_left = game.config.total_rounds - game.round
        best, best_worth = None, 0.0
        for i, card in enumerate(game.project_slots):
            if card is None or i == skip or card.category != ProjectCategory.CITY:
                continue
            if not game.can_afford(city, card):
                continue
            if any(city.inventory.get(r, 0) - n < reserve.get(r, 0) for r, n in card.cost.items()):
                continue  # would dip into goods we're saving
            price = game.cash_cost(card)
            if price and city.cash - price < cash_floor:
                continue  # would spend money we're saving
            worth = self.project_worth(game, city, card, rounds_left)
            if worth > best_worth:
                best, best_worth = i, worth
        return best

    def choose_discards(self, game: TradingGame, slot: int, excess: int) -> Bundle | None:
        return None

    # --- Target selection ---

    def _target_index(self, game: TradingGame) -> int | None:
        for i, card in enumerate(game.project_slots):
            if card is not None and card.id == self.target_id:
                return i
        return None

    def _target_cost(self, game: TradingGame) -> Bundle:
        index = self._target_index(game)
        return dict(game.project_slots[index].cost) if index is not None else {}

    def _target_cash(self, game: TradingGame) -> int:
        index = self._target_index(game)
        return game.cash_cost(game.project_slots[index]) if index is not None else 0

    def _update_target(self, game: TradingGame, city: City) -> None:
        rounds_left = game.config.total_rounds - game.round
        scored: dict[str, float] = {}
        for card in game.project_slots:
            if card is None:
                continue
            worth = self.project_worth(game, city, card, rounds_left)
            gap = self._gap(game, city, card)
            if worth <= 0 or gap > self.tuning.max_gap_per_round * max(rounds_left, 1):
                continue
            scored[card.id] = worth / (1 + gap)

        best = max(scored, key=scored.get, default=None)
        current = scored.get(self.target_id) if self.target_id else None
        # Sticky: only switch when the current target vanished or something is clearly better.
        if current is None or (best and scored[best] > current * self.tuning.switch_margin):
            self.target_id = best

    def _gap(self, game: TradingGame, city: City, card: ProjectCard) -> int:
        """Units still missing for ``card`` after setting this round's upkeep aside."""
        upkeep = game.upkeep_for(city)
        return sum(
            max(0, n - max(0, city.inventory.get(r, 0) - upkeep.get(r, 0)))
            for r, n in card.cost.items()
        )

    def project_worth(
        self, game: TradingGame, city: City, card: ProjectCard, rounds_left: int
    ) -> float:
        t = self.tuning
        if card.category == ProjectCategory.PRESTIGE:
            return card.vp
        effect = card.effect
        match effect.kind:
            case EffectKind.INCOME:
                return t.income_vp_per_dollar * effect.amount * rounds_left
            case EffectKind.STORAGE:
                return t.storage_vp
            case EffectKind.PRODUCTION | EffectKind.UPKEEP_REDUCTION:
                net = self._net_change(game, city, extra_effect=effect)
                return t.unit_vp * net * rounds_left + card.vp
            case EffectKind.MARKET:
                return t.unit_vp * self._market_advantage(game, city, card) * rounds_left + card.vp
        return card.vp

    def _net_change(self, game: TradingGame, city: City, **what_if) -> int:
        """Change in (production - upkeep) units per round under a hypothetical effect."""
        before = sum(game.production_for(city).values()) - sum(game.upkeep_for(city).values())
        after = sum(game.production_for(city, **what_if).values()) - sum(
            game.upkeep_for(city, **what_if).values()
        )
        return after - before

    def _market_advantage(self, game: TradingGame, city: City, card: ProjectCard) -> float:
        """How much more this global effect helps me than it helps my rivals, in units/round."""
        e = card.effect
        override = (e.resource, e.axis, e.level)
        mine = self._net_change(game, city, market_override=override)
        rivals = [
            self._net_change(game, c, market_override=override)
            for c in game.cities
            if c.index != city.index
        ]
        advantage = mine - self.tuning.rival_weight * (sum(rivals) / len(rivals))
        # Squeezing supply of something I must import also hurts me as a buyer.
        if (
            e.axis == MarketAxis.SUPPLY
            and e.level == MarketLevel.DOWN
            and e.resource in city.slot.upkeep
            and e.resource not in city.slot.production
        ):
            advantage -= 1
        return advantage

    # --- Selling ---

    def _reserve(self, game: TradingGame, city: City) -> Bundle:
        """Upkeep, target cost, and a spare of each import: never sold."""
        keep = dict(game.upkeep_for(city))
        for r, n in self._target_cost(game).items():
            keep[r] = keep.get(r, 0) + n
        for r in city.slot.upkeep:
            if r not in city.slot.production:
                keep[r] = keep.get(r, 0) + self.tuning.import_spare
        return keep

    # --- Bidding ---

    def _unit_price(self, game: TradingGame) -> float:
        t = self.tuning
        sold = [h for h in game.history if h.winner is not None][-t.price_window :]
        units = sum(sum(h.contents.values()) for h in sold)
        average = sum(h.price for h in sold) / units if units else t.default_unit_price
        return max(average, t.min_unit_price)

    def _lot_value(self, game: TradingGame, city: City, contents: Bundle) -> float:
        """What the lot is worth to me: each unit fills the most urgent need first."""
        t = self.tuning
        wealth = min(t.max_wealth_mult, max(1.0, city.cash / t.comfortable_cash))
        price = self._unit_price(game) * wealth
        upkeep = game.upkeep_for(city)
        target = self._target_cost(game)
        capacity = game.storage_for(city)
        room = math.inf if capacity is None else capacity - sum(city.inventory.values())

        value = 0.0
        for r, n in contents.items():
            have = city.inventory.get(r, 0)
            need, want = upkeep.get(r, 0), target.get(r, 0)
            upkeep_gap = max(0, need - have)
            target_gap = max(0, want - max(0, have - need))
            # Enough left over to cover next round's upkeep as well.
            buffer_gap = max(0, need - max(0, have - need - want))
            for _ in range(n):
                if upkeep_gap:
                    upkeep_gap -= 1
                    value += max(t.upkeep_gap_min, t.upkeep_gap_mult * price)
                elif target_gap:
                    target_gap -= 1
                    value += t.target_mult * price
                elif buffer_gap:
                    buffer_gap -= 1
                    value += t.buffer_mult * price
                elif room > 0:
                    value += t.other_value
                room -= 1
        return value


def make_strategy(kind: AIStrategyKind, rng: random.Random) -> CityStrategy:
    if kind == AIStrategyKind.PASSIVE:
        return PassiveStrategy()
    return HeuristicStrategy(rng=rng)
