"""Split a sequence into fixed-size chunks."""

from __future__ import annotations


def chunk(items: list[int], size: int) -> list[list[int]]:
    if size < 1:
        raise ValueError("size must be >= 1")
    chunks: list[list[int]] = []
    for start in range(0, len(items) - size + 1, size):
        chunks.append(items[start : start + size])
    return chunks
