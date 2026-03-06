from maque.agents.base import AgentDecision
from maque.engine import MahjongEngine
from maque.rules import ActionOption, PASS
from maque.state import ActionEvent
from maque.tiles import SEATS


class _StubAgent:
    def __init__(self, decision: AgentDecision) -> None:
        self._decision = decision

    def decide(self, seat: str, context: dict, legal_options: list[ActionOption]) -> AgentDecision:
        return self._decision


def _build_agents(decision: AgentDecision) -> dict[str, _StubAgent]:
    return {seat: _StubAgent(decision) for seat in SEATS}


def test_context_marks_drawn_tile_as_right_side_group():
    agents = _build_agents(AgentDecision(action=PASS, reason="ok", raw=None))
    engine = MahjongEngine(agents=agents, seed=2026)
    state = engine.init_game()

    seat = state.current
    drawn_tile = state.players[seat].hand[0]
    engine._record_event(state, ActionEvent(turn=0, player=seat, action="DRAW", tile=drawn_tile))

    ctx = engine._build_context_for_seat(state, seat)
    assert ctx["draw_split_index"] == len(ctx["indexed_hand"]) - 1
    assert ctx["indexed_hand"][-1][1] == drawn_tile


def test_context_has_no_draw_split_without_draw_event():
    agents = _build_agents(AgentDecision(action=PASS, reason="ok", raw=None))
    engine = MahjongEngine(agents=agents, seed=2027)
    state = engine.init_game()

    ctx = engine._build_context_for_seat(state, state.current)
    assert ctx["draw_split_index"] is None
