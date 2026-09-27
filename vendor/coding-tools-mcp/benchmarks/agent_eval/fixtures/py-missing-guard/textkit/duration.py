"""Parse short duration strings such as "90s", "2m", or "1h"."""

from __future__ import annotations

UNITS = {"s": 1, "m": 60, "h": 3600}


def parse_duration(text: str) -> int:
    unit = text[-1]
    if unit not in UNITS:
        raise ValueError(f"unknown duration unit: {unit}")
    return int(text[:-1]) * UNITS[unit]
