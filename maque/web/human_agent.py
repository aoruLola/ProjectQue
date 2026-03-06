from __future__ import annotations

import threading
from typing import Callable

from ..agents.base import AgentDecision
from ..rules import ActionOption, PASS


def serialize_options(legal_options: list[ActionOption]) -> list[dict[str, str | None]]:
    seen: set[tuple[str, str | None]] = set()
    result: list[dict[str, str | None]] = []
    for option in legal_options:
        key = (option.action, option.tile)
        if key in seen:
            continue
        seen.add(key)
        result.append({"action": option.action, "tile": option.tile})
    return result


class WebHumanAgent:
    def __init__(
        self,
        on_turn: Callable[[dict, list[dict[str, str | None]]], None],
    ) -> None:
        self._on_turn = on_turn
        self._cond = threading.Condition()
        self._pending_context: dict | None = None
        self._pending_options: list[ActionOption] = []
        self._pending_decision: AgentDecision | None = None
        self._closed = False

    def decide(self, seat: str, context: dict, legal_options: list[ActionOption]) -> AgentDecision:
        serialized = serialize_options(legal_options)
        with self._cond:
            self._pending_context = context
            self._pending_options = legal_options
            self._pending_decision = None
        self._on_turn(context, serialized)

        with self._cond:
            while self._pending_decision is None and not self._closed:
                self._cond.wait(timeout=0.2)

            decision = self._pending_decision
            self._pending_context = None
            self._pending_options = []
            self._pending_decision = None

        # Clear action area in UI after decision is consumed.
        self._on_turn(context, [])

        if decision is not None:
            return decision

        for option in legal_options:
            if option.action == PASS:
                return AgentDecision(action=PASS, reason="session closed")
        fallback = legal_options[0] if legal_options else ActionOption(PASS)
        return AgentDecision(action=fallback.action, tile=fallback.tile, reason="session closed")

    def submit_action(self, action: str, tile: str | None = None) -> tuple[bool, str | None]:
        action = str(action or "").strip().upper()
        tile = str(tile or "").strip().upper() or None

        with self._cond:
            if self._closed:
                return False, "会话已关闭"
            if not self._pending_options:
                return False, "当前没有等待中的玩家动作"

            legal = {(opt.action, opt.tile) for opt in self._pending_options}
            if (action, tile) not in legal:
                return False, "非法动作或牌面"

            self._pending_decision = AgentDecision(action=action, tile=tile, reason="web action")
            self._cond.notify_all()
            return True, None

    def pending_options(self) -> list[dict[str, str | None]]:
        with self._cond:
            return serialize_options(list(self._pending_options))

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()
