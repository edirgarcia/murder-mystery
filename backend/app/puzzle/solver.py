"""CP-SAT solver wrapper using Google OR-Tools.

Builds a constraint-programming model from clue objects and counts /
enumerates solutions. Uses inverse permutation variables so that each
clue translates to 1-3 simple constraints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from .clues import Clue

from .schema import get_schema
from .value_mapping import ValueMapping

Solution = dict[str, list[str]]

# Module-level schema override. Set by the pipeline before running
# selection so that solver functions use player names without needing
# to thread the parameter through every call.
_schema_override: dict[str, list[str]] | None = None


def set_schema_override(schema: dict[str, list[str]] | None) -> None:
    global _schema_override
    _schema_override = schema


def _get_schema(n: int) -> dict[str, list[str]]:
    if _schema_override is not None:
        return _schema_override
    return get_schema(n)


# ── Model building ───────────────────────────────────────────────

InvVars = dict[str, list[cp_model.IntVar]]


def build_model(
    n: int, clues: list[Clue]
) -> tuple[cp_model.CpModel, InvVars, ValueMapping]:
    """Build a CP-SAT model for *n* positions with the given clues.

    Returns:
        (model, inv_vars, mapping)

    ``inv_vars[cat][val_int]`` gives the *position* (0 … n-1) where value
    ``val_int`` of category ``cat`` is placed. This is the *inverse
    permutation* representation, enforced via ``AddInverse``.
    """
    schema = _get_schema(n)
    mapping = ValueMapping(schema)
    model = cp_model.CpModel()

    # Forward vars: fwd[cat][pos] = which value is at that position
    fwd: dict[str, list[cp_model.IntVar]] = {}
    # Inverse vars: inv[cat][val] = which position has that value
    inv: dict[str, list[cp_model.IntVar]] = {}

    for cat in schema:
        fwd[cat] = [
            model.new_int_var(0, n - 1, f"fwd_{cat}_{pos}") for pos in range(n)
        ]
        inv[cat] = [
            model.new_int_var(0, n - 1, f"inv_{cat}_{val}") for val in range(n)
        ]
        model.add_inverse(fwd[cat], inv[cat])

    for clue in clues:
        clue.add_to_model(model, n, inv, mapping)

    return model, inv, mapping


# ── Solution callback for bounded counting ───────────────────────

class _BoundedCounter(cp_model.CpSolverSolutionCallback):
    """Counts solutions and stops after reaching the limit."""

    def __init__(self, limit: int) -> None:
        super().__init__()
        self.limit = limit
        self.count = 0

    def on_solution_callback(self) -> None:
        self.count += 1
        if self.count >= self.limit:
            self.stop_search()


class _SolutionCollector(cp_model.CpSolverSolutionCallback):
    """Collects solutions (as raw inv-var assignments) up to a limit."""

    def __init__(self, inv: InvVars, limit: int) -> None:
        super().__init__()
        self._inv = inv
        self.limit = limit
        self.solutions: list[dict[str, list[int]]] = []

    def on_solution_callback(self) -> None:
        sol: dict[str, list[int]] = {}
        for cat, vars_ in self._inv.items():
            sol[cat] = [self.value(v) for v in vars_]
        self.solutions.append(sol)
        if len(self.solutions) >= self.limit:
            self.stop_search()


# ── Public API (same signatures as before) ───────────────────────


def _make_solver() -> cp_model.CpSolver:
    """Create a deterministic CP-SAT solver for solution enumeration.

    Pin to 1 worker so solution counts are exact (multi-worker mode
    can report duplicate solutions).
    """
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.num_workers = 1
    return solver


def count_solutions_bounded(n: int, clues: list[Clue], limit: int = 2) -> int:
    """Count solutions up to *limit* (early stop).

    Returns the actual count if <= limit, otherwise returns limit.
    """
    model, _inv, _mapping = build_model(n, clues)
    solver = _make_solver()
    counter = _BoundedCounter(limit)
    solver.solve(model, counter)
    return counter.count


def is_unique(n: int, clues: list[Clue]) -> bool:
    """Check if exactly one solution exists."""
    return count_solutions_bounded(n, clues, limit=2) == 1


def get_unique_solution(n: int, clues: list[Clue]) -> Solution | None:
    """Return the solution if exactly one exists, else None."""
    model, inv, mapping = build_model(n, clues)
    solver = _make_solver()
    collector = _SolutionCollector(inv, limit=2)
    solver.solve(model, collector)
    if len(collector.solutions) == 1:
        return _raw_to_solution(collector.solutions[0], mapping)
    return None


def get_solutions_bounded(n: int, clues: list[Clue], limit: int) -> list[Solution]:
    """Return up to *limit* solutions."""
    model, inv, mapping = build_model(n, clues)
    solver = _make_solver()
    collector = _SolutionCollector(inv, limit)
    solver.solve(model, collector)
    return [_raw_to_solution(raw, mapping) for raw in collector.solutions]


def _raw_to_solution(
    raw: dict[str, list[int]], mapping: ValueMapping
) -> Solution:
    """Convert inv-var assignments {cat: [pos_for_val0, pos_for_val1, …]}
    to the standard Solution format {cat: [val_at_pos0, val_at_pos1, …]}.
    """
    solution: Solution = {}
    for cat, positions in raw.items():
        n = len(positions)
        vals = [""] * n
        for val_int, pos in enumerate(positions):
            vals[pos] = mapping.int_to_str(cat, val_int)
        solution[cat] = vals
    return solution
