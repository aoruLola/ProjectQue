from __future__ import annotations

from dataclasses import dataclass, field

from .rules import HuResult
from .tiles import SEATS


@dataclass
class Settlement:
    winner: str
    losers: list[str]
    base: int
    multipliers: list[str]
    ma_tiles: list[str]
    final_delta_by_player: dict[str, int]
    ma_unit_scores: list[int] = field(default_factory=list)
    ma_unit_total: int = 0
    baopei_payer: str | None = None


def _pattern_multiplier(pattern: str | None) -> int:
    if pattern in {"pengpenghu", "qixiaodui"}:
        return 2
    if pattern == "haohua_qixiaodui":
        return 4
    return 1


def ma_tile_face_value(tile: str) -> int:
    honors = {"EW", "SW", "WW", "NW", "RD", "GD", "WB"}
    if tile in honors:
        return 5

    if len(tile) == 2 and tile[0].isdigit():
        n = int(tile[0])
        if n == 1:
            return 10
        return n

    return 0


def ma_tile_unit_score(tile: str) -> int:
    return ma_tile_face_value(tile) + 1


def compute_settlement(
    winner: str,
    hu_result: HuResult,
    ma_tiles: list[str],
    baopei_payer: str | None = None,
    base: int = 1,
) -> Settlement:
    losers = [seat for seat in SEATS if seat != winner]

    multiplier = _pattern_multiplier(hu_result.pattern)
    tags: list[str] = []
    if hu_result.pattern in {"pengpenghu", "qixiaodui", "haohua_qixiaodui"}:
        tags.append(hu_result.pattern)

    if hu_result.is_wugui:
        multiplier *= 2
        tags.append("wugui_x2")

    ma_unit_scores = [ma_tile_unit_score(tile) for tile in ma_tiles]
    ma_unit_total = sum(ma_unit_scores)
    if ma_unit_total:
        tags.append(f"ma_unit+{ma_unit_total}")

    per_loser = base * multiplier + ma_unit_total
    delta = {seat: 0 for seat in SEATS}

    if baopei_payer:
        total = per_loser * len(losers)
        delta[winner] += total
        delta[baopei_payer] -= total
    else:
        for loser in losers:
            delta[loser] -= per_loser
            delta[winner] += per_loser

    return Settlement(
        winner=winner,
        losers=losers,
        base=base,
        multipliers=tags,
        ma_tiles=ma_tiles,
        ma_unit_scores=ma_unit_scores,
        ma_unit_total=ma_unit_total,
        final_delta_by_player=delta,
        baopei_payer=baopei_payer,
    )
