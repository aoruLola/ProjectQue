from __future__ import annotations

import argparse
from pathlib import Path

from .agents.fallback import RuleSafeAgent
from .agents.human import HumanAgent
from .agents.llm import OpenAILLMAgent
from .engine import MahjongEngine
from .logging.replay import EventLogger, ReplayView
from .tiles import SEATS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="maque", description="肇庆麻将 CLI（实验版）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    play = sub.add_parser("play", help="开始一局")
    play.add_argument("--model", default="gpt-4.1-mini")
    play.add_argument("--base-url", default=None, help="自定义 OpenAI 兼容接口地址")
    play.add_argument("--seed", type=int, default=None)
    play.add_argument("--log-dir", default="./logs")
    play.add_argument("--interactive", action="store_true")

    replay = sub.add_parser("replay", help="回放日志")
    replay.add_argument("--log", required=True)

    return parser


def run_play(args: argparse.Namespace) -> int:
    fallback = RuleSafeAgent()
    agents = {
        seat: OpenAILLMAgent(model=args.model, fallback=fallback, base_url=args.base_url)
        for seat in SEATS
    }

    if args.interactive:
        agents["E"] = HumanAgent()

    logger = EventLogger(args.log_dir)
    engine = MahjongEngine(agents=agents, event_logger=logger, seed=args.seed, dealer="E")
    result = engine.run()

    if result.settlement is None:
        print("结果: 流局（牌墙耗尽）")
    else:
        st = result.settlement
        print(f"结果: 胜者={st.winner} 包赔={st.baopei_payer or '无'}")
        print(f"加成: {', '.join(st.multipliers) if st.multipliers else '无'}")
        print(f"买马: {' '.join(st.ma_tiles) if st.ma_tiles else '(无)'}")
        print("分数变化:")
        for seat, score in st.final_delta_by_player.items():
            print(f"  {seat}: {score:+d}")

    if result.log_path:
        print(f"日志: {result.log_path}")
    return 0


def run_replay(args: argparse.Namespace) -> int:
    lines = ReplayView.replay(args.log)
    print(f"回放文件: {Path(args.log).resolve()}")
    for line in lines:
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "play":
        return run_play(args)
    if args.cmd == "replay":
        return run_replay(args)

    raise RuntimeError("unknown command")
