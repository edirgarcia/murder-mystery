"""Clue types for the murder mystery puzzle.

Each clue type knows how to:
1. Generate candidate clues from a known solution
2. Add itself as a constraint to a CP-SAT model (via inv_vars)
3. Check if a candidate solution satisfies it
4. Render itself as human-readable text
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ortools.sat.python import cp_model

    from .solver import InvVars
    from .value_mapping import ValueMapping

from .generator import Solution


def _ucfirst(s: str) -> str:
    """Uppercase just the first character, preserving the rest."""
    return s[0].upper() + s[1:] if s else s


def _describe(cat: str, val: str) -> str:
    """Convert a (category, value) pair into natural language."""
    match cat:
        case "name":
            return val
        case "nationality":
            return f"the {val} person"
        case "house_color":
            return f"the person in the {val} house"
        case "drink":
            return f"the {val} drinker"
        case "pet":
            return f"the {val} owner"
        case "weapon":
            return f"the person with the {val}"
        case _:
            return f"the person with {cat} {val}"


def _describe_trait(cat: str, val: str, negated: bool = False) -> str:
    """Describe a trait as a predicate (for 'is/has' clauses)."""
    if negated:
        match cat:
            case "name":
                return f"is not {val}"
            case "nationality":
                return f"is not {val}"
            case "house_color":
                return f"does not live in the {val} house"
            case "drink":
                return f"does not drink {val}"
            case "pet":
                return f"does not own the {val}"
            case "weapon":
                return f"does not have the {val}"
            case _:
                return f"does not have {cat} {val}"
    match cat:
        case "name":
            return f"is {val}"
        case "nationality":
            return f"is {val}"
        case "house_color":
            return f"lives in the {val} house"
        case "drink":
            return f"drinks {val}"
        case "pet":
            return f"owns the {val}"
        case "weapon":
            return f"has the {val}"
        case _:
            return f"has {cat} {val}"


class Clue(ABC):
    """Base class for all clue types."""

    @abstractmethod
    def add_to_model(
        self,
        model: cp_model.CpModel,
        n: int,
        inv_vars: InvVars,
        mapping: ValueMapping,
    ) -> None:
        """Add this clue's constraint(s) to the CP-SAT model."""

    @abstractmethod
    def is_satisfied_by(self, solution: Solution) -> bool:
        """Check if a candidate solution satisfies this clue."""

    @abstractmethod
    def render(self) -> str:
        """Human-readable description of the clue."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        return {"type": self.__class__.__name__, "text": self.render()}


@dataclass(frozen=True)
class DirectEquality(Clue):
    """'The person in the Red house drinks Tea.'

    States that category1=value1 and category2=value2 belong to the same position.
    """

    cat1: str
    val1: str
    cat2: str
    val2: str

    def add_to_model(self, model: cp_model.CpModel, n: int, inv_vars: InvVars, mapping: ValueMapping) -> None:
        v1 = mapping.str_to_int(self.cat1, self.val1)
        v2 = mapping.str_to_int(self.cat2, self.val2)
        model.add(inv_vars[self.cat1][v1] == inv_vars[self.cat2][v2])

    def is_satisfied_by(self, solution: Solution) -> bool:
        for pos in range(len(solution[self.cat1])):
            if solution[self.cat1][pos] == self.val1:
                return solution[self.cat2][pos] == self.val2
        return False

    def render(self) -> str:
        subj = _describe(self.cat1, self.val1)
        pred = _describe_trait(self.cat2, self.val2)
        return f"{_ucfirst(subj)} {pred}."


@dataclass(frozen=True)
class Negation(Clue):
    """'The person in the Red house does NOT drink Tea.'"""

    cat1: str
    val1: str
    cat2: str
    val2: str

    def add_to_model(self, model: cp_model.CpModel, n: int, inv_vars: InvVars, mapping: ValueMapping) -> None:
        v1 = mapping.str_to_int(self.cat1, self.val1)
        v2 = mapping.str_to_int(self.cat2, self.val2)
        model.add(inv_vars[self.cat1][v1] != inv_vars[self.cat2][v2])

    def is_satisfied_by(self, solution: Solution) -> bool:
        for pos in range(len(solution[self.cat1])):
            if solution[self.cat1][pos] == self.val1:
                return solution[self.cat2][pos] != self.val2
        return True

    def render(self) -> str:
        subj = _describe(self.cat1, self.val1)
        pred = _describe_trait(self.cat2, self.val2, negated=True)
        return f"{_ucfirst(subj)} {pred}."


@dataclass(frozen=True)
class PositionClue(Clue):
    """'The person in position X has category=value.'

    Positions are 1-indexed in the rendered text, 0-indexed internally.
    """

    cat: str
    val: str
    position: int  # 0-indexed

    def add_to_model(self, model: cp_model.CpModel, n: int, inv_vars: InvVars, mapping: ValueMapping) -> None:
        v = mapping.str_to_int(self.cat, self.val)
        model.add(inv_vars[self.cat][v] == self.position)

    def is_satisfied_by(self, solution: Solution) -> bool:
        return solution[self.cat][self.position] == self.val

    def render(self) -> str:
        pred = _describe_trait(self.cat, self.val)
        return f"The person in house {self.position + 1} {pred}."


@dataclass(frozen=True)
class Adjacency(Clue):
    """'The person with cat1=val1 lives next to the person with cat2=val2.'"""

    cat1: str
    val1: str
    cat2: str
    val2: str

    def add_to_model(self, model: cp_model.CpModel, n: int, inv_vars: InvVars, mapping: ValueMapping) -> None:
        v1 = mapping.str_to_int(self.cat1, self.val1)
        v2 = mapping.str_to_int(self.cat2, self.val2)
        diff = model.new_int_var(-(n - 1), n - 1, "")
        model.add(diff == inv_vars[self.cat1][v1] - inv_vars[self.cat2][v2])
        abs_diff = model.new_int_var(0, n - 1, "")
        model.add_abs_equality(abs_diff, diff)
        model.add(abs_diff == 1)

    def is_satisfied_by(self, solution: Solution) -> bool:
        n = len(solution[self.cat1])
        pos1 = pos2 = None
        for i in range(n):
            if solution[self.cat1][i] == self.val1:
                pos1 = i
            if solution[self.cat2][i] == self.val2:
                pos2 = i
        if pos1 is None or pos2 is None:
            return False
        return abs(pos1 - pos2) == 1

    def render(self) -> str:
        subj = _describe(self.cat1, self.val1)
        obj = _describe(self.cat2, self.val2)
        return f"{_ucfirst(subj)} lives next to {obj}."


@dataclass(frozen=True)
class Ordering(Clue):
    """'The person with cat1=val1 is to the left of (lower position than) cat2=val2.'"""

    cat1: str
    val1: str
    cat2: str
    val2: str

    def add_to_model(self, model: cp_model.CpModel, n: int, inv_vars: InvVars, mapping: ValueMapping) -> None:
        v1 = mapping.str_to_int(self.cat1, self.val1)
        v2 = mapping.str_to_int(self.cat2, self.val2)
        model.add(inv_vars[self.cat1][v1] < inv_vars[self.cat2][v2])

    def is_satisfied_by(self, solution: Solution) -> bool:
        n = len(solution[self.cat1])
        pos1 = pos2 = None
        for i in range(n):
            if solution[self.cat1][i] == self.val1:
                pos1 = i
            if solution[self.cat2][i] == self.val2:
                pos2 = i
        if pos1 is None or pos2 is None:
            return False
        return pos1 < pos2

    def render(self) -> str:
        subj = _describe(self.cat1, self.val1)
        obj = _describe(self.cat2, self.val2)
        return f"{_ucfirst(subj)} lives to the left of {obj}."


def generate_candidates(solution: Solution, rng: random.Random | None = None) -> list[Clue]:
    """Generate a pool of candidate clues that are satisfied by the given solution."""
    rng = rng or random.Random()
    n = len(next(iter(solution.values())))
    cats = list(solution.keys())
    candidates: list[Clue] = []

    for i, cat1 in enumerate(cats):
        for cat2 in cats[i + 1 :]:
            for pos in range(n):
                val1 = solution[cat1][pos]
                val2 = solution[cat2][pos]
                # Direct equality
                candidates.append(DirectEquality(cat1, val1, cat2, val2))

            # Negation: pick pairs that are NOT co-located
            for pos1 in range(n):
                for pos2 in range(n):
                    if pos1 != pos2:
                        val1 = solution[cat1][pos1]
                        val2 = solution[cat2][pos2]
                        candidates.append(Negation(cat1, val1, cat2, val2))

            # Adjacency: pick pairs that ARE adjacent
            for pos in range(n - 1):
                val1 = solution[cat1][pos]
                val2 = solution[cat2][pos + 1]
                candidates.append(Adjacency(cat1, val1, cat2, val2))
                val1 = solution[cat1][pos + 1]
                val2 = solution[cat2][pos]
                candidates.append(Adjacency(cat1, val1, cat2, val2))

            # Ordering: pick pairs where pos1 < pos2
            for pos1 in range(n):
                for pos2 in range(pos1 + 1, n):
                    val1 = solution[cat1][pos1]
                    val2 = solution[cat2][pos2]
                    candidates.append(Ordering(cat1, val1, cat2, val2))

    # Position clues
    for cat in cats:
        for pos in range(n):
            candidates.append(PositionClue(cat, solution[cat][pos], pos))

    rng.shuffle(candidates)
    return candidates
