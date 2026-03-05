from __future__ import annotations

from ..state import ActionEvent, GameState
from ..tiles import sort_tiles


def indexed_hand(hand: list[str]) -> list[tuple[int, str]]:
    ordered = sort_tiles(hand)
    return [(idx + 1, tile) for idx, tile in enumerate(ordered)]


def render_state(state: GameState, human_seat: str, last_event: ActionEvent | None) -> str:
    player = state.players[human_seat]
    lines: list[str] = []

    lines.append(f"Turn: {state.turn}  Current: {state.current}  Wall: {len(state.wall)}")
    if last_event:
        tile_part = f" {last_event.tile}" if last_event.tile else ""
        from_part = f" <- {last_event.from_player}" if last_event.from_player else ""
        lines.append(f"Last: {last_event.player} {last_event.action}{tile_part}{from_part}")
    else:
        lines.append("Last: (none)")

    idx_hand = indexed_hand(player.hand)
    hand_str = " ".join(f"[{idx}]{tile}" for idx, tile in idx_hand)
    lines.append(f"Hand({human_seat}): {hand_str}")

    lines.append("Discards:")
    for seat in ("E", "S", "W", "N"):
        recent = " ".join(state.discard_view.recent_by_player[seat])
        lines.append(f"{seat}: [{recent}]")
    lines.append(f"History: {' '.join(state.discard_view.history_compact)}")

    return "\n".join(lines)


def render_settlement(settlement) -> str:
    lines = ["Settlement:"]
    lines.append(f"Winner: {settlement.winner}")
    if settlement.baopei_payer:
        lines.append(f"Baopei payer: {settlement.baopei_payer}")
    lines.append(f"Multipliers: {', '.join(settlement.multipliers) if settlement.multipliers else 'none'}")
    lines.append(f"Ma tiles: {' '.join(settlement.ma_tiles) if settlement.ma_tiles else '(none)'}")
    lines.append("Delta:")
    for seat, value in settlement.final_delta_by_player.items():
        lines.append(f"  {seat}: {value:+d}")
    return "\n".join(lines)
