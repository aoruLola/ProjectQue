from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from .state import PlayerState
from .tiles import ALL_TILE_TYPES, GHOST_TILE, SEATS, is_suited, tile_number, tile_suit


DRAW = "DRAW"
DISCARD = "DISCARD"
PENG = "PENG"
GANG_MING = "GANG_MING"
GANG_AN = "GANG_AN"
GANG_JIA = "GANG_JIA"
HU = "HU"
PASS = "PASS"

_NON_GHOST_TILES = tuple(tile for tile in ALL_TILE_TYPES if tile != GHOST_TILE)


@dataclass
class ActionOption:
    action: str
    tile: str | None = None


@dataclass
class HuResult:
    is_hu: bool
    pattern: str | None = None
    is_wugui: bool = False
    source: str = "zimo"
    baopei_info: dict[str, str] | None = None


def next_seat(seat: str, step: int = 1) -> str:
    idx = SEATS.index(seat)
    return SEATS[(idx + step) % 4]


def claim_order(from_seat: str) -> list[str]:
    return [next_seat(from_seat, i) for i in (1, 2, 3)]


def _count_ghosts(tiles: Iterable[str]) -> int:
    return sum(1 for t in tiles if t == GHOST_TILE)


def _counts_key(counter: Counter[str]) -> tuple[int, ...]:
    return tuple(counter.get(tile, 0) for tile in _NON_GHOST_TILES)


def _subtract(counter: Counter[str], tile: str, amount: int = 1) -> None:
    counter[tile] -= amount
    if counter[tile] <= 0:
        counter.pop(tile, None)


@lru_cache(maxsize=200000)
def _can_form_groups_cached(key: tuple[int, ...], ghosts: int, allow_sequences: bool) -> bool:
    counter = Counter({tile: key[idx] for idx, tile in enumerate(_NON_GHOST_TILES) if key[idx] > 0})

    def solve(c: Counter[str], g: int) -> bool:
        if not c:
            return True

        tile = min(c.keys(), key=lambda t: _NON_GHOST_TILES.index(t))
        count = c[tile]

        need_triplet = max(0, 3 - count)
        if g >= need_triplet:
            c2 = c.copy()
            _subtract(c2, tile, min(3, count))
            if solve(c2, g - need_triplet):
                return True

        if allow_sequences and is_suited(tile):
            n = tile_number(tile)
            suit = tile_suit(tile)
            if n <= 7:
                t2 = f"{n + 1}{suit}"
                t3 = f"{n + 2}{suit}"
                c2 = c.copy()
                _subtract(c2, tile, 1)
                need = 0
                for t in (t2, t3):
                    if c2.get(t, 0) > 0:
                        _subtract(c2, t, 1)
                    else:
                        need += 1
                if g >= need and solve(c2, g - need):
                    return True

        return False

    return solve(counter, ghosts)


def _can_standard_hu(tiles: list[str], allow_sequences: bool = True) -> bool:
    counter = Counter(t for t in tiles if t != GHOST_TILE)
    ghosts = _count_ghosts(tiles)

    pair_candidates = set(counter.keys())
    if ghosts >= 2:
        pair_candidates.add("__GHOST_PAIR__")

    for tile in pair_candidates:
        c2 = counter.copy()
        g2 = ghosts

        if tile == "__GHOST_PAIR__":
            g2 -= 2
        else:
            need = max(0, 2 - c2.get(tile, 0))
            if need > g2:
                continue
            g2 -= need
            _subtract(c2, tile, min(2, c2.get(tile, 0)))

        if _can_form_groups_cached(_counts_key(c2), g2, allow_sequences):
            return True

    return False


def _check_qixiaodui(tiles: list[str]) -> tuple[bool, bool]:
    if len(tiles) != 14:
        return False, False

    counter = Counter(t for t in tiles if t != GHOST_TILE)
    ghosts = _count_ghosts(tiles)

    pairs = sum(cnt // 2 for cnt in counter.values())
    singles = sum(cnt % 2 for cnt in counter.values())

    if ghosts < singles:
        return False, False

    ghosts_left = ghosts - singles
    pairs += singles + (ghosts_left // 2)

    is_valid = pairs >= 7
    is_haohua = any(cnt == 4 for cnt in counter.values())
    return is_valid, is_haohua


def is_pengpeng_hu(tiles: list[str]) -> bool:
    return _can_standard_hu(tiles, allow_sequences=False)


def evaluate_hu(
    tiles: list[str],
    source: str = "zimo",
    baopei_info: dict[str, str] | None = None,
) -> HuResult:
    is_wugui = GHOST_TILE not in tiles

    qxd, haohua = _check_qixiaodui(tiles)
    if qxd:
        return HuResult(
            is_hu=True,
            pattern="haohua_qixiaodui" if haohua else "qixiaodui",
            is_wugui=is_wugui,
            source=source,
            baopei_info=baopei_info,
        )

    if _can_standard_hu(tiles, allow_sequences=True):
        pattern = "pengpenghu" if is_pengpeng_hu(tiles) else "normal"
        return HuResult(
            is_hu=True,
            pattern=pattern,
            is_wugui=is_wugui,
            source=source,
            baopei_info=baopei_info,
        )

    return HuResult(is_hu=False, is_wugui=is_wugui, source=source, baopei_info=baopei_info)


def legal_actions_after_draw(player: PlayerState) -> list[ActionOption]:
    options: list[ActionOption] = []
    if evaluate_hu(player.hand).is_hu:
        options.append(ActionOption(HU))

    counter = Counter(player.hand)
    for tile, cnt in counter.items():
        if cnt >= 4:
            options.append(ActionOption(GANG_AN, tile))

    peng_tiles = {meld.tiles[0] for meld in player.melds if meld.kind == PENG}
    for tile in peng_tiles:
        if counter.get(tile, 0) >= 1:
            options.append(ActionOption(GANG_JIA, tile))

    for tile in sorted(counter.keys()):
        options.append(ActionOption(DISCARD, tile))

    return options


def legal_actions_on_discard(player: PlayerState, tile: str) -> list[ActionOption]:
    counter = Counter(player.hand)
    options = [ActionOption(PASS)]
    if counter.get(tile, 0) >= 3:
        options.append(ActionOption(GANG_MING, tile))
    if counter.get(tile, 0) >= 2:
        options.append(ActionOption(PENG, tile))
    return options


def legal_actions_on_qianggang(player: PlayerState, gang_tile: str) -> list[ActionOption]:
    options = [ActionOption(PASS)]
    if evaluate_hu(player.hand + [gang_tile], source="qianggang").is_hu:
        options.append(ActionOption(HU, gang_tile))
    return options


def remove_tiles(hand: list[str], tile: str, n: int) -> None:
    for _ in range(n):
        hand.remove(tile)


def upgrade_peng_to_jiagang(player: PlayerState, tile: str) -> bool:
    for meld in player.melds:
        if meld.kind == PENG and meld.tiles[0] == tile:
            meld.kind = GANG_JIA
            meld.tiles = [tile] * 4
            return True
    return False
