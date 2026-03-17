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
from app.puzzle.pipeline import generate_puzzle
from app.puzzle.value_mapping import ValueMapping

import random


class TestSchema:
    def test_get_schema_returns_correct_size(self):
        schema = get_schema(4)
        for cat, vals in schema.items():
            assert len(vals) == 4

    def test_get_schema_invalid_n(self):
        with pytest.raises(ValueError):
            get_schema(2)
        with pytest.raises(ValueError):
            get_schema(11)

    def test_category_scaling(self):
        # n <= 4: 5 categories + name = 6 total
        assert len(get_active_categories(3)) == 5
        assert len(get_active_categories(4)) == 5
        # n <= 6: 4 categories + name = 5 total
        assert len(get_active_categories(5)) == 4
        assert len(get_active_categories(6)) == 4
        # n <= 10: 3 categories + name = 4 total
        assert len(get_active_categories(7)) == 3
        assert len(get_active_categories(10)) == 3

    def test_weapon_always_included(self):
        for n in range(3, 11):
            cats = get_active_categories(n)
            assert WEAPON_CATEGORY in cats

    def test_schema_7_succeeds(self):
        schema = get_schema(7)
        # 3 puzzle categories + name = 4
        assert len(schema) == 4
        assert NAME_CATEGORY in schema
        assert WEAPON_CATEGORY in schema


class TestGenerator:
    def test_generate_solution_has_correct_shape(self):
        sol = generate_solution(4)
        # n=4 → 5 puzzle categories + name = 6
        assert len(sol) == 6
        for vals in sol.values():
            assert len(vals) == 4

    def test_generate_solution_shape_varies_by_n(self):
        sol7 = generate_solution(7)
        # n=7 → 3 puzzle categories + name = 4
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
        return generate_solution(4, rng=random.Random(42))

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
        n = 3
        sol = generate_solution(n, rng=random.Random(1))
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
        sol = generate_solution(4, rng)
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
            sol = generate_solution(4, rng)
            _, weapon, _ = generate_murder_clues(sol, rng)
            weapons.add(weapon)
        assert len(weapons) > 1, "Weapon should vary across different seeds"


class TestPipeline:
    @pytest.mark.parametrize("n,seed", [(3, 42), (4, 99), (7, 42), (10, 7)])
    def test_generate_puzzle_produces_unique_solution(self, n, seed):
        puzzle = generate_puzzle(n, seed=seed, max_attempts=10)
        assert puzzle.n == n
        assert puzzle.murderer_name in puzzle.solution[NAME_CATEGORY]
        assert puzzle.murder_weapon in puzzle.solution[WEAPON_CATEGORY]
        assert len(puzzle.cards) == n
        # Verify uniqueness
        assert is_unique(n, puzzle.clues)
        unique_sol = get_unique_solution(n, puzzle.clues)
        assert unique_sol == puzzle.solution

    def test_murder_clues_on_separate_cards(self):
        puzzle = generate_puzzle(4, seed=99)
        # Each murder clue should be on a different card
        murder_texts = {c.render() for c in puzzle.murder_clues}
        for card in puzzle.cards:
            card_murder = [c for c in card.clues if c.render() in murder_texts]
            assert len(card_murder) <= 1, "Multiple murder clues on same card"

    @pytest.mark.parametrize("n,seed", [(4, 99), (7, 42), (10, 7)])
    def test_clue_counts_balanced(self, n, seed):
        puzzle = generate_puzzle(n, seed=seed, max_attempts=10)
        sizes = [len(card.clues) for card in puzzle.cards]
        assert max(sizes) - min(sizes) <= 1, f"Clue counts too uneven: {sizes}"
