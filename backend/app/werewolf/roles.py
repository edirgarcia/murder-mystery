"""Role assignment logic for Werewolf."""

from __future__ import annotations

import random

from .config import WEREWOLF_COUNT_RULES
from .models import Role


def assign_roles(player_ids: list[str]) -> dict[str, Role]:
    """Assign roles to players based on count.

    Distribution:
        - 1 Seer, 1 Witch, 1 Hunter, 1 Cupid (always)
        - Werewolves: 2 for 6-8, 3 for 9-12, 4 for 13-16
        - Rest are Villagers
    """
    n = len(player_ids)

    num_werewolves = 2
    for min_p, max_p, count in WEREWOLF_COUNT_RULES:
        if min_p <= n <= max_p:
            num_werewolves = count
            break

    roles: list[Role] = [Role.SEER, Role.WITCH, Role.HUNTER, Role.CUPID]
    roles.extend([Role.WEREWOLF] * num_werewolves)
    roles.extend([Role.VILLAGER] * (n - len(roles)))

    random.shuffle(roles)
    shuffled_ids = list(player_ids)
    random.shuffle(shuffled_ids)

    return dict(zip(shuffled_ids, roles))
