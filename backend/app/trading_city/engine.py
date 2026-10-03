"""Trading City rules engine.

Pure, synchronous game state. No I/O and no clock: anything time-dependent
(auction timers) takes ``now`` as a float timestamp, so the whole game can be
driven deterministically from tests. The async route layer owns pacing.

Economic actors are identified by economic slot index (0-7). Human players are
mapped to the slot they claimed; every unclaimed slot is an AI city.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from .ai import CityStrategy, make_strategy
from .config import (
    DEFAULT_CONFIG,
    AIProjectPriority,
    BalanceConfig,
    DisplacedCardPolicy,
    EffectTiming,
)
from .economy import RESOURCES, EconomicSlot, Resource, build_slots
from .projects import (
    Effect,
    EffectKind,
    MarketAxis,
    MarketLevel,
    ProjectCard,
    ProjectCategory,
    build_catalog,
)

Bundle = dict[Resource, int]
# A hypothetical market state used for "what-if" evaluation: (resource, axis, level).
MarketOverride = tuple[Resource, "MarketAxis", "MarketLevel"]


class RuleError(Exception):
    """An action that the rules do not allow in the current state."""


class Phase(str, Enum):
    CITY_SELECTION = "city_selection"
    PRODUCTION = "production"
    MARKET_STUDY = "market_study"  # no actions: time to read the project board
    LOT_CREATION = "lot_creation"
    AUCTION = "auction"
    PROJECTS = "projects"
    UPKEEP = "upkeep"
    CLEANUP = "cleanup"
    FINISHED = "finished"


# --- Bundle helpers ---


def bundle_size(bundle: Bundle) -> int:
    return sum(bundle.values())


def clean_bundle(bundle: Bundle) -> Bundle:
    return {r: n for r, n in bundle.items() if n > 0}


def _validate_bundle(bundle: Bundle) -> Bundle:
    for r, n in bundle.items():
        if not isinstance(r, Resource):
            raise RuleError(f"Unknown resource: {r}")
        if not isinstance(n, int) or n < 0:
            raise RuleError("Resource quantities must be non-negative integers")
    return clean_bundle(bundle)


# --- State ---


@dataclass
class BuiltProject:
    card: ProjectCard
    round_built: int
    # Round from which upkeep-affecting effects count (see EffectTiming).
    active_from_round: int


@dataclass
class City:
    slot: EconomicSlot
    owner_id: str | None = None
    owner_name: str | None = None
    inventory: Bundle = field(default_factory=dict)
    cash: int = 0
    shortage: int = 0
    projects: list[BuiltProject] = field(default_factory=list)

    @property
    def index(self) -> int:
        return self.slot.index

    @property
    def is_ai(self) -> bool:
        return self.owner_id is None

    @property
    def name(self) -> str:
        return self.slot.ai_city_name if self.is_ai else self.slot.city_name

    @property
    def vp(self) -> int:
        return sum(p.card.vp for p in self.projects)

    def has(self, bundle: Bundle) -> bool:
        return all(self.inventory.get(r, 0) >= n for r, n in bundle.items())

    def add(self, bundle: Bundle) -> None:
        for r, n in bundle.items():
            self.inventory[r] = self.inventory.get(r, 0) + n
        self.inventory = clean_bundle(self.inventory)

    def remove(self, bundle: Bundle) -> None:
        if not self.has(bundle):
            raise RuleError("Not enough resources")
        for r, n in bundle.items():
            self.inventory[r] -= n
        self.inventory = clean_bundle(self.inventory)


@dataclass
class MarketSlot:
    level: MarketLevel = MarketLevel.NEUTRAL
    card: ProjectCard | None = None
    built_by: int | None = None
    active_from_round: int = 0


@dataclass
class Lot:
    id: int
    seller: int
    contents: Bundle


@dataclass
class Bid:
    bidder: int
    amount: int
    at: float


@dataclass
class Auction:
    lot: Lot
    ends_at: float
    bids: list[Bid] = field(default_factory=list)
    passed: set[int] = field(default_factory=set)

    @property
    def high_bid(self) -> Bid | None:
        return self.bids[-1] if self.bids else None


@dataclass
class AuctionRecord:
    round: int
    lot_id: int
    seller: int
    contents: Bundle
    winner: int | None
    price: int | None
    bids: list[Bid]


@dataclass
class UpkeepResult:
    required: Bundle
    paid: Bundle
    missing: int
    shortage_before: int
    shortage_after: int


@dataclass
class ProjectEvent:
    round: int
    city: int
    card: ProjectCard
    displaced: ProjectCard | None = None


class TradingGame:
    def __init__(
        self,
        players: list[tuple[str, str]],
        config: BalanceConfig = DEFAULT_CONFIG,
        rng: random.Random | None = None,
        strategy_factory: Callable[[int], CityStrategy] | None = None,
    ) -> None:
        slots = build_slots(config.production_pattern, config.upkeep_size)
        if not 1 <= len(players) <= len(slots):
            raise RuleError(f"Trading City supports 1-{len(slots)} human players")
        self.config = config
        self.rng = rng or random.Random()
        self.players: dict[str, str] = dict(players)
        self.strategy_factory = strategy_factory or (
            lambda _slot: make_strategy(config.ai_strategy, random.Random(self.rng.random()))
        )
        self.strategies: dict[int, CityStrategy] = {}

        self.cities: list[City] = [City(slot=s) for s in slots]
        self.phase = Phase.CITY_SELECTION
        self.round = 0
        # Fixed seating drawn at setup; each round's priority order rotates it.
        self.seat_order: list[int] = []
        self.priority: list[int] = []  # city slots, in this round's project order

        self.market: dict[Resource, dict[MarketAxis, MarketSlot]] = {
            r: {axis: MarketSlot() for axis in MarketAxis} for r in RESOURCES
        }
        self.project_slots: list[ProjectCard | None] = [None] * len(config.project_slot_mix)
        self.decks: dict[str, list[ProjectCard]] = self._build_decks()
        self.discarded_cards: list[ProjectCard] = []
        self.project_log: list[ProjectEvent] = []

        self.lots: dict[int, Lot | None] = {}
        self.auction_queue: list[Lot] = []
        self.auction: Auction | None = None
        self.auctions_total = 0
        self.history: list[AuctionRecord] = []
        self._next_lot_id = 1

        self.project_turn = 0
        self.project_actions: dict[int, str | None] = {}  # slot -> card id, or None (passed)

        self.last_production: dict[int, Bundle] = {}
        self.last_income: dict[int, int] = {}
        self.last_upkeep: dict[int, UpkeepResult] = {}
        self.pending_discards: dict[int, int] = {}
        self.last_discards: dict[int, Bundle] = {}

    # --- Lookups ---

    def city_of(self, player_id: str) -> City:
        for city in self.cities:
            if city.owner_id == player_id:
                return city
        raise RuleError("You have not claimed a city")

    def human_cities(self) -> list[City]:
        return [c for c in self.cities if not c.is_ai]

    def _require_phase(self, *phases: Phase) -> None:
        if self.phase not in phases:
            raise RuleError(f"Not allowed during {self.phase.value}")

    # --- Derived economics (spec §12, §34-§35, §43, §46, §49) ---

    def market_level(
        self,
        resource: Resource,
        axis: MarketAxis,
        override: MarketOverride | None = None,
        at_round: int | None = None,
    ) -> MarketLevel:
        if override is not None and override[0] == resource and override[1] == axis:
            return override[2]
        slot = self.market[resource][axis]
        round_ = self.round if at_round is None else at_round
        return slot.level if round_ >= slot.active_from_round else MarketLevel.NEUTRAL

    def _effects(
        self,
        city: City,
        kind: EffectKind,
        *,
        upkeep: bool = False,
        extra: Effect | None = None,
        at_round: int | None = None,
    ) -> list[Effect]:
        round_ = self.round if at_round is None else at_round
        effects = [
            p.card.effect
            for p in city.projects
            if p.card.effect.kind == kind and (not upkeep or round_ >= p.active_from_round)
        ]
        if extra is not None and extra.kind == kind:
            effects.append(extra)
        return effects

    # ``market_override`` / ``extra_effect`` answer "what if?" without touching state,
    # e.g. for AI project evaluation. ``at_round`` evaluates as of a later round
    # (effects with delayed activation), e.g. to preview next round at Cleanup.

    def production_for(
        self,
        city: City,
        *,
        market_override: MarketOverride | None = None,
        extra_effect: Effect | None = None,
        at_round: int | None = None,
    ) -> Bundle:
        result: Bundle = {}
        for r in RESOURCES:
            amount = city.slot.production.get(r, 0)
            amount += sum(
                e.amount
                for e in self._effects(city, EffectKind.PRODUCTION, extra=extra_effect)
                if e.resource == r
            )
            # Supply modifiers only touch cities that already produce the resource.
            if amount > 0:
                supply = self.market_level(r, MarketAxis.SUPPLY, market_override, at_round)
                amount += {MarketLevel.UP: 1, MarketLevel.DOWN: -1}.get(supply, 0)
            if r == city.slot.primary_resource:
                amount -= city.shortage
            if amount > 0:
                result[r] = amount
        return result

    def upkeep_for(
        self,
        city: City,
        *,
        market_override: MarketOverride | None = None,
        extra_effect: Effect | None = None,
        at_round: int | None = None,
    ) -> Bundle:
        result: Bundle = {}
        for r in RESOURCES:
            base = city.slot.upkeep.get(r, 0)
            amount = base
            if base > 0:
                demand = self.market_level(r, MarketAxis.DEMAND, market_override, at_round)
                amount += {MarketLevel.UP: 1, MarketLevel.DOWN: -1}.get(demand, 0)
            amount -= sum(
                e.amount
                for e in self._effects(
                    city, EffectKind.UPKEEP_REDUCTION, upkeep=True, extra=extra_effect, at_round=at_round
                )
                if e.resource == r
            )
            if amount > 0:
                result[r] = amount
        return result

    def income_for(self, city: City) -> int:
        return self.config.income_per_round + sum(
            e.amount for e in self._effects(city, EffectKind.INCOME)
        )

    def storage_for(self, city: City) -> int | None:
        if self.config.storage_capacity is None:
            return None
        return self.config.storage_capacity + sum(
            e.amount for e in self._effects(city, EffectKind.STORAGE)
        )

    # --- City selection (spec §6, §8) ---

    def claim_city(self, player_id: str, slot: int) -> City:
        self._require_phase(Phase.CITY_SELECTION)
        if player_id not in self.players:
            raise RuleError("Unknown player")
        if not 0 <= slot < len(self.cities):
            raise RuleError("Unknown city")
        if any(c.owner_id == player_id for c in self.cities):
            raise RuleError("You already claimed a city")
        city = self.cities[slot]
        if city.owner_id is not None:
            raise RuleError(f"{city.slot.city_name} was already claimed")
        city.owner_id = player_id
        city.owner_name = self.players[player_id]
        return city

    def all_claimed(self) -> bool:
        return len(self.human_cities()) == len(self.players)

    def finish_city_selection(self) -> None:
        """Assign anyone who didn't pick, activate AI cities, seed starting state."""
        self._require_phase(Phase.CITY_SELECTION)
        claimed = {c.owner_id for c in self.cities}
        free = [c for c in self.cities if c.owner_id is None]
        self.rng.shuffle(free)
        for player_id, name in self.players.items():
            if player_id not in claimed:
                city = free.pop()
                city.owner_id, city.owner_name = player_id, name

        for city in self.cities:
            city.cash = self.config.starting_cash
            city.inventory = dict(city.slot.upkeep)
            if city.is_ai:
                self.strategies[city.index] = self.strategy_factory(city.index)

        self.seat_order = [c.index for c in self.cities]
        self.rng.shuffle(self.seat_order)
        self.phase = Phase.PRODUCTION

    # --- Round start + production (spec §11-§12) ---

    def start_round(self) -> None:
        self._require_phase(Phase.PRODUCTION, Phase.CLEANUP)
        if self.round >= self.config.total_rounds:
            raise RuleError("The game is over")
        self.round += 1
        self.priority = self._priority_for_round()
        self.last_income = {}
        for city in self.cities:
            income = self.income_for(city)
            city.cash += income
            self.last_income[city.index] = income
        if self.round >= self.config.small_city_until_round:
            # Small storage only belongs to the early game: retire it from deck and board.
            city_deck = self.decks[ProjectCategory.CITY.value]
            city_deck[:] = [c for c in city_deck if not self._is_small(c)]
            self.project_slots = [
                None if card is not None and self._is_small(card) else card
                for card in self.project_slots
            ]
        if self.round >= self.config.grand_city_from_round and self.decks["city:grand"]:
            city_deck = self.decks[ProjectCategory.CITY.value]
            city_deck.extend(self.decks["city:grand"])
            self.decks["city:grand"].clear()
            self.rng.shuffle(city_deck)
        self._refill_project_slots()

        self.phase = Phase.PRODUCTION
        self.last_production = {}
        for city in self.cities:
            produced = self.production_for(city)
            city.add(produced)
            self.last_production[city.index] = produced

    def _priority_for_round(self) -> list[int]:
        """Project order for the current round (spec §27), rotating one seat per round."""

        def rotate(seats: list[int]) -> list[int]:
            if not seats:
                return []
            k = (self.round - 1) % len(seats)
            return seats[k:] + seats[:k]

        if self.config.ai_project_priority == AIProjectPriority.ROTATING:
            return rotate(self.seat_order)
        humans = [s for s in self.seat_order if not self.cities[s].is_ai]
        ais = [s for s in self.seat_order if self.cities[s].is_ai]
        return rotate(humans) + rotate(ais)

    # --- Project market (spec §23, §28, §42) ---

    def _build_decks(self) -> dict[str, list[ProjectCard]]:
        city_cards, market_cards, prestige_cards = build_catalog(self.config.resource_split)
        decks: dict[str, list[ProjectCard]] = {
            ProjectCategory.CITY.value: [c for c in city_cards if c.vp == 0],
            "city:grand": [c for c in city_cards if c.vp > 0],
            ProjectCategory.MARKET.value: list(market_cards),
        }
        for card in prestige_cards:
            decks.setdefault(f"prestige:{card.tier}", []).append(card)
        for deck in decks.values():
            self.rng.shuffle(deck)
        # Seed Small cards among the first draws (decks are drawn from the end).
        city = decks[ProjectCategory.CITY.value]
        small = [c for c in city if self._is_small(c)]
        rest = [c for c in city if not self._is_small(c)]
        opening = small + rest[: len(small)]
        self.rng.shuffle(opening)
        decks[ProjectCategory.CITY.value] = rest[len(small) :] + opening
        return decks

    @staticmethod
    def _is_small(card: ProjectCard) -> bool:
        return card.id.startswith("small-")

    def prestige_tier(self) -> str:
        tier = self.config.prestige_tier_schedule[0][1]
        for first_round, name in self.config.prestige_tier_schedule:
            if self.round >= first_round:
                tier = name
        return tier

    def _deck_for(self, category: str) -> list[ProjectCard]:
        if category == ProjectCategory.PRESTIGE.value:
            return self.decks.get(f"prestige:{self.prestige_tier()}", [])
        return self.decks[category]

    def _refill_project_slots(self) -> None:
        for i, category in enumerate(self.config.project_slot_mix):
            if self.project_slots[i] is None:
                deck = self._deck_for(category)
                if deck:
                    self.project_slots[i] = deck.pop()

    # --- Surplus lots (spec §13-§15) ---

    def open_market_study(self) -> None:
        """A pause before lots so players can plan around the visible projects."""
        self._require_phase(Phase.PRODUCTION)
        self.phase = Phase.MARKET_STUDY

    def open_lot_creation(self) -> None:
        self._require_phase(Phase.PRODUCTION, Phase.MARKET_STUDY)
        self.phase = Phase.LOT_CREATION
        self.lots = {}
        for city in self.cities:
            if city.is_ai:
                contents = self.strategies[city.index].choose_lot(self, city.index)
                self._commit_lot(city, contents or {})

    def submit_lot(self, player_id: str, contents: Bundle) -> Lot | None:
        self._require_phase(Phase.LOT_CREATION)
        city = self.city_of(player_id)
        if city.index in self.lots:
            raise RuleError("Your lot is already locked in")
        return self._commit_lot(city, contents)

    def _commit_lot(self, city: City, contents: Bundle) -> Lot | None:
        contents = _validate_bundle(contents)
        if not contents:
            self.lots[city.index] = None
            return None
        if not city.has(contents):
            raise RuleError("You don't own those resources")
        city.remove(contents)
        lot = Lot(id=self._next_lot_id, seller=city.index, contents=contents)
        self._next_lot_id += 1
        self.lots[city.index] = lot
        return lot

    def has_submitted_lot(self, player_id: str) -> bool:
        return self.city_of(player_id).index in self.lots

    def all_lots_submitted(self) -> bool:
        return all(c.index in self.lots for c in self.cities)

    # --- Auctions (spec §16-§22) ---

    def start_auctions(self) -> None:
        """Lock lot creation; anyone who didn't submit gets no lot."""
        self._require_phase(Phase.LOT_CREATION)
        for city in self.cities:
            self.lots.setdefault(city.index, None)
        self.auction_queue = [lot for lot in self.lots.values() if lot is not None]
        self.rng.shuffle(self.auction_queue)
        self.auctions_total = len(self.auction_queue)
        self.auction = None
        self.phase = Phase.AUCTION

    def reveal_next_lot(self, now: float) -> Auction | None:
        self._require_phase(Phase.AUCTION)
        if self.auction is not None:
            raise RuleError("Current auction has not been resolved")
        if not self.auction_queue:
            return None
        lot = self.auction_queue.pop(0)
        self.auction = Auction(lot=lot, ends_at=now + self.config.auction_seconds)
        for city in self.cities:
            if city.is_ai and not self.strategies[city.index].bids_in_auctions:
                self.auction.passed.add(city.index)
        return self.auction

    def min_next_bid(self) -> int:
        if self.auction is None or self.auction.high_bid is None:
            return self.config.min_bid
        return self.auction.high_bid.amount + self.config.min_increment

    def _require_open_auction(self, now: float) -> Auction:
        self._require_phase(Phase.AUCTION)
        if self.auction is None:
            raise RuleError("No lot is up for auction")
        if now >= self.auction.ends_at:
            raise RuleError("This auction has closed")
        return self.auction

    def place_bid(self, slot: int, amount: int, now: float) -> Bid:
        auction = self._require_open_auction(now)
        city = self.cities[slot]
        if slot == auction.lot.seller:
            raise RuleError("You can't bid on your own lot")
        if slot in auction.passed:
            raise RuleError("You already passed on this lot")
        if auction.high_bid and auction.high_bid.bidder == slot:
            raise RuleError("You are already the high bidder")
        if amount < self.min_next_bid():
            raise RuleError(f"Bid must be at least ${self.min_next_bid()}")
        if amount > city.cash:
            raise RuleError("You can't bid more cash than you have")
        bid = Bid(bidder=slot, amount=amount, at=now)
        auction.bids.append(bid)
        # Anti-sniping (spec §19): late bids extend the timer.
        if auction.ends_at - now <= self.config.anti_snipe_window_seconds:
            auction.ends_at += self.config.anti_snipe_extension_seconds
        return bid

    def pass_auction(self, slot: int, now: float) -> None:
        auction = self._require_open_auction(now)
        if slot == auction.lot.seller:
            raise RuleError("You can't bid on your own lot")
        if auction.high_bid and auction.high_bid.bidder == slot:
            raise RuleError("You are the high bidder")
        if slot in auction.passed:
            raise RuleError("You already passed on this lot")
        auction.passed.add(slot)

    def run_ai_auction_step(self, now: float) -> bool:
        """Let each bidding AI city raise or drop out once. Returns True if any bid landed."""
        auction = self.auction
        if auction is None:
            return False
        ai_cities = [c for c in self.cities if c.is_ai]
        self.rng.shuffle(ai_cities)  # no AI gets a permanent first-mover edge
        placed = False
        for city in ai_cities:
            strategy = self.strategies[city.index]
            high = auction.high_bid
            if (
                not strategy.bids_in_auctions
                or city.index == auction.lot.seller
                or city.index in auction.passed
                or (high is not None and high.bidder == city.index)
            ):
                continue
            amount = strategy.choose_bid(self, city.index)
            try:
                if amount is None:
                    # A value-capped bidder never wants back in once priced out.
                    self.pass_auction(city.index, now)
                else:
                    self.place_bid(city.index, amount, now)
                    placed = True
            except RuleError:
                auction.passed.add(city.index)
        return placed

    def auction_settled(self) -> bool:
        """True when no one could still change the outcome, so the timer can be cut short."""
        auction = self.auction
        if auction is None:
            return True
        high = auction.high_bid
        minimum = self.min_next_bid()
        for city in self.cities:
            if city.index in (auction.lot.seller, high.bidder if high else None):
                continue
            if city.index not in auction.passed and city.cash >= minimum:
                return False
        return True

    def resolve_auction(self) -> AuctionRecord:
        self._require_phase(Phase.AUCTION)
        auction = self.auction
        if auction is None:
            raise RuleError("No lot is up for auction")
        lot, high = auction.lot, auction.high_bid
        seller = self.cities[lot.seller]
        if high is None:
            seller.add(lot.contents)
        else:
            buyer = self.cities[high.bidder]
            buyer.cash -= high.amount
            seller.cash += high.amount
            buyer.add(lot.contents)
        record = AuctionRecord(
            round=self.round,
            lot_id=lot.id,
            seller=lot.seller,
            contents=dict(lot.contents),
            winner=high.bidder if high else None,
            price=high.amount if high else None,
            bids=list(auction.bids),
        )
        self.history.append(record)
        self.auction = None
        return record

    # --- Projects (spec §25-§28, §32, §36) ---

    def start_projects(self) -> None:
        self._require_phase(Phase.AUCTION)
        if self.auction is not None or self.auction_queue:
            raise RuleError("Auctions are still running")
        self.phase = Phase.PROJECTS
        self.project_turn = 0
        self.project_actions = {}
        self._run_ai_project_turns()

    def current_project_slot(self) -> int | None:
        if self.phase != Phase.PROJECTS or self.project_turn >= len(self.priority):
            return None
        return self.priority[self.project_turn]

    def current_project_player(self) -> str | None:
        """The human whose turn it is; None while no human is up (or the phase is over)."""
        slot = self.current_project_slot()
        return None if slot is None else self.cities[slot].owner_id

    def projects_done(self) -> bool:
        return self.phase == Phase.PROJECTS and self.project_turn >= len(self.priority)

    def build_project(self, player_id: str, slot_index: int) -> ProjectEvent:
        self._require_phase(Phase.PROJECTS)
        if self.current_project_player() != player_id:
            raise RuleError("It's not your turn to build")
        city = self.city_of(player_id)
        event = self._build(city, slot_index)
        self._end_project_turn(city.index, event.card.id)
        return event

    def pass_project(self, player_id: str) -> None:
        self._require_phase(Phase.PROJECTS)
        if self.current_project_player() != player_id:
            raise RuleError("It's not your turn to build")
        self._end_project_turn(self.city_of(player_id).index, None)

    def _end_project_turn(self, slot: int, card_id: str | None) -> None:
        self.project_actions[slot] = card_id
        self.project_turn += 1
        self._run_ai_project_turns()

    def _run_ai_project_turns(self) -> None:
        """AI turns resolve instantly, until a human is up or everyone has acted."""
        while (slot := self.current_project_slot()) is not None and self.cities[slot].is_ai:
            card_id = None
            choice = self.strategies[slot].choose_project(self, slot)
            if choice is not None:
                try:
                    card_id = self._build(self.cities[slot], choice).card.id
                except RuleError:
                    pass
            self.project_actions[slot] = card_id
            self.project_turn += 1

    def cash_cost(self, card: ProjectCard) -> int:
        if card.category != ProjectCategory.PRESTIGE:
            return 0
        return math.ceil(card.vp * self.config.prestige_cash_per_vp)

    def can_afford(self, city: City, card: ProjectCard) -> bool:
        return city.has(card.cost) and city.cash >= self.cash_cost(card)

    def _build(self, city: City, slot_index: int) -> ProjectEvent:
        if not 0 <= slot_index < len(self.project_slots):
            raise RuleError("Unknown project slot")
        card = self.project_slots[slot_index]
        if card is None:
            raise RuleError("That project slot is empty")
        if not city.has(card.cost):
            raise RuleError(f"You don't have the resources for {card.name}")
        price = self.cash_cost(card)
        if city.cash < price:
            raise RuleError(f"{card.name} also costs ${price}")
        city.remove(card.cost)
        city.cash -= price  # leaves the economy: the game's money sink
        self.project_slots[slot_index] = None  # refilled next Round Start

        active_from = self.round
        if self.config.upkeep_effect_timing == EffectTiming.NEXT_ROUND:
            active_from = self.round + 1

        displaced = None
        if card.category == ProjectCategory.MARKET:
            effect = card.effect
            market_slot = self.market[effect.resource][effect.axis]
            displaced = market_slot.card
            if displaced is not None:
                if self.config.displaced_market_card == DisplacedCardPolicy.RETURN_TO_POOL:
                    deck = self.decks[ProjectCategory.MARKET.value]
                    deck.insert(self.rng.randint(0, len(deck)), displaced)
                else:
                    self.discarded_cards.append(displaced)
            self.market[effect.resource][effect.axis] = MarketSlot(
                level=effect.level,
                card=card,
                built_by=city.index,
                # Supply only matters at the next Production anyway; Demand follows the timing switch.
                active_from_round=active_from if effect.axis == MarketAxis.DEMAND else self.round,
            )
        else:
            city.projects.append(
                BuiltProject(card=card, round_built=self.round, active_from_round=active_from)
            )
        event = ProjectEvent(round=self.round, city=city.index, card=card, displaced=displaced)
        self.project_log.append(event)
        return event

    # --- Upkeep (spec §43-§48) ---

    def run_upkeep(self) -> dict[int, UpkeepResult]:
        self._require_phase(Phase.PROJECTS)
        self.phase = Phase.UPKEEP
        self.last_upkeep = {}
        for city in self.cities:
            required = self.upkeep_for(city)
            paid = {r: min(n, city.inventory.get(r, 0)) for r, n in required.items()}
            city.remove(clean_bundle(paid))
            missing = bundle_size(required) - bundle_size(paid)
            before = city.shortage
            city.shortage = 0 if missing == 0 else city.shortage + missing
            self.last_upkeep[city.index] = UpkeepResult(
                required=required,
                paid=clean_bundle(paid),
                missing=missing,
                shortage_before=before,
                shortage_after=city.shortage,
            )
        return self.last_upkeep

    # --- Cleanup (spec §49, §52) ---

    def excess_for(self, city: City) -> int:
        capacity = self.storage_for(city)
        if capacity is None:
            return 0
        return max(0, bundle_size(city.inventory) - capacity)

    def start_cleanup(self) -> dict[int, int]:
        """Returns human cities that must choose discards: {slot: units over capacity}."""
        self._require_phase(Phase.UPKEEP)
        self.phase = Phase.CLEANUP
        self.last_discards = {}
        self.pending_discards = {}
        for city in self.cities:
            excess = self.excess_for(city)
            if not excess:
                continue
            if city.is_ai:
                choice = self.strategies[city.index].choose_discards(self, city.index, excess)
                try:
                    if not choice:
                        raise RuleError("No discard choice")
                    self._discard(city, choice)
                except RuleError:
                    self._auto_discard(city)
            else:
                self.pending_discards[city.index] = excess
        return dict(self.pending_discards)

    def discard(self, player_id: str, contents: Bundle) -> None:
        self._require_phase(Phase.CLEANUP)
        city = self.city_of(player_id)
        if city.index not in self.pending_discards:
            raise RuleError("You have nothing to discard")
        contents = _validate_bundle(contents)
        if bundle_size(contents) != self.pending_discards[city.index]:
            raise RuleError(f"Discard exactly {self.pending_discards[city.index]} resources")
        self._discard(city, contents)

    def _discard(self, city: City, contents: Bundle) -> None:
        contents = _validate_bundle(contents)
        if bundle_size(contents) != self.excess_for(city):
            raise RuleError("Wrong number of resources to discard")
        city.remove(contents)
        self.last_discards[city.index] = contents
        self.pending_discards.pop(city.index, None)

    def _auto_discard(self, city: City) -> None:
        """Default: drop from the largest stacks first."""
        removed: Bundle = {}
        for _ in range(self.excess_for(city)):
            r = max(city.inventory, key=lambda res: city.inventory[res])
            city.remove({r: 1})
            removed[r] = removed.get(r, 0) + 1
        self.last_discards[city.index] = removed
        self.pending_discards.pop(city.index, None)

    def finish_cleanup(self) -> None:
        self._require_phase(Phase.CLEANUP)
        for slot in list(self.pending_discards):
            self._auto_discard(self.cities[slot])
        if self.round >= self.config.total_rounds:
            self.phase = Phase.FINISHED

    # --- Scoring (spec §53: provisional) ---

    def score_for(self, city: City) -> int:
        score = city.vp
        if self.config.cash_per_vp:
            score += city.cash // self.config.cash_per_vp
        return score

    def standings(self) -> list[City]:
        return sorted(
            self.human_cities(),
            key=lambda c: (self.score_for(c), c.cash),
            reverse=True,
        )
