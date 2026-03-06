from __future__ import annotations

import argparse
import os
import random
from pathlib import Path
from typing import Callable

from .agents.fallback import RuleSafeAgent
from .agents.human import HumanAgent
from .agents.llm import OpenAILLMAgent
from .engine import MahjongEngine
from .logging.replay import EventLogger, ReplayView
from .scoring import Settlement
from .tiles import SEATS, tile_text_cn

DEFAULT_PLAY_MODEL = "gpt-4.1-mini"

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    _RICH_ENABLED = True
except Exception:
    _RICH_ENABLED = False


def _seat_cn(seat: str | None) -> str:
    mapping = {"E": "东风", "S": "南风", "W": "西风", "N": "北风"}
    if seat is None:
        return "未知"
    return mapping.get(seat, str(seat))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="maque", description="肇庆麻将 CLI（实验版）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    play = sub.add_parser("play", help="开始一局")
    play.add_argument("--model", default=DEFAULT_PLAY_MODEL)
    play.add_argument("--base-url", default=None, help="自定义 OpenAI 兼容接口地址")
    play.add_argument("--seed", type=int, default=None)
    play.add_argument("--log-dir", default="./logs")
    play.add_argument("--interactive", action="store_true")

    replay = sub.add_parser("replay", help="回放日志")
    replay.add_argument("--log", required=True)

    web = sub.add_parser("web", help="启动手机网页端服务")
    web.add_argument("--host", default="0.0.0.0")
    web.add_argument("--port", type=int, default=8000)

    return parser


def _table_setup(seed: int | None = None) -> tuple[str, int, int, int]:
    rng: random.Random | random.SystemRandom
    if seed is None:
        rng = random.SystemRandom()
    else:
        rng = random.Random(seed)

    dealer = rng.choice(list(SEATS))
    d1 = rng.randint(1, 6)
    d2 = rng.randint(1, 6)
    # Keep dice as part of wall seed while adding high entropy to avoid
    # repeating only 36 possible shuffles across games.
    dice_component = d1 * 10 + d2
    entropy_component = rng.getrandbits(48)
    wall_seed = (dice_component << 48) | entropy_component
    return dealer, d1, d2, wall_seed


def _show_start_screen(interactive: bool) -> None:
    if not interactive:
        return

    if _RICH_ENABLED:
        console = Console()
        console.clear()
        button_text = Text(" 开始游戏 ", style="bold black on bright_green")
        panel = Panel(button_text, title="MAQUE", subtitle="按 Enter 开始")
        console.print(panel)
    else:
        os.system("cls" if os.name == "nt" else "clear")
        print("┌──────────────┐")
        print("│   开始游戏   │")
        print("└──────────────┘")
        print("按 Enter 开始")

    input()


def _show_table_setup(dealer: str, d1: int, d2: int, wall_seed: int, interactive: bool) -> None:
    msg = f"随机坐庄: {_seat_cn(dealer)}({dealer}) | 骰子: {d1}, {d2} | 牌墙种子: {wall_seed}"
    if _RICH_ENABLED:
        console = Console()
        console.print(Panel(msg, title="开局信息", border_style="yellow"))
    else:
        print(msg)

    if interactive:
        if _RICH_ENABLED:
            Console().print("按 Enter 继续...")
        else:
            print("按 Enter 继续...")
        input()


def _load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def _resolve_model_arg(model_arg: str) -> str:
    env_model = (os.getenv("MAQUE_MODEL") or "").strip()
    if model_arg == DEFAULT_PLAY_MODEL and env_model:
        return env_model
    return model_arg


def _build_ai_decision_wrapper(
    interactive: bool,
    human_agent: HumanAgent | None,
    human_seat: str,
) -> Callable[[str, dict, Callable[[], object]], object] | None:
    if not interactive:
        return None

    def wrapper(seat: str, observer_context: dict, decide_fn: Callable[[], object]) -> object:
        if human_agent is not None:
            human_agent.render_view(
                human_seat,
                observer_context,
                prompt=None,
                thinking_seat=seat,
                thinking_text="思考中",
            )
        return decide_fn()

    return wrapper


def _print_settlement(st: Settlement, scale: int = 1) -> None:
    winner_txt = f"{_seat_cn(st.winner)}({st.winner})"
    baopei_txt = f"{_seat_cn(st.baopei_payer)}({st.baopei_payer})" if st.baopei_payer else "无"
    print(f"结果: 胜者={winner_txt} 包赔={baopei_txt}")
    print(f"加成: {', '.join(st.multipliers) if st.multipliers else '无'}")
    print(f"买马: {' '.join(tile_text_cn(tile) for tile in st.ma_tiles) if st.ma_tiles else '(无)'}")
    print("分数变化:")
    for seat in SEATS:
        score = st.final_delta_by_player.get(seat, 0) * scale
        print(f"  {_seat_cn(seat)}({seat}): {score:+d}")


def _accumulate_scores(total_scores: dict[str, int], round_delta: dict[str, int], scale: int) -> None:
    for seat in SEATS:
        total_scores[seat] += round_delta.get(seat, 0) * scale


def _print_leaderboard(total_scores: dict[str, int]) -> None:
    print("Total Leaderboard:")
    for seat in SEATS:
        print(f"  {_seat_cn(seat)}({seat}): {total_scores[seat]:+d}")


def run_play(args: argparse.Namespace) -> int:
    _load_env_file()
    model = _resolve_model_arg(args.model)

    fallback = RuleSafeAgent()
    agents = {
        seat: OpenAILLMAgent(model=model, fallback=fallback, base_url=args.base_url)
        for seat in SEATS
    }

    human_seat = "E"
    human_agent: HumanAgent | None = None
    if args.interactive:
        human_agent = HumanAgent()
        agents[human_seat] = human_agent

    _show_start_screen(args.interactive)

    ai_seats = set(SEATS)
    if args.interactive:
        ai_seats.discard(human_seat)

    def observer_renderer(context: dict, prompt: str | None) -> None:
        if human_agent is not None:
            human_agent.render_view(human_seat, context, prompt=prompt)

    if not os.getenv("OPENAI_API_KEY"):
        print("提示: 未检测到 OPENAI_API_KEY，AI 已回退为规则引擎，不会产生 LLM 消耗。")

    total_scores = {seat: 0 for seat in SEATS}
    round_index = 0
    forced_dealer: str | None = None

    while True:
        round_seed = args.seed + round_index if args.seed is not None else None
        random_dealer, d1, d2, wall_seed = _table_setup(round_seed)
        dealer = forced_dealer or random_dealer
        _show_table_setup(dealer, d1, d2, wall_seed, args.interactive)

        logger = EventLogger(args.log_dir)
        engine = MahjongEngine(
            agents=agents,
            event_logger=logger,
            seed=wall_seed,
            dealer=dealer,
            ai_seats=ai_seats,
            ai_decision_wrapper=_build_ai_decision_wrapper(args.interactive, human_agent, human_seat),
            observer_seat=human_seat if args.interactive else None,
            observer_renderer=observer_renderer if args.interactive else None,
        )

        result = engine.run(auto_settle=not args.interactive)
        settlement = result.settlement

        if args.interactive and settlement is None and result.win_context is not None:
            if human_agent is not None:
                winner_hand = (
                    list(result.state.players.get(result.win_context.winner).hand)
                    if result.win_context.winner in result.state.players
                    else []
                )
                human_agent.render_hu_wait_screen(
                    winner_seat=result.win_context.winner,
                    winner_hand=winner_hand,
                )
            input()
            settlement = engine.finalize_settlement(result.state, result.win_context)

        if settlement is None:
            print("结果: 流局（牌墙耗尽）")
        else:
            scale = 100 if args.interactive else 1
            if args.interactive:
                round_delta = {seat: settlement.final_delta_by_player.get(seat, 0) * scale for seat in SEATS}
                _accumulate_scores(total_scores, settlement.final_delta_by_player, scale=scale)
                if human_agent is not None:
                    winner_hand = list(result.state.players.get(settlement.winner).hand) if settlement.winner in result.state.players else []
                    self_hand = list(result.state.players.get(human_seat).hand) if human_seat in result.state.players else []
                    human_agent.render_ma_screen(
                        winner_seat=settlement.winner,
                        winner_hand=winner_hand,
                        ma_tiles=settlement.ma_tiles,
                        ma_unit_scores=settlement.ma_unit_scores,
                        round_delta=round_delta,
                        leaderboard=total_scores,
                        self_seat=human_seat,
                        self_hand=self_hand,
                    )
                else:
                    _print_settlement(settlement, scale=scale)
                _print_leaderboard(total_scores)
            else:
                _print_settlement(settlement, scale=scale)

        if result.log_path:
            print(f"日志: {result.log_path}")

        if not args.interactive:
            break

        forced_dealer = result.state.winner if result.state.winner else None
        nxt = input("按 Enter 开始下一局，输入 Q 退出: ").strip().lower()
        if nxt == "q":
            break
        round_index += 1

    return 0


def run_replay(args: argparse.Namespace) -> int:
    lines = ReplayView.replay(args.log)
    print(f"回放文件: {Path(args.log).resolve()}")
    for line in lines:
        print(line)
    return 0


def run_web(args: argparse.Namespace) -> int:
    from .web.server import run_server

    run_server(host=args.host, port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "play":
        return run_play(args)
    if args.cmd == "replay":
        return run_replay(args)
    if args.cmd == "web":
        return run_web(args)

    raise RuntimeError("unknown command")
