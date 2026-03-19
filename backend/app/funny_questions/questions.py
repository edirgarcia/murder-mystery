"""Load and filter questions from the JSON data file."""

from __future__ import annotations

import json
import random
from pathlib import Path
from dataclasses import dataclass

DATA_FILE = Path(__file__).parent / "data" / "questions.json"


@dataclass
class Question:
    text: str
    category: str
    spice_level: int


_ALL_QUESTIONS: list[Question] | None = None


def _load_all() -> list[Question]:
    global _ALL_QUESTIONS
    if _ALL_QUESTIONS is None:
        raw = json.loads(DATA_FILE.read_text())
        _ALL_QUESTIONS = [Question(**q) for q in raw]
    return _ALL_QUESTIONS


def get_categories() -> list[str]:
    """Return sorted list of unique categories."""
    return sorted({q.category for q in _load_all()})


def draw_questions(
    count: int,
    categories: list[str] | None = None,
    max_spice: int = 3,
) -> list[Question]:
    """Draw a random sample of questions filtered by categories and max spice level."""
    pool = _load_all()

    if categories:
        cat_set = set(categories)
        pool = [q for q in pool if q.category in cat_set]

    pool = [q for q in pool if q.spice_level <= max_spice]

    if len(pool) <= count:
        result = list(pool)
        random.shuffle(result)
        return result

    return random.sample(pool, count)
