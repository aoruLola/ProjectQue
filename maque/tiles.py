from __future__ import annotations

import random
from collections import Counter
from typing import Iterable

SEATS = ("E", "S", "W", "N")
SUITS = ("T", "B")
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
        suit_order = {"T": 0, "B": 1}
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


def tile_text_cn(tile: str) -> str:
    honors = {
        "EW": "东风",
        "SW": "南风",
        "WW": "西风",
        "NW": "北风",
        "RD": "红中",
        "GD": "发财",
        "WB": "白板",
    }
    if tile in honors:
        return honors[tile]

    if len(tile) == 2 and tile[0].isdigit():
        nums = {
            "1": "一",
            "2": "二",
            "3": "三",
            "4": "四",
            "5": "五",
            "6": "六",
            "7": "七",
            "8": "八",
            "9": "九",
        }
        unit = {"T": "索", "B": "筒"}.get(tile[1], "")
        if unit:
            return f"{nums.get(tile[0], tile[0])}{unit}"

    return tile


def counts_without_ghost(tiles: Iterable[str]) -> Counter[str]:
    c = Counter(tiles)
    c.pop(GHOST_TILE, None)
    return c
