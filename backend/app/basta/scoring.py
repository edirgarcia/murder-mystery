"""Pure scoring functions for Basta rounds."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass
class CategoryScore:
    category: str
    answers: dict[str, str]
    points: dict[str, int]
    invalid_players: list[str]
    vetoed_players: list[str]


@dataclass
class RoundScore:
    points: dict[str, int]
    category_results: list[CategoryScore]


def normalize_text(value: str) -> str:
    """Normalize for accent-insensitive, case-insensitive comparisons."""
    decomposed = unicodedata.normalize("NFD", value.strip())
    without_accents = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents).casefold()


def answer_starts_with_letter(answer: str, letter: str) -> bool:
    normalized_answer = normalize_text(answer)
    normalized_letter = normalize_text(letter)
    return bool(normalized_answer) and normalized_answer.startswith(normalized_letter)


def points_for_match_count(count: int) -> int:
    if count <= 0:
        return 0
    if count == 1:
        return 100
    if count == 2:
        return 50
    return 25


def score_round(
    answers: dict[str, dict[str, str]],
    player_ids: list[str],
    categories: list[str],
    letter: str,
    vetoed_answers: dict[str, set[str]] | None = None,
) -> RoundScore:
    """Score a Basta round.

    Blank answers and answers that do not start with the round letter score 0.
    Valid answers are grouped case/accent-insensitively within each category:
    unique answers get 100, answers shared by exactly two players get 50 each,
    and answers shared by three or more players get 25 each.
    """
    total_points = {pid: 0 for pid in player_ids}
    category_results: list[CategoryScore] = []

    for category in categories:
        submitted_answers: dict[str, str] = {}
        valid_groups: dict[str, list[str]] = {}
        vetoed_players = set(vetoed_answers.get(category, set())) if vetoed_answers else set()
        invalid_players: list[str] = []

        for pid in player_ids:
            answer = answers.get(pid, {}).get(category, "").strip()
            submitted_answers[pid] = answer
            if pid in vetoed_players:
                invalid_players.append(pid)
            elif answer_starts_with_letter(answer, letter):
                valid_groups.setdefault(normalize_text(answer), []).append(pid)
            else:
                invalid_players.append(pid)

        category_points = {pid: 0 for pid in player_ids}
        for grouped_players in valid_groups.values():
            points = points_for_match_count(len(grouped_players))
            for pid in grouped_players:
                category_points[pid] = points
                total_points[pid] += points

        category_results.append(
            CategoryScore(
                category=category,
                answers=submitted_answers,
                points=category_points,
                invalid_players=invalid_players,
                vetoed_players=list(vetoed_players),
            )
        )

    return RoundScore(points=total_points, category_results=category_results)
