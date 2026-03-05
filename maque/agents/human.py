from __future__ import annotations

import os

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    _COLOR_ENABLED = True
except Exception:
    _COLOR_ENABLED = False

from ..rules import DISCARD, GANG_AN, GANG_JIA, GANG_MING, HU, PASS, PENG, ActionOption
from .base import AgentDecision


class HumanAgent:
    def decide(self, seat: str, context: dict, legal_options: list[ActionOption]) -> AgentDecision:
        legal = {(o.action, o.tile) for o in legal_options}
        legal_actions = {o.action for o in legal_options}
        index_map = {str(idx): tile for idx, tile in context.get("indexed_hand", [])}

        self._render_context(seat, context)
        print("可执行动作:", ", ".join(self._format_option(o) for o in legal_options))
        print("输入示例: d 3 | d 5W | p | gm | ga 9W | gj 2T | h | pass")

        while True:
            raw = input(f"[{seat}] > ").strip().lower()
            if not raw:
                continue
            parts = raw.split()
            cmd = parts[0]

            if cmd in {"h", "hu"} and HU in legal_actions:
                return AgentDecision(action=HU, reason="玩家胡牌")

            if cmd in {"pass", "p0"} and PASS in legal_actions:
                return AgentDecision(action=PASS, reason="玩家过")

            if cmd in {"p", "peng"} and any(o.action == PENG for o in legal_options):
                tile = next(o.tile for o in legal_options if o.action == PENG)
                return AgentDecision(action=PENG, tile=tile, reason="玩家碰")

            if cmd in {"gm", "gangm"} and any(o.action == GANG_MING for o in legal_options):
                tile = next(o.tile for o in legal_options if o.action == GANG_MING)
                return AgentDecision(action=GANG_MING, tile=tile, reason="玩家明杠")

            if cmd in {"ga", "ganga"}:
                tile = parts[1].upper() if len(parts) > 1 else None
                if tile and (GANG_AN, tile) in legal:
                    return AgentDecision(action=GANG_AN, tile=tile, reason="玩家暗杠")

            if cmd in {"gj", "gangj"}:
                tile = parts[1].upper() if len(parts) > 1 else None
                if tile and (GANG_JIA, tile) in legal:
                    return AgentDecision(action=GANG_JIA, tile=tile, reason="玩家加杠")

            if cmd in {"d", "discard"} and DISCARD in legal_actions and len(parts) > 1:
                arg = parts[1]
                tile = index_map.get(arg, arg.upper())
                if (DISCARD, tile) in legal:
                    return AgentDecision(action=DISCARD, tile=tile, reason="玩家出牌")

            print("输入无效，请重试。")

    def _render_context(self, seat: str, context: dict) -> None:
        self._clear_screen()

        width = 78
        print()
        print("=" * width)
        title = self._paint(" MAQUE 麻雀实验局 ", "yellow")
        print(f"{title} | 第 {context.get('turn')} 轮 | 当前玩家 {context.get('current')} | 牌墙 {context.get('wall_count')}")
        print("-" * width)

        last = context.get("last_event")
        if last:
            tile = f" {self._pretty_tile(last['tile'])}" if last.get("tile") else ""
            frm = f" <- {last['from_player']}" if last.get("from_player") else ""
            print(f"上一步: {last['player']} {self._action_label(last['action'])}{tile}{frm}")
        else:
            print("上一步: (无)")

        print(f"你的座位: {seat}")
        print("你的手牌:")
        indexed = [f"[{idx:02d}]{self._pretty_tile(tile)}" for idx, tile in context.get("indexed_hand", [])]
        for chunk in self._chunk(indexed, 8):
            print("  " + "  ".join(chunk))

        discard_view = context.get("discard_view", {})
        recent = discard_view.get("recent_by_player", {})
        print("-" * width)
        print("弃牌区（每家最近2张）:")
        for s in ("E", "S", "W", "N"):
            tiles = [self._pretty_tile(t) for t in recent.get(s, [])]
            row = " ".join(tiles) if tiles else "--"
            print(f"  {s} | {row}")

        history_tiles = [self._pretty_tile(t) for t in discard_view.get("history_compact", [])]
        if history_tiles:
            print("历史弃牌:")
            for row in self._chunk(history_tiles, 18):
                print("  " + " ".join(row))
        else:
            print("历史弃牌: (无)")

        print("=" * width)

    @staticmethod
    def _format_option(option: ActionOption) -> str:
        action = HumanAgent._action_label(option.action)
        tile = HumanAgent._pretty_tile(option.tile) if option.tile else None
        return f"{action}:{tile}" if tile else action

    @staticmethod
    def _pretty_tile(tile: str) -> str:
        honor = {
            "EW": ("东", "yellow"),
            "SW": ("南", "yellow"),
            "WW": ("西", "yellow"),
            "NW": ("北", "yellow"),
            "RD": ("中", "red"),
            "GD": ("发", "green"),
            "WB": ("白*", "white"),
        }
        if tile in honor:
            txt, color = honor[tile]
            return HumanAgent._paint(txt, color)

        if len(tile) == 2 and tile[0].isdigit():
            n, suit = tile[0], tile[1]
            if suit == "W":
                return HumanAgent._paint(f"{n}万", "red")
            if suit == "T":
                return HumanAgent._paint(f"{n}条", "green")
            if suit == "B":
                return HumanAgent._paint(f"{n}筒", "cyan")
        return tile

    @staticmethod
    def _chunk(items: list[str], size: int) -> list[list[str]]:
        return [items[i : i + size] for i in range(0, len(items), size)]

    @staticmethod
    def _clear_screen() -> None:
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def _paint(text: str, color: str) -> str:
        if not _COLOR_ENABLED:
            return text
        color_map = {
            "red": Fore.RED,
            "green": Fore.GREEN,
            "yellow": Fore.YELLOW,
            "cyan": Fore.CYAN,
            "white": Fore.WHITE,
        }
        return f"{color_map.get(color, '')}{text}{Style.RESET_ALL}"

    @staticmethod
    def _action_label(action: str) -> str:
        mapping = {
            "DRAW": "摸牌",
            "DISCARD": "出牌",
            "PENG": "碰",
            "GANG_MING": "明杠",
            "GANG_AN": "暗杠",
            "GANG_JIA": "加杠",
            "HU": "胡",
            "PASS": "过",
        }
        return mapping.get(action, action)
