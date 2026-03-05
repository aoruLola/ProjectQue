from __future__ import annotations

import random
from collections import Counter
from typing import Iterable

SEATS = ("E", "S", "W", "N")
SUITS = ("W", "T", "B")
HONORS = ("EW", "SW", "WW", "NW", "RD", "GD", "WB")
GHOST_TILE = "WB"

SUITED_TILES = tuple(f"{n}{s}" for s in SUITS for n in range(1, 10))
ALL_TILE_TYPES = SUITED_TILES + HONORS


def is_suited(tile: str) -> bool:
    return len(tile) == 2 and tile[0].isdigit() and tile[1] in SUITS


def tile_number(tile: str) -> int:
    return int(tile[0])


def tile_suit(tile: str) -> str:
    return tile[1]


def tile_sort_key(tile: str) -> tuple[int, int, str]:
    if is_suited(tile):
        suit_order = {"W": 0, "T": 1, "B": 2}
        return (0, suit_order[tile_suit(tile)], tile_number(tile))
    honor_order = {"EW": 0, "SW": 1, "WW": 2, "NW": 3, "RD": 4, "GD": 5, "WB": 6}
    return (1, honor_order[tile], 0)


def sort_tiles(tiles: Iterable[str]) -> list[str]:
    return sorted(tiles, key=tile_sort_key)


def build_wall(seed: int | None = None) -> list[str]:
    wall: list[str] = []
    for tile in ALL_TILE_TYPES:
        wall.extend([tile] * 4)
    rng = random.Random(seed)
    rng.shuffle(wall)
    return wall


def pretty_tiles(tiles: Iterable[str]) -> str:
    return " ".join(sort_tiles(tiles))


def counts_without_ghost(tiles: Iterable[str]) -> Counter[str]:
    c = Counter(tiles)
    c.pop(GHOST_TILE, None)
    return c
