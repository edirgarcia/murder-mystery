"""String ↔ integer mapping for CP-SAT variables.

CP-SAT requires integer domains. This module maps each category's string
values to consecutive integers (0 … n-1) and back.
"""

from __future__ import annotations


class ValueMapping:
    """Bidirectional mapping between string values and integers per category."""

    def __init__(self, schema: dict[str, list[str]]) -> None:
        self._str_to_int: dict[str, dict[str, int]] = {}
        self._int_to_str: dict[str, dict[int, str]] = {}
        for cat, values in schema.items():
            s2i = {v: i for i, v in enumerate(values)}
            i2s = {i: v for i, v in enumerate(values)}
            self._str_to_int[cat] = s2i
            self._int_to_str[cat] = i2s

    def str_to_int(self, cat: str, val: str) -> int:
        return self._str_to_int[cat][val]

    def int_to_str(self, cat: str, val_int: int) -> str:
        return self._int_to_str[cat][val_int]
