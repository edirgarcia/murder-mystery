"""Trading City settings.

Everything in ``BalanceConfig`` is balance data (spec §58): it can be tuned
without touching the rules engine. Structural rules live in ``engine.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

MIN_PLAYERS = 2
# One human per economic slot; remaining slots are filled by AI cities.
MAX_PLAYERS = 8


class DisplacedCardPolicy(str, Enum):
    """What happens to a Market Project card whose effect was replaced (spec §36, TBD)."""

    DISCARD = "discard"
    RETURN_TO_POOL = "return_to_pool"


class EffectTiming(str, Enum):
    """When newly built upkeep-affecting effects start to apply (spec §57, TBD).

    Projects are built before Upkeep in the same round, so this decides whether
    a Demand modifier / upkeep reduction built this round already counts.
    """

    IMMEDIATE = "immediate"
    NEXT_ROUND = "next_round"


class AIProjectPriority(str, Enum):
    """Where AI cities sit in the project build order (spec §26 only covers humans)."""

    # All active cities share one rotation: with 8 rounds each gets first pick once.
    ROTATING = "rotating"
    # Humans rotate among themselves and always act first; AI cities follow.
    AFTER_HUMANS = "after_humans"


class AIStrategyKind(str, Enum):
    HEURISTIC = "heuristic"
    PASSIVE = "passive"


@dataclass(frozen=True)
class BalanceConfig:
    total_rounds: int = 8
    # City economy shape (see economy.build_slots): production per produced resource,
    # main export first, and upkeep size (all 1-unit; the last one is never produced).
    # Deliberately smaller than the spec's 4/3/2/1 + upkeep 4: at 10/4 cities produced
    # far more than upkeep and projects could absorb, and discarded ~a third of it.
    production_pattern: tuple[int, ...] = (2, 1, 1, 1)
    upkeep_size: int = 3
    # Which resources project costs ask for (projects.RESOURCE_SPLITS): "even", or
    # "gentle"/"strong" to tilt cheap cards toward basic goods and big ones toward
    # refined goods. "handwritten" is the original hand-picked catalog.
    resource_split: str = "gentle"
    starting_cash: int = 15
    income_per_round: int = 4
    # None disables the storage limit entirely (spec §49: provisional).
    storage_capacity: int | None = 10

    min_bid: int = 1
    min_increment: int = 1
    auction_seconds: int = 20
    anti_snipe_window_seconds: int = 5
    anti_snipe_extension_seconds: int = 5

    # Visible project-market slots, by category, in display order. The spec (§23)
    # suggests 8; 12 makes it much likelier everyone can afford *something* each round.
    project_slot_mix: tuple[str, ...] = field(
        default=("city",) * 5 + ("market",) * 4 + ("prestige",) * 3
    )
    # (first_round, tier) pairs; the highest first_round <= current round wins.
    prestige_tier_schedule: tuple[tuple[int, str], ...] = field(
        default=((1, "small"), (3, "medium"), (6, "major"))
    )
    # "Grand" City projects (same effect + 1-2 VP) are shuffled into the City deck from
    # this round on: early game builds engines, late game turns them into points.
    grand_city_from_round: int = 4
    # Cheap "Small" storage cards (2 resources) are seeded near the top of the City deck
    # so early boards always have something affordable; from this round on they are
    # removed from the deck *and* the board, leaving the +5 and Grand storage cards.
    small_city_until_round: int = 4

    displaced_market_card: DisplacedCardPolicy = DisplacedCardPolicy.DISCARD
    upkeep_effect_timing: EffectTiming = EffectTiming.IMMEDIATE
    # Final scoring is still provisional (spec §53): leftover cash converts at a poor
    # rate so hoarding stays worse than building. None => cash only breaks VP ties.
    cash_per_vp: int | None = 12
    # Prestige projects also cost cash (VP x this, rounded up): victory costs goods *and*
    # gold. City/Market projects never cost cash, so struggling cities can still rebuild.
    prestige_cash_per_vp: float = 2.0

    ai_strategy: AIStrategyKind = AIStrategyKind.HEURISTIC
    ai_project_priority: AIProjectPriority = AIProjectPriority.ROTATING
    # Pause before AI cities respond in an auction, so they don't feel robotic.
    ai_bid_delay_seconds: float = 1.5

    # Phase timers (UI pacing, not rules).
    city_selection_seconds: int = 90
    lot_creation_seconds: int = 60
    project_turn_seconds: int = 30
    discard_seconds: int = 45
    # Summary screens wait up to this long, but move on once every player taps Continue.
    production_display_seconds: int = 20
    upkeep_display_seconds: int = 20
    # "Study the Market" pause before lots, every round (also ends when all continue).
    market_study_seconds: int = 30
    lot_result_display_seconds: int = 6


DEFAULT_CONFIG = BalanceConfig()
