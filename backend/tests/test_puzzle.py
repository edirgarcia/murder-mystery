"""Tests for the puzzle engine."""

import pytest

from app.puzzle.schema import (
    get_schema,
    get_active_categories,
    WEAPON_CATEGORY,
    NAME_CATEGORY,
)
from app.puzzle.generator import generate_solution
from app.puzzle.solver import is_unique, get_unique_solution, count_solutions_bounded
from app.puzzle.clues import (
    DirectEquality,
    Negation,
    PositionClue,
    Adjacency,
    Ordering,
    generate_candidates,
)
from app.puzzle.murder import generate_murder_clues
from app.puzzle.solver import set_schema_override as _set_schema_override
from app.puzzle.value_mapping import ValueMapping

import random


class TestSchema:
    def test_get_schema_returns_correct_size(self):
        schema = get_schema(4)
        for cat, vals in schema.items():
            assert len(vals) == 4

    def test_get_schema_invalid_n(self):
        with pytest.raises(ValueError):
            get_schema(3)
        with pytest.raises(ValueError):
            get_schema(13)

    def test_category_scaling(self):
        # Easy: small tier 3, large tier 3
        assert len(get_active_categories(4, "easy")) == 3
        assert len(get_active_categories(6, "easy")) == 3
        assert len(get_active_categories(7, "easy")) == 3
        assert len(get_active_categories(12, "easy")) == 3

        # Medium: small tier 4, large tier 3
        assert len(get_active_categories(4, "medium")) == 4
        assert len(get_active_categories(6, "medium")) == 4
        assert len(get_active_categories(7, "medium")) == 3
        assert len(get_active_categories(12, "medium")) == 3

        # Hard: small tier 5, large tier 4
        assert len(get_active_categories(4, "hard")) == 5
        assert len(get_active_categories(6, "hard")) == 5
        assert len(get_active_categories(7, "hard")) == 4
        assert len(get_active_categories(12, "hard")) == 4

    def test_weapon_always_included(self):
        for n in range(4, 13):
            for diff in ("easy", "medium", "hard"):
                cats = get_active_categories(n, diff)
                assert WEAPON_CATEGORY in cats

    def test_schema_7_succeeds(self):
        schema = get_schema(7)
        # medium default: 3 puzzle categories + name = 4
        assert len(schema) == 4
        assert NAME_CATEGORY in schema
        assert WEAPON_CATEGORY in schema

    def test_schema_12_succeeds(self):
        schema = get_schema(12, difficulty="hard")
        # hard large tier: 4 puzzle categories + name = 5
        assert len(schema) == 5
        for vals in schema.values():
            assert len(vals) == 12


class TestGenerator:
    def test_generate_solution_has_correct_shape(self):
        sol = generate_solution(4, difficulty="hard")
        # n=4 hard → 5 puzzle categories + name = 6
        assert len(sol) == 6
        for vals in sol.values():
            assert len(vals) == 4

    def test_generate_solution_shape_varies_by_n(self):
        sol7 = generate_solution(7)
        # n=7 medium → 3 puzzle categories + name = 4
        assert len(sol7) == 4
        for vals in sol7.values():
            assert len(vals) == 7

    def test_generate_solution_all_values_unique_per_category(self):
        sol = generate_solution(5)
        for vals in sol.values():
            assert len(set(vals)) == len(vals)

    def test_seeded_generation_is_reproducible(self):
        sol1 = generate_solution(4, rng=random.Random(123))
        sol2 = generate_solution(4, rng=random.Random(123))
        assert sol1 == sol2


class TestClueTypes:
    @pytest.fixture
    def solution(self):
        return generate_solution(4, rng=random.Random(42), difficulty="hard")

    def test_direct_equality(self, solution):
        cat1 = "name"
        cat2 = "nationality"
        val1 = solution[cat1][0]
        val2 = solution[cat2][0]
        clue = DirectEquality(cat1, val1, cat2, val2)
        assert clue.is_satisfied_by(solution)
        wrong = DirectEquality(cat1, val1, cat2, solution[cat2][1])
        assert not wrong.is_satisfied_by(solution)

    def test_negation(self, solution):
        cat1 = "name"
        cat2 = "drink"
        val1 = solution[cat1][0]
        val2_wrong = solution[cat2][1]  # Different position
        clue = Negation(cat1, val1, cat2, val2_wrong)
        assert clue.is_satisfied_by(solution)

    def test_position_clue(self, solution):
        clue = PositionClue("name", solution["name"][2], 2)
        assert clue.is_satisfied_by(solution)
        wrong = PositionClue("name", solution["name"][0], 2)
        assert not wrong.is_satisfied_by(solution)

    def test_adjacency(self, solution):
        cat1 = "name"
        cat2 = "drink"
        val1 = solution[cat1][0]
        val2 = solution[cat2][1]  # Position 1 is adjacent to 0
        clue = Adjacency(cat1, val1, cat2, val2)
        assert clue.is_satisfied_by(solution)

    def test_ordering(self, solution):
        cat1 = "name"
        cat2 = "drink"
        val1 = solution[cat1][0]
        val2 = solution[cat2][2]  # Position 2 > 0
        clue = Ordering(cat1, val1, cat2, val2)
        assert clue.is_satisfied_by(solution)

    def test_generate_candidates_all_satisfied(self, solution):
        candidates = generate_candidates(solution, rng=random.Random(42))
        assert len(candidates) > 0
        for clue in candidates:
            assert clue.is_satisfied_by(solution), f"Clue not satisfied: {clue.render()}"


class TestSolver:
    def test_position_and_equality_clues_give_unique_solution(self):
        n = 4
        difficulty = "easy"
        schema = get_schema(n, difficulty=difficulty)
        sol = generate_solution(n, rng=random.Random(1), difficulty=difficulty)
        _set_schema_override(schema)
        try:
            clues = []
            # Pin one category to positions to break symmetry
            for pos in range(n):
                clues.append(PositionClue("name", sol["name"][pos], pos))
            # Add cross-category equalities
            cats = list(sol.keys())
            for i, cat1 in enumerate(cats):
                for cat2 in cats[i + 1 :]:
                    for pos in range(n):
                        clues.append(DirectEquality(cat1, sol[cat1][pos], cat2, sol[cat2][pos]))
            assert is_unique(n, clues)
            result = get_unique_solution(n, clues)
            assert result == sol
        finally:
            _set_schema_override(None)


class TestValueMapping:
    def test_roundtrip(self):
        schema = get_schema(4)
        mapping = ValueMapping(schema)
        for cat, vals in schema.items():
            for val in vals:
                i = mapping.str_to_int(cat, val)
                assert mapping.int_to_str(cat, i) == val


class TestMurder:
    def test_murder_clues_point_to_correct_person(self):
        rng = random.Random(42)
        sol = generate_solution(4, rng, difficulty="hard")
        murderer, weapon, clues = generate_murder_clues(sol, rng)
        assert weapon in sol[WEAPON_CATEGORY]
        murder_pos = sol[WEAPON_CATEGORY].index(weapon)
        assert murderer == sol[NAME_CATEGORY][murder_pos]
        assert len(clues) >= 2
        for c in clues:
            assert c.is_satisfied_by(sol)

    def test_weapon_varies_across_seeds(self):
        weapons = set()
        for seed in range(20):
            rng = random.Random(seed)
            sol = generate_solution(4, rng, difficulty="hard")
            _, weapon, _ = generate_murder_clues(sol, rng)
            weapons.add(weapon)
        assert len(weapons) > 1, "Weapon should vary across different seeds"

    def test_murder_chain_length(self):
        """Verify chain hops match difficulty settings."""
        # 4 players easy → 3 hops → 3 clues (weapon → a → b → name)
        rng = random.Random(42)
        sol = generate_solution(4, rng, difficulty="easy")
        _, _, clues = generate_murder_clues(sol, rng, chain_hops=3)
        assert len(clues) == 3

        # 8 players medium → 3 hops → 3 clues
        rng = random.Random(42)
        sol = generate_solution(8, rng, difficulty="medium")
        _, _, clues = generate_murder_clues(sol, rng, chain_hops=3)
        assert len(clues) == 3

        # 4 players hard → 5 hops → 5 clues
        rng = random.Random(42)
        sol = generate_solution(4, rng, difficulty="hard")
        _, _, clues = generate_murder_clues(sol, rng, chain_hops=5)
        assert len(clues) == 5

    def test_chain_hops_too_large_raises(self):
        rng = random.Random(42)
        sol = generate_solution(4, rng, difficulty="easy")
        # easy 4 players → 3 categories (weapon + 1 intermediate), so max chain_hops = 2
        # Actually: 3 cats = weapon + nationality + drink; intermediates = nationality, drink → 2 intermediates → max chain = 3
        # Requesting 4 hops needs 3 intermediates, but only 1 available (3 cats - weapon - name = 1)
        with pytest.raises(ValueError, match="chain_hops"):
            generate_murder_clues(sol, rng, chain_hops=4)


class TestPipeline:
    # Skipped: we rely on pre-generated puzzles now, and live generation tests
    # are slow (minutes) with a known flaky ordering issue in solution comparison.
    pass
