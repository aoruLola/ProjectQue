from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..agents.fallback import RuleSafeAgent
from ..agents.llm import OpenAILLMAgent
from ..cli import DEFAULT_PLAY_MODEL, _table_setup
from ..engine import MahjongEngine
from ..tiles import SEATS
from .human_agent import WebHumanAgent


def _ma_formula_lines() -> list[str]:
    return [
        "单张马分 = (牌面映射 + 1) x 100",
        "牌面映射: 一=10，东南西北中发白=5，其余按数字",
        "补摸: 摸到二索或二筒，加摸1张，允许连摸",
        "基础摸马: 无鬼自摸2张，其他1张",
    ]


@dataclass
class SessionConfig:
    model: str = DEFAULT_PLAY_MODEL
    base_url: str | None = None
    seed: int | None = None
    player_seat: str = "E"
    log_dir: str = "./logs"


class GameWebSession:
    def __init__(self, session_id: str, config: SessionConfig) -> None:
        self.session_id = session_id
        self.config = config

        self._state_lock = threading.Lock()
        self._control_cond = threading.Condition()
        self._events_lock = threading.Lock()

        self.phase = "starting"
        self.round_index = 0
        self.current_dealer = "E"
        self.leaderboard_total = {seat: 0 for seat in SEATS}
        self.round_delta = {seat: 0 for seat in SEATS}
        self.pending_options: list[dict[str, str | None]] = []
        self.last_context: dict[str, Any] | None = None
        self.last_prompt: str | None = None
        self.last_error: str | None = None

        self._dealer_override: str | None = None
        self._quit_requested = False
        self._start_ma_requested = False
        self._next_round_requested = False

        self._events: list[dict[str, Any]] = []
        self._next_seq = 1

        self._human_agent = WebHumanAgent(on_turn=self._on_human_turn)
        self._thread = threading.Thread(target=self._run_loop, name=f"maque-session-{session_id}", daemon=True)
        self._thread.start()

    def snapshot(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "session_id": self.session_id,
                "phase": self.phase,
                "round_index": self.round_index,
                "dealer": self.current_dealer,
                "leaderboard_total": dict(self.leaderboard_total),
                "round_delta": dict(self.round_delta),
                "pending_options": list(self.pending_options),
                "context": self.last_context,
                "prompt": self.last_prompt,
                "error": self.last_error,
            }

    def get_events_since(self, seq: int) -> tuple[list[dict[str, Any]], int]:
        with self._events_lock:
            events = [event for event in self._events if event["seq"] >= seq]
            return events, self._next_seq

    def submit_action(self, action: str, tile: str | None = None) -> tuple[bool, str | None]:
        ok, err = self._human_agent.submit_action(action=action, tile=tile)
        if not ok and err:
            self._set_error(err)
            self._push_event("error", {"message": err})
            self._push_state_update()
        return ok, err

    def request_start_ma(self) -> tuple[bool, str | None]:
        with self._control_cond:
            if self.phase != "hu_wait":
                return False, "当前不在买马前等待阶段"
            self._start_ma_requested = True
            self._control_cond.notify_all()
        return True, None

    def request_next_round(self) -> tuple[bool, str | None]:
        with self._control_cond:
            if self.phase not in {"ma_result", "round_end"}:
                return False, "当前不在可开下一局阶段"
            self._next_round_requested = True
            self._control_cond.notify_all()
        return True, None

    def request_quit(self) -> None:
        with self._control_cond:
            self._quit_requested = True
            self._control_cond.notify_all()
        self._human_agent.close()
        self._push_event("info", {"message": "会话结束"})

    def is_closed(self) -> bool:
        with self._control_cond:
            return self._quit_requested or self.phase == "finished"

    def _set_error(self, message: str | None) -> None:
        with self._state_lock:
            self.last_error = message

    def _set_phase(self, phase: str) -> None:
        with self._state_lock:
            self.phase = phase

    def _push_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with self._events_lock:
            event = {
                "seq": self._next_seq,
                "type": event_type,
                "payload": payload,
                "ts": time.time(),
            }
            self._events.append(event)
            self._next_seq += 1

    def _push_state_update(self) -> None:
        self._push_event("state_update", self.snapshot())

    def _on_human_turn(self, context: dict, serialized_options: list[dict[str, str | None]]) -> None:
        with self._state_lock:
            self.pending_options = serialized_options
            self.last_context = context
            self.last_prompt = "请选择动作"
        self._push_state_update()

    def _observer_renderer(self, context: dict, prompt: str | None) -> None:
        with self._state_lock:
            self.last_context = context
            self.last_prompt = prompt
        self._push_state_update()

    def _wait_until(self, predicate: callable) -> bool:
        with self._control_cond:
            while not predicate():
                if self._quit_requested:
                    return False
                self._control_cond.wait(timeout=0.25)
            return not self._quit_requested

    def _run_loop(self) -> None:
        Path(self.config.log_dir).mkdir(parents=True, exist_ok=True)
        fallback = RuleSafeAgent()

        while True:
            with self._control_cond:
                if self._quit_requested:
                    break

            round_seed = self.config.seed + self.round_index if self.config.seed is not None else None
            random_dealer, d1, d2, wall_seed = _table_setup(round_seed)
            dealer = self._dealer_override or random_dealer
            with self._state_lock:
                self.current_dealer = dealer
                self.round_delta = {seat: 0 for seat in SEATS}
                self.last_error = None

            self._set_phase("playing")
            self._push_event(
                "table_setup",
                {
                    "round_index": self.round_index,
                    "dealer": dealer,
                    "dice": [d1, d2],
                    "wall_seed": wall_seed,
                },
            )

            agents = {
                seat: (
                    self._human_agent
                    if seat == self.config.player_seat
                    else OpenAILLMAgent(model=self.config.model, fallback=fallback, base_url=self.config.base_url)
                )
                for seat in SEATS
            }

            engine = MahjongEngine(
                agents=agents,
                event_logger=None,
                seed=wall_seed,
                dealer=dealer,
                ai_seats={seat for seat in SEATS if seat != self.config.player_seat},
                ai_decision_wrapper=None,
                observer_seat=self.config.player_seat,
                observer_renderer=self._observer_renderer,
            )

            result = engine.run(auto_settle=False)
            with self._state_lock:
                self.last_context = engine._build_context_for_seat(result.state, self.config.player_seat)
            self._push_state_update()

            if result.win_context is None:
                self._set_phase("round_end")
                self._push_event("info", {"message": "流局"})
            else:
                winner = result.win_context.winner
                winner_hand = list(result.state.players[winner].hand)
                self._set_phase("hu_wait")
                self._push_event(
                    "hu_wait",
                    {
                        "winner_seat": winner,
                        "winner_hand": winner_hand,
                        "formula_lines": _ma_formula_lines(),
                    },
                )

                with self._control_cond:
                    self._start_ma_requested = False
                if not self._wait_until(lambda: self._start_ma_requested):
                    break

                settlement = engine.finalize_settlement(result.state, result.win_context)
                round_delta = {seat: settlement.final_delta_by_player.get(seat, 0) * 100 for seat in SEATS}
                with self._state_lock:
                    self.round_delta = round_delta
                    for seat in SEATS:
                        self.leaderboard_total[seat] += round_delta.get(seat, 0)
                self._set_phase("ma_result")
                self._push_event(
                    "ma_result",
                    {
                        "winner_seat": settlement.winner,
                        "winner_hand": list(result.state.players[settlement.winner].hand),
                        "ma_tiles": settlement.ma_tiles,
                        "ma_unit_scores": settlement.ma_unit_scores,
                        "round_delta": round_delta,
                        "leaderboard_total": dict(self.leaderboard_total),
                        "self_seat": self.config.player_seat,
                        "self_hand": list(result.state.players[self.config.player_seat].hand),
                    },
                )
                self._push_state_update()

            with self._control_cond:
                self._next_round_requested = False
            if not self._wait_until(lambda: self._next_round_requested):
                break

            self._round_advance(result.state.winner)

        self._set_phase("finished")
        self._push_state_update()
        self._push_event("info", {"message": "会话线程已退出"})

    def _round_advance(self, winner: str | None) -> None:
        self.round_index += 1
        self._dealer_override = winner if winner else None


class SessionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, GameWebSession] = {}

    def create_session(self, config: SessionConfig) -> GameWebSession:
        session_id = uuid.uuid4().hex[:12]
        session = GameWebSession(session_id=session_id, config=config)
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> GameWebSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

