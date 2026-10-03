"""Resources and the eight economic slots (spec §3-§7).

Each slot has one economic profile, one player-selectable city and one AI
counterpart sharing that profile. Exactly one city per slot is active.

City names are loosely inspired by Civilization VI city-states and Civilization VII
independent powers, each matched to a place known for that slot's main resource.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Resource(str, Enum):
    GRAIN = "grain"
    LIVESTOCK = "livestock"
    TIMBER = "timber"
    IRON = "iron"
    CLOTH = "cloth"
    TOOLS = "tools"
    WINE = "wine"
    SPICES = "spices"


RESOURCES: tuple[Resource, ...] = tuple(Resource)



@dataclass(frozen=True)
class EconomicSlot:
    index: int
    profile: str
    city_name: str
    ai_city_name: str
    production: dict[Resource, int]
    upkeep: dict[Resource, int]

    @property
    def primary_resource(self) -> Resource:
        """The base 4-production resource that Shortage penalties target (spec §46)."""
        return max(self.production, key=lambda r: self.production[r])


# (profile, player city, AI counterpart), in resource order: slot i specialises in RESOURCES[i].
CITY_NAMES: tuple[tuple[str, str, str], ...] = (
    ("Grain", "Babylon", "Carthage"),
    ("Livestock", "Dublin", "Troy"),
    ("Timber", "Stockholm", "Wolin"),
    ("Iron", "Cardiff", "Hattusa"),
    ("Cloth", "Brussels", "Samarkand"),
    ("Tools", "Geneva", "Taruga"),
    ("Wine", "Lisbon", "Yerevan"),
    ("Spices", "Venice", "Zanzibar"),
)

def build_slots(production_pattern: tuple[int, ...], upkeep_size: int) -> tuple[EconomicSlot, ...]:
    """Generate the eight symmetric economic slots.

    Slot ``i`` produces ``production_pattern[k]`` of ``RESOURCES[i + k]`` (wrapping),
    so every resource gets the same total production. Upkeep is 1 unit each of
    the next ``upkeep_size - 1`` resources the slot produces (never its main
    export) plus the first resource it does *not* produce — the structural
    dependency on trade (spec §7).

    (4, 3, 2, 1) with upkeep 4 reproduces the spec v0.1 tables exactly; the game
    default lives in ``BalanceConfig``.
    """
    n = len(RESOURCES)
    produced = len(production_pattern)
    if not 1 <= upkeep_size <= produced or produced >= n:
        raise ValueError("upkeep_size must be 1..len(pattern), and the pattern must leave a resource unproduced")
    slots = []
    for i, (profile, city, ai_city) in enumerate(CITY_NAMES):
        production = {RESOURCES[(i + k) % n]: amount for k, amount in enumerate(production_pattern) if amount > 0}
        upkeep = [RESOURCES[(i + k) % n] for k in range(1, upkeep_size)]
        upkeep.append(RESOURCES[(i + produced) % n])  # never produced: must be bought
        slots.append(
            EconomicSlot(
                index=i,
                profile=profile,
                city_name=city,
                ai_city_name=ai_city,
                production=production,
                upkeep={r: 1 for r in upkeep},
            )
        )
    return tuple(slots)

