from __future__ import annotations

from dataclasses import dataclass

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
    baopei_payer: str | None = None


def _pattern_multiplier(pattern: str | None) -> int:
    if pattern in {"pengpenghu", "qixiaodui"}:
        return 2
    if pattern == "haohua_qixiaodui":
        return 4
    return 1


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

    horse_bonus = len(ma_tiles)
    if horse_bonus:
        tags.append(f"ma+{horse_bonus}")

    per_loser = base * multiplier + horse_bonus
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
        final_delta_by_player=delta,
        baopei_payer=baopei_payer,
    )
