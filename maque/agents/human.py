from __future__ import annotations

import os
import sys
from typing import Any

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    _COLOR_ENABLED = True
except Exception:
    _COLOR_ENABLED = False

try:
    from rich import box as rich_box
    from rich.columns import Columns
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    _RICH_ENABLED = True
except Exception:
    _RICH_ENABLED = False

from ..rules import DISCARD, GANG_AN, GANG_JIA, GANG_MING, HU, PASS, PENG, ActionOption
from ..tiles import sort_tiles, tile_text_cn
from .base import AgentDecision


class HumanAgent:
    def __init__(self) -> None:
        self.console = Console() if _RICH_ENABLED else None

    def decide(self, seat: str, context: dict, legal_options: list[ActionOption]) -> AgentDecision:
        self._flush_stale_input()
        while True:
            entry = self._pick_action_with_arrows(seat, context, legal_options)

            if entry["kind"] == "discard":
                tile = self._pick_discard_tile_with_arrows(seat, context)
                if tile is None:
                    continue
                return AgentDecision(action=DISCARD, tile=tile, reason="方向键选择出牌")

            option = entry["option"]
            return AgentDecision(
                action=option.action,
                tile=option.tile,
                reason="方向键选择动作",
            )

    @staticmethod
    def _drain_windows_input_buffer(msvcrt_mod: Any) -> int:
        drained = 0
        while msvcrt_mod.kbhit():
            msvcrt_mod.getch()
            drained += 1
        return drained

    def _flush_stale_input(self) -> None:
        if os.name != "nt":
            return
        try:
            import msvcrt

            self._drain_windows_input_buffer(msvcrt)
        except Exception:
            # Ignore platform/terminal-specific issues and continue.
            return

    def render_view(
        self,
        seat: str,
        context: dict,
        prompt: str | None = None,
        thinking_seat: str | None = None,
        thinking_text: str | None = None,
    ) -> None:
        self._render_context(
            seat,
            context,
            selected_tile_index=None,
            prompt=prompt,
            thinking_seat=thinking_seat,
            thinking_text=thinking_text,
        )

    def render_hu_wait_screen(
        self,
        *,
        winner_seat: str,
        winner_hand: list[str],
    ) -> None:
        if _RICH_ENABLED and self.console is not None:
            self._render_hu_wait_screen_rich(winner_seat=winner_seat, winner_hand=winner_hand)
            return

        self._clear_screen()
        lines = self._build_hu_wait_lines(winner_seat=winner_seat, winner_hand=winner_hand)
        print("\n".join(lines))

    def _render_hu_wait_screen_rich(self, *, winner_seat: str, winner_hand: list[str]) -> None:
        assert self.console is not None
        self.console.clear()
        self.console.rule("胡牌", style="bright_yellow")
        self.console.print(Panel(Text(f"{self._seat_cn(winner_seat)}({winner_seat}) 胡牌", style="bold yellow"), border_style="yellow"))
        winner_ascii = "\n".join(self._render_box_lines_raw(sort_tiles(winner_hand)))
        self.console.print(Panel(Text(winner_ascii), title="赢家手牌", border_style="yellow"))
        formula = "\n".join(self._ma_formula_lines())
        self.console.print(Panel(Text(formula), title="买马计算公式", border_style="cyan"))
        self.console.print(Text("按 Enter 进入买马", style="bright_green"))

    @staticmethod
    def _build_hu_wait_lines(
        *,
        winner_seat: str,
        winner_hand: list[str],
    ) -> list[str]:
        lines: list[str] = []
        lines.append("=== 胡牌 ===")
        lines.append(f"{HumanAgent._seat_cn(winner_seat)}({winner_seat}) 胡牌")
        lines.append("")
        lines.append("赢家手牌:")
        for row in HumanAgent._render_box_lines_raw(sort_tiles(winner_hand)):
            lines.append(f"  {row}")
        lines.append("")
        lines.append("买马计算公式:")
        lines.extend(HumanAgent._ma_formula_lines())
        lines.append("")
        lines.append("按 Enter 进入买马")
        return lines

    def render_ma_screen(
        self,
        *,
        winner_seat: str,
        winner_hand: list[str],
        ma_tiles: list[str],
        ma_unit_scores: list[int],
        round_delta: dict[str, int] | None = None,
        leaderboard: dict[str, int],
        self_seat: str,
        self_hand: list[str],
    ) -> None:
        if _RICH_ENABLED and self.console is not None:
            self._render_ma_screen_rich(
                winner_seat=winner_seat,
                winner_hand=winner_hand,
                ma_tiles=ma_tiles,
                ma_unit_scores=ma_unit_scores,
                round_delta=round_delta,
                leaderboard=leaderboard,
                self_seat=self_seat,
                self_hand=self_hand,
            )
            return

        self._clear_screen()
        lines = self._build_ma_screen_lines(
            winner_seat=winner_seat,
            winner_hand=winner_hand,
            ma_tiles=ma_tiles,
            ma_unit_scores=ma_unit_scores,
            round_delta=round_delta,
            leaderboard=leaderboard,
            self_seat=self_seat,
            self_hand=self_hand,
        )
        print("\n".join(lines))

    def _render_ma_screen_rich(
        self,
        *,
        winner_seat: str,
        winner_hand: list[str],
        ma_tiles: list[str],
        ma_unit_scores: list[int],
        round_delta: dict[str, int] | None = None,
        leaderboard: dict[str, int],
        self_seat: str,
        self_hand: list[str],
    ) -> None:
        assert self.console is not None
        self.console.clear()
        self.console.rule("买马结算", style="bright_green")

        top_ascii = "\n".join(self._render_box_lines_raw(sort_tiles(winner_hand)))
        self.console.print(Panel(Text(top_ascii), title=f"赢家手牌 ({self._seat_cn(winner_seat)} {winner_seat})", border_style="yellow"))

        ma_table = Table(show_header=True, header_style="bold cyan")
        ma_table.add_column("马牌")
        ma_table.add_column("单位分", justify="right")
        ma_table.add_column("x100", justify="right")
        for idx, tile in enumerate(ma_tiles):
            unit = ma_unit_scores[idx] if idx < len(ma_unit_scores) else 0
            ma_table.add_row(self._tile_text_cn(tile), f"+{unit}", f"+{unit * 100}")
        ma_total = sum(ma_unit_scores)
        ma_table.add_row("合计", f"+{ma_total}", f"+{ma_total * 100}")

        lb_table = Table(show_header=True, header_style="bold magenta")
        lb_table.add_column("排行")
        lb_table.add_column("本局", justify="right")
        lb_table.add_column("总分", justify="right")
        current = round_delta or {}
        for seat in ("E", "S", "W", "N"):
            lb_table.add_row(
                f"{self._seat_cn(seat)}({seat})",
                f"{current.get(seat, 0):+d}",
                f"{leaderboard.get(seat, 0):+d}",
            )

        middle = Columns(
            [
                Panel(ma_table, title="马牌", border_style="cyan"),
                Panel(lb_table, title="排行榜", border_style="magenta"),
            ],
            expand=True,
            equal=True,
        )
        self.console.print(middle)

        bottom_ascii = "\n".join(self._render_box_lines_raw(sort_tiles(self_hand)))
        self.console.print(Panel(Text(bottom_ascii), title=f"自己手牌 ({self._seat_cn(self_seat)} {self_seat})", border_style="green"))

    @staticmethod
    def _build_ma_screen_lines(
        *,
        winner_seat: str,
        winner_hand: list[str],
        ma_tiles: list[str],
        ma_unit_scores: list[int],
        round_delta: dict[str, int] | None = None,
        leaderboard: dict[str, int],
        self_seat: str,
        self_hand: list[str],
    ) -> list[str]:
        lines: list[str] = []
        lines.append("=== 买马结算 ===")
        lines.append(f"赢家手牌 ({HumanAgent._seat_cn(winner_seat)} {winner_seat}):")
        for row in HumanAgent._render_box_lines_raw(sort_tiles(winner_hand)):
            lines.append(f"  {row}")
        lines.append("")
        lines.append("马牌:")
        if ma_tiles:
            for idx, tile in enumerate(ma_tiles):
                unit = ma_unit_scores[idx] if idx < len(ma_unit_scores) else 0
                lines.append(f"  {tile_text_cn(tile)}  +{unit} (x100=+{unit * 100})")
        else:
            lines.append("  (无)")
        lines.append(f"  合计 +{sum(ma_unit_scores)} (x100=+{sum(ma_unit_scores) * 100})")
        lines.append("")
        lines.append("本局分数:")
        current = round_delta or {}
        for seat in ("E", "S", "W", "N"):
            lines.append(f"  {HumanAgent._seat_cn(seat)}({seat}): {current.get(seat, 0):+d}")
        lines.append("")
        lines.append("排行榜:")
        for seat in ("E", "S", "W", "N"):
            lines.append(f"  {HumanAgent._seat_cn(seat)}({seat}): {leaderboard.get(seat, 0):+d}")
        lines.append("")
        lines.append(f"自己手牌 ({HumanAgent._seat_cn(self_seat)} {self_seat}):")
        for row in HumanAgent._render_box_lines_raw(sort_tiles(self_hand)):
            lines.append(f"  {row}")
        return lines

    def _pick_action_with_arrows(self, seat: str, context: dict, legal_options: list[ActionOption]) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []
        seen: set[tuple[str, str | None]] = set()
        has_discard = False

        for opt in legal_options:
            key = (opt.action, opt.tile)
            if key in seen:
                continue
            seen.add(key)

            if opt.action == DISCARD:
                has_discard = True
                continue

            label = self._format_option(opt)
            entries.append({"kind": "action", "option": opt, "label": label})

        if has_discard:
            entries.append({"kind": "discard", "option": None, "label": "出牌"})

        if not entries:
            return {"kind": "action", "option": ActionOption(PASS), "label": "过"}

        if len(entries) == 1:
            return entries[0]

        idx = 0
        while True:
            prompt = "方向键选择动作：←/→ 切换，Enter 确认"
            self._render_context(
                seat,
                context,
                selected_tile_index=None,
                prompt=prompt,
                thinking_seat=None,
                thinking_text=None,
            )
            self._render_action_bar(entries, idx)

            key = self._read_key()
            if key in {"left", "up"}:
                idx = (idx - 1) % len(entries)
                continue
            if key in {"right", "down"}:
                idx = (idx + 1) % len(entries)
                continue
            if key == "enter":
                return entries[idx]

    def _pick_discard_tile_with_arrows(self, seat: str, context: dict) -> str | None:
        indexed_hand: list[tuple[int, str]] = context.get("indexed_hand", [])
        if not indexed_hand:
            raise RuntimeError("手牌为空，无法出牌")

        pos = 0
        while True:
            selected_idx, selected_tile = indexed_hand[pos]
            prompt = (
                "方向键选择要出的牌：←/→ 切换，Enter 确认，Esc 返回动作选择"
                f" | 当前: {self._tile_text_cn(selected_tile)}"
            )
            self._render_context(
                seat,
                context,
                selected_tile_index=selected_idx,
                prompt=prompt,
                thinking_seat=None,
                thinking_text=None,
            )

            key = self._read_key()
            if key in {"left", "up"}:
                pos = (pos - 1) % len(indexed_hand)
                continue
            if key in {"right", "down"}:
                pos = (pos + 1) % len(indexed_hand)
                continue
            if key == "enter":
                return selected_tile
            if key == "esc":
                return None

    def _render_action_bar(self, entries: list[dict[str, Any]], selected: int) -> None:
        labels: list[str] = []
        for i, entry in enumerate(entries):
            txt = f" {entry['label']} "
            if i == selected:
                if _RICH_ENABLED and self.console is not None:
                    labels.append(f"[black on yellow]{txt}[/]")
                else:
                    labels.append(f">{txt}<")
            else:
                labels.append(txt)

        line = " | ".join(labels)
        if _RICH_ENABLED and self.console is not None:
            self.console.print(line)
        else:
            print(line)

    def _render_context(
        self,
        seat: str,
        context: dict,
        selected_tile_index: int | None,
        prompt: str | None,
        thinking_seat: str | None,
        thinking_text: str | None,
    ) -> None:
        if _RICH_ENABLED and self.console is not None:
            self._render_context_rich(
                seat,
                context,
                selected_tile_index,
                prompt,
                thinking_seat,
                thinking_text,
            )
            return
        self._render_context_plain(
            seat,
            context,
            selected_tile_index,
            prompt,
            thinking_seat,
            thinking_text,
        )

    def _render_context_rich(
        self,
        seat: str,
        context: dict,
        selected_tile_index: int | None,
        prompt: str | None,
        thinking_seat: str | None,
        thinking_text: str | None,
    ) -> None:
        assert self.console is not None
        self.console.clear()

        status_label, status_style = self._llm_status_badge(context.get("llm_status"))
        header_bar = Table.grid(expand=True)
        header_bar.add_column(justify="left")
        header_bar.add_column(justify="right")
        header_bar.add_row(
            Text(" MAQUE 麻雀实验局 ", style="bold yellow"),
            Text(f"LLM: {status_label}", style=status_style),
        )
        self.console.print(header_bar)
        self.console.rule(
            f"第 {context.get('turn')} 轮 | 庄家 {self._seat_cn(context.get('dealer'))} | 当前玩家 {self._seat_cn(context.get('current'))} | 牌墙 {context.get('wall_count')}",
            style="bright_blue",
        )
        llm_error = str((context.get("llm_status") or {}).get("last_error") or "").strip()
        if llm_error:
            self.console.print(Text(f"LLM原因: {llm_error}", style="red"))
        self.console.print(Text(f"你的风位: {self._seat_cn(seat)} ({seat})", style="bold cyan"))

        last = context.get("last_event")
        current_discard = self._resolve_current_discard(seat, context.get("last_discard"), last)
        if last and self._should_show_last_event(seat, last):
            tile = f" {self._pretty_tile(last['tile'])}" if last.get("tile") else ""
            frm = f" <- {self._seat_cn(last['from_player'])}" if last.get("from_player") else ""
            self.console.print(f"上一步: {self._seat_cn(last['player'])} {self._action_label(last['action'])}{tile}{frm}")
        else:
            self.console.print("上一步: (无)")

        discard_view = context.get("discard_view", {})
        recent = discard_view.get("recent_by_player", {})
        history_tiles = discard_view.get("history_compact", [])
        public_melds = context.get("public_melds", {})
        self.console.print(
            self._build_discard_panel(
                recent,
                history_tiles,
                thinking_seat,
                thinking_text,
                context.get("dealer"),
                public_melds,
                seat,
                current_discard,
            )
        )
        self.console.print(self._build_my_meld_panel(public_melds, seat))
        self.console.print(
            self._build_hand_panel(
                seat,
                context.get("indexed_hand", []),
                selected_tile_index,
                context.get("draw_split_index"),
            )
        )

        if prompt:
            self.console.print(Panel(prompt, border_style="yellow"))

    def _build_hand_panel(
        self,
        seat: str,
        indexed_hand: list[tuple[int, str]],
        selected_tile_index: int | None,
        draw_split_index: int | None,
    ) -> Any:
        if not indexed_hand:
            return Panel("(空)", title=f"你的手牌 ({self._seat_cn(seat)} {seat})", border_style="cyan")

        blocks: list[Any] = []
        name_row = Table.grid(padding=(0, 0))
        tile_row = Table.grid(padding=(0, 0))
        column_widths: list[int] = []
        for pos in range(len(indexed_hand)):
            if draw_split_index is not None and pos == draw_split_index:
                column_widths.append(2)
            column_widths.append(7)
        for width in column_widths:
            name_row.add_column(justify="center", width=width)
            tile_row.add_column(justify="center", width=width)

        name_cells: list[Any] = []
        tile_cells: list[Any] = []
        for pos, (idx, tile) in enumerate(indexed_hand):
            if draw_split_index is not None and pos == draw_split_index:
                name_cells.append(Text(" ", style="dim"))
                tile_cells.append(Text(" ", style="dim"))
            name_style = "bold yellow" if idx == selected_tile_index else "dim"
            name_cells.append(Text(self._tile_text_cn(tile), style=name_style, justify="center"))
            tile_cells.append(self._tile_panel(tile, highlight=(idx == selected_tile_index)))

        name_row.add_row(*name_cells)
        tile_row.add_row(*tile_cells)
        blocks.append(name_row)
        blocks.append(tile_row)

        return Panel(Group(*blocks), title=f"你的手牌 ({self._seat_cn(seat)} {seat})", border_style="cyan")

    def _build_discard_panel(
        self,
        recent_by_player: dict[str, list[str]],
        history_tiles: list[str],
        thinking_seat: str | None,
        thinking_text: str | None,
        dealer: str | None,
        public_melds: dict[str, list[dict]],
        self_seat: str,
        current_discard: dict[str, str] | None,
    ) -> Any:
        seat_table = Table.grid(padding=(0, 1))
        seat_table.add_column(style="bold yellow", width=8)
        seat_table.add_column()
        seat_table.add_column(justify="right", width=14)
        seat_table.add_column(justify="right", width=30)

        for s in ("E", "S", "W", "N"):
            tiles = recent_by_player.get(s, [])
            seat_label = f"{self._seat_cn(s)}(庄)" if dealer == s else self._seat_cn(s)
            thinking_cell = f"[{thinking_text or '思考中'}]" if thinking_seat == s else ""
            meld_summary = ""
            if s != self_seat:
                summary = self._format_meld_summary(public_melds, s)
                meld_summary = "" if summary == "(无)" else summary
            if not tiles:
                seat_table.add_row(
                    seat_label,
                    Text("(无)", style="dim"),
                    Text(thinking_cell, style="yellow" if thinking_cell else "dim"),
                    Text(meld_summary, style="cyan" if meld_summary else "dim"),
                )
            else:
                seat_table.add_row(
                    seat_label,
                    self._tiles_text_rich(tiles),
                    Text(thinking_cell, style="yellow" if thinking_cell else "dim"),
                    Text(meld_summary, style="cyan" if meld_summary else "dim"),
                )

        if history_tiles:
            history_render = self._tiles_text_rich(history_tiles)
        else:
            history_render = Text("(无)", style="dim")

        main_group = Group(
            Text("弃牌区", style="bold"),
            seat_table,
            Text(""),
            Text("历史弃牌", style="bold"),
            history_render,
        )
        main_panel = Panel(main_group, border_style="magenta")
        if not current_discard:
            return main_panel

        side_panel = self._build_current_discard_panel(current_discard)
        return Columns([main_panel, side_panel], expand=True, equal=False)

    def _build_current_discard_panel(self, current_discard: dict[str, str]) -> Any:
        actor = current_discard.get("player", "")
        tile = current_discard.get("tile", "")
        actor_line = Text(f"{self._seat_cn(actor)} 出牌", style="bold yellow")
        tile_name = Text(self._tile_text_cn(tile), style=self._rich_style(self._tile_color(tile)))
        tile_panel = self._tile_panel(tile, highlight=False) if tile else Text("(无)", style="dim")
        content = Group(actor_line, tile_name, Text(""), tile_panel)
        return Panel(content, title="当前打出", border_style="bright_yellow", width=18)

    def _build_my_meld_panel(self, public_melds: dict[str, list[dict]], seat: str) -> Any:
        summary = self._format_meld_summary(public_melds, seat)
        return Panel(Text(summary, style="cyan"), title="我的碰杠区", border_style="green")

    def _tile_panel(self, tile: str, highlight: bool) -> Any:
        rows, color = self._tile_face_rows(tile)
        if _RICH_ENABLED:
            rich_style = self._rich_style(color)
            content = Text("\n".join(rows), style=rich_style)
            border = "bright_yellow" if highlight else rich_style
            return Panel.fit(
                content,
                box=rich_box.SQUARE,
                padding=(0, 0),
                width=7,
                border_style=border,
            )
        return "\n".join(self._tile_box(tile))

    def _render_context_plain(
        self,
        seat: str,
        context: dict,
        selected_tile_index: int | None,
        prompt: str | None,
        thinking_seat: str | None,
        thinking_text: str | None,
    ) -> None:
        self._clear_screen()

        width = 78
        print()
        print("=" * width)
        status_label, _ = self._llm_status_badge(context.get("llm_status"))
        print(f"{('LLM: ' + status_label):>{width}}")
        llm_error = str((context.get("llm_status") or {}).get("last_error") or "").strip()
        if llm_error:
            print(f"{('LLM原因: ' + llm_error):>{width}}")
        title = self._paint(" MAQUE 麻雀实验局 ", "yellow")
        print(
            f"{title} | 第 {context.get('turn')} 轮 | 庄家 {self._seat_cn(context.get('dealer'))} | 当前玩家 {self._seat_cn(context.get('current'))} | 牌墙 {context.get('wall_count')}"
        )
        print("-" * width)

        last = context.get("last_event")
        current_discard = self._resolve_current_discard(seat, context.get("last_discard"), last)
        if last and self._should_show_last_event(seat, last):
            tile = f" {self._pretty_tile(last['tile'])}" if last.get("tile") else ""
            frm = f" <- {self._seat_cn(last['from_player'])}" if last.get("from_player") else ""
            print(f"上一步: {self._seat_cn(last['player'])} {self._action_label(last['action'])}{tile}{frm}")
        else:
            print("上一步: (无)")

        discard_view = context.get("discard_view", {})
        recent = discard_view.get("recent_by_player", {})
        print("-" * width)
        print("弃牌区:")
        public_melds = context.get("public_melds", {})
        for s in ("E", "S", "W", "N"):
            tiles = recent.get(s, [])
            seat_label = f"{self._seat_cn(s)}(庄)" if context.get("dealer") == s else self._seat_cn(s)
            thinking = f"[{thinking_text or '思考中'}]" if thinking_seat == s else ""
            meld_summary = ""
            if s != seat:
                summary = self._format_meld_summary(public_melds, s)
                meld_summary = "" if summary == "(无)" else summary
            tile_text = self._tiles_text_cn_colored(tiles) if tiles else "(无)"
            line = f"  {seat_label:<6} | {tile_text}"
            if thinking:
                line = f"{line} {thinking}"
            if meld_summary:
                pad = max(1, width - len(line) - len(meld_summary))
                line = f"{line}{' ' * pad}{meld_summary}"
            print(line)

        history_tiles = discard_view.get("history_compact", [])
        if history_tiles:
            print("历史弃牌:")
            print("  " + self._tiles_text_cn_colored(history_tiles))
        else:
            print("历史弃牌: (无)")
        if current_discard:
            actor = self._seat_cn(current_discard["player"])
            print(f"{('当前打出: ' + actor + ' 出牌'):>{width}}")
            for box_line in self._tile_box(current_discard["tile"]):
                print(f"{box_line:>{width}}")

        print("-" * width)
        print(f"我的碰杠区: {self._format_meld_summary(public_melds, seat)}")
        print("-" * width)
        print(f"你的风位: {self._seat_cn(seat)} ({seat})")
        print("你的手牌:")
        indexed = context.get("indexed_hand", [])
        draw_split_index = context.get("draw_split_index")
        if indexed:
            labels = []
            for pos, (idx, tile) in enumerate(indexed):
                if draw_split_index is not None and pos == draw_split_index:
                    labels.append("  ")
                name = self._tile_text_cn(tile).center(7)
                if idx == selected_tile_index:
                    labels.append(self._paint(name, "yellow"))
                else:
                    labels.append(name)
            print("  " + "".join(labels))
            box_lines = self._render_box_lines([tile for _, tile in indexed], split_index=draw_split_index)
            for line in box_lines:
                print("  " + line)
        else:
            print("  (空)")

        if prompt:
            print("-" * width)
            print(prompt)
        print("=" * width)

    @staticmethod
    def _format_option(option: ActionOption) -> str:
        action = HumanAgent._action_label(option.action)
        if not option.tile:
            return action
        return f"{action}:{HumanAgent._pretty_tile(option.tile)}"

    @staticmethod
    def _pretty_tile(tile: str) -> str:
        return tile_text_cn(tile)

    @staticmethod
    def _render_box_lines(tiles: list[str], split_index: int | None = None) -> list[str]:
        if not tiles:
            return ["(无)"]

        boxes = [HumanAgent._tile_box(t) for t in tiles]
        merged: list[str] = []
        for row in range(5):
            parts: list[str] = []
            for idx, box in enumerate(boxes):
                if split_index is not None and idx == split_index:
                    parts.append("  ")
                parts.append(box[row])
            merged.append("".join(parts))
        return merged

    @staticmethod
    def _render_box_lines_raw(tiles: list[str], split_index: int | None = None) -> list[str]:
        if not tiles:
            return ["(无)"]

        boxes = [HumanAgent._tile_box_raw(t) for t in tiles]
        merged: list[str] = []
        for row in range(5):
            parts: list[str] = []
            for idx, box in enumerate(boxes):
                if split_index is not None and idx == split_index:
                    parts.append("  ")
                parts.append(box[row])
            merged.append("".join(parts))
        return merged

    @staticmethod
    def _tile_box(tile: str) -> list[str]:
        rows, color = HumanAgent._tile_face_rows(tile)
        colored_rows = [HumanAgent._paint(r, color) if color else r for r in rows]
        return [
            "┌─────┐",
            f"│{colored_rows[0]}│",
            f"│{colored_rows[1]}│",
            f"│{colored_rows[2]}│",
            "└─────┘",
        ]

    @staticmethod
    def _tile_box_raw(tile: str) -> list[str]:
        rows, _ = HumanAgent._tile_face_rows(tile)
        return [
            "┌─────┐",
            f"│{rows[0]}│",
            f"│{rows[1]}│",
            f"│{rows[2]}│",
            "└─────┘",
        ]

    @staticmethod
    def _tile_face_rows(tile: str) -> tuple[list[str], str | None]:
        honor = {
            "EW": ("東", "yellow"),
            "SW": ("南", "yellow"),
            "WW": ("西", "yellow"),
            "NW": ("北", "yellow"),
            "RD": ("中", "red"),
            "GD": ("发", "green"),
            "WB": ("白", "white"),
        }
        if tile in honor:
            txt, color = honor[tile]
            return ["     ", txt.center(5), "     "], color

        if len(tile) == 2 and tile[0].isdigit():
            n = int(tile[0])
            suit = tile[1]
            if suit == "B":
                return HumanAgent._tong_face(n), "cyan"
            if suit == "T":
                return HumanAgent._tiao_face(n), "green"

        return ["     ", tile[:5].center(5), "     "], None

    @staticmethod
    def _tong_face(n: int) -> list[str]:
        patterns = {
            1: ["     ", "  ●  ", "     "],
            2: [" ●   ", "     ", "   ● "],
            3: [" ●   ", "  ●  ", "   ● "],
            4: [" ● ● ", "     ", " ● ● "],
            5: [" ● ● ", "  ●  ", " ● ● "],
            6: [" ● ● ", " ● ● ", " ● ● "],
            7: [" ● ● ", "● ● ●", " ● ● "],
            8: ["● ● ●", " ● ● ", "● ● ●"],
            9: ["● ● ●", "● ● ●", "● ● ●"],
        }
        return patterns.get(n, ["     ", "  ?  ", "     "])

    @staticmethod
    def _tiao_face(n: int) -> list[str]:
        patterns = {
            1: ["  |  ", "  |  ", "  |  "],
            2: [" |   ", "     ", "   | "],
            3: [" |   ", "  |  ", "   | "],
            4: [" | | ", "     ", " | | "],
            5: [" | | ", "  |  ", " | | "],
            6: [" | | ", " | | ", " | | "],
            7: [" | | ", "| | |", " | | "],
            8: ["| | |", " | | ", "| | |"],
            9: ["| | |", "| | |", "| | |"],
        }
        return patterns.get(n, ["     ", "  ?  ", "     "])

    @staticmethod
    def _chunk(items: list, size: int) -> list[list]:
        return [items[i : i + size] for i in range(0, len(items), size)]

    @staticmethod
    def _ma_formula_lines() -> list[str]:
        return [
            "单张马分 = (牌面映射 + 1) x 100",
            "牌面映射: 一=10，东南西北中发白=5，其余按数字",
            "补摸: 摸到二索或二筒，加摸1张，允许连摸",
            "基础摸马: 无鬼自摸2张，其他1张",
        ]

    @staticmethod
    def _clear_screen() -> None:
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def _paint(text: str, color: str | None) -> str:
        if not _COLOR_ENABLED or not color:
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
    def _rich_style(color: str | None) -> str:
        mapping = {
            "red": "red",
            "green": "green",
            "yellow": "yellow",
            "cyan": "cyan",
            "white": "white",
        }
        return mapping.get(color or "", "white")

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

    @staticmethod
    def _llm_status_badge(llm_status: dict | None) -> tuple[str, str]:
        if not llm_status:
            return "未知", "white"
        code = str(llm_status.get("code", "unknown"))
        label = str(llm_status.get("label", "未知"))
        style_map = {
            "connected": "green",
            "partial": "yellow",
            "probing": "yellow",
            "failed": "red",
            "no_key": "red",
            "disabled": "white",
        }
        return label, style_map.get(code, "white")

    @staticmethod
    def _tiles_text_cn(tiles: list[str]) -> str:
        return "、".join(HumanAgent._tile_text_cn(t) for t in tiles)

    @staticmethod
    def _tiles_text_cn_colored(tiles: list[str]) -> str:
        parts: list[str] = []
        for tile in tiles:
            text = HumanAgent._tile_text_cn(tile)
            parts.append(HumanAgent._paint(text, HumanAgent._tile_color(tile)))
        return "、".join(parts)

    @staticmethod
    def _tiles_text_rich(tiles: list[str]) -> Text:
        text = Text()
        for idx, tile in enumerate(tiles):
            if idx > 0:
                text.append("、")
            text.append(HumanAgent._tile_text_cn(tile), style=HumanAgent._rich_style(HumanAgent._tile_color(tile)))
        return text

    @staticmethod
    def _tile_color(tile: str) -> str | None:
        honors = {
            "EW": "yellow",
            "SW": "yellow",
            "WW": "yellow",
            "NW": "yellow",
            "RD": "red",
            "GD": "green",
            "WB": "white",
        }
        if tile in honors:
            return honors[tile]
        if len(tile) == 2 and tile[0].isdigit():
            if tile[1] == "T":
                return "green"
            if tile[1] == "B":
                return "cyan"
            if tile[1] == "W":
                return "red"
        return None

    @staticmethod
    def _format_meld_summary(public_melds: dict[str, list[dict]], seat: str) -> str:
        melds = public_melds.get(seat) or []
        if not melds:
            return "(无)"

        chunks: list[str] = []
        for meld in melds:
            tiles = meld.get("tiles") or []
            if not tiles:
                continue
            chunks.append(" ".join(HumanAgent._tile_text_cn(tile) for tile in tiles))
        return " | ".join(chunks) if chunks else "(无)"

    @staticmethod
    def _seat_cn(seat: str | None) -> str:
        mapping = {"E": "东风", "S": "南风", "W": "西风", "N": "北风"}
        if seat is None:
            return "未知"
        return mapping.get(seat, str(seat))

    @staticmethod
    def _should_show_last_event(viewer_seat: str, last_event: dict[str, Any]) -> bool:
        actor = str(last_event.get("player") or "")
        action = str(last_event.get("action") or "")
        if actor != viewer_seat and action == "DRAW":
            return False
        return True

    @staticmethod
    def _current_discard_event(viewer_seat: str, last_event: dict[str, Any] | None) -> dict[str, str] | None:
        if not last_event:
            return None
        if not HumanAgent._should_show_last_event(viewer_seat, last_event):
            return None

        action = str(last_event.get("action") or "")
        actor = str(last_event.get("player") or "")
        tile = str(last_event.get("tile") or "")
        if action != DISCARD or not actor or not tile:
            return None
        return {"player": actor, "tile": tile}

    @staticmethod
    def _resolve_current_discard(
        viewer_seat: str,
        last_discard: tuple[str, str] | list[str] | None,
        last_event: dict[str, Any] | None,
    ) -> dict[str, str] | None:
        if isinstance(last_discard, (tuple, list)) and len(last_discard) == 2:
            actor = str(last_discard[0] or "")
            tile = str(last_discard[1] or "")
            if actor and tile:
                return {"player": actor, "tile": tile}
        return HumanAgent._current_discard_event(viewer_seat, last_event)

    @staticmethod
    def _tile_text_cn(tile: str) -> str:
        return tile_text_cn(tile)

    def _read_key(self) -> str:
        if os.name == "nt":
            import msvcrt

            while True:
                ch = msvcrt.getch()
                if ch in {b"\x00", b"\xe0"}:
                    ch2 = msvcrt.getch()
                    mapping = {b"K": "left", b"M": "right", b"H": "up", b"P": "down"}
                    if ch2 in mapping:
                        return mapping[ch2]
                    continue
                if ch in {b"\r", b"\n"}:
                    return "enter"
                if ch == b"\x1b":
                    return "esc"
                return ch.decode(errors="ignore").lower()

        # POSIX fallback
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                ch3 = sys.stdin.read(1)
                if ch2 == "[":
                    mapping = {"A": "up", "B": "down", "C": "right", "D": "left"}
                    return mapping.get(ch3, "esc")
                return "esc"
            if ch in {"\r", "\n"}:
                return "enter"
            return ch.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
