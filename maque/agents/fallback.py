from __future__ import annotations

from collections import Counter

from ..rules import DISCARD, GANG_AN, GANG_JIA, GANG_MING, HU, PASS, ActionOption
from ..tiles import GHOST_TILE, sort_tiles
from .base import AgentDecision


class RuleSafeAgent:
    """Deterministic fallback policy to keep game progressing."""

    def decide(self, seat: str, context: dict, legal_options: list[ActionOption]) -> AgentDecision:
        actions = [opt.action for opt in legal_options]

        if HU in actions:
            return AgentDecision(action=HU, reason="legal hu available")

        option_by_action: dict[str, list[ActionOption]] = {}
        for opt in legal_options:
            option_by_action.setdefault(opt.action, []).append(opt)

        if GANG_MING in option_by_action:
            return AgentDecision(action=GANG_MING, tile=option_by_action[GANG_MING][0].tile, reason="prefer ming gang")

        if GANG_JIA in option_by_action:
            return AgentDecision(action=GANG_JIA, tile=option_by_action[GANG_JIA][0].tile, reason="prefer jia gang")

        if GANG_AN in option_by_action:
            return AgentDecision(action=GANG_AN, tile=option_by_action[GANG_AN][0].tile, reason="prefer an gang")

        if DISCARD in option_by_action:
            hand = context.get("self_hand", [])
            counter = Counter(hand)
            candidates = [t for t in sort_tiles(counter.keys()) if t != GHOST_TILE]
            tile = candidates[-1] if candidates else sort_tiles(counter.keys())[-1]
            return AgentDecision(action=DISCARD, tile=tile, reason="safe default discard")

        if PASS in actions:
            return AgentDecision(action=PASS, reason="no strong claim")

        first = legal_options[0]
        return AgentDecision(action=first.action, tile=first.tile, reason="first legal option")
