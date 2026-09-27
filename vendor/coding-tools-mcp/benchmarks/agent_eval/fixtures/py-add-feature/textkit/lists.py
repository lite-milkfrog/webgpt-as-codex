"""List helpers."""

from __future__ import annotations

from typing import Iterable, TypeVar

T = TypeVar("T")


def flatten(nested: Iterable[Iterable[T]]) -> list[T]:
    return [item for group in nested for item in group]
