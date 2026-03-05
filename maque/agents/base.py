from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..rules import ActionOption


@dataclass
class AgentDecision:
    action: str
    tile: str | None = None
    reason: str = ""
    raw: str | None = None


class Agent(Protocol):
    def decide(self, seat: str, context: dict, legal_options: list[ActionOption]) -> AgentDecision:
        ...
