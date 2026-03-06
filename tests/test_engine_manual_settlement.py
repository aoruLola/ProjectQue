from maque.agents.base import AgentDecision
from maque.engine import MahjongEngine
from maque.rules import ActionOption, PASS
from maque.tiles import SEATS


class _StubAgent:
    def __init__(self, decision: AgentDecision) -> None:
        self._decision = decision

    def decide(self, seat: str, context: dict, legal_options: list[ActionOption]) -> AgentDecision:
        return self._decision


def _build_agents(decision: AgentDecision) -> dict[str, _StubAgent]:
    return {seat: _StubAgent(decision) for seat in SEATS}


def _force_win_phase(state):
    state.winner = state.current
    state.win_source = "zimo"
    return "done"


def test_run_auto_settle_false_keeps_wall_and_defers_settlement(monkeypatch):
    agents = _build_agents(AgentDecision(action=PASS, reason="ok", raw=None))
    engine = MahjongEngine(agents=agents, seed=123)
    seeded_state = engine.init_game()
    wall_before = list(seeded_state.wall)

    monkeypatch.setattr(engine, "init_game", lambda: seeded_state)
    monkeypatch.setattr(engine, "_process_after_draw_phase", _force_win_phase)

    result = engine.run(auto_settle=False)

    assert result.state.winner is not None
    assert result.settlement is None
    assert result.win_context is not None
    assert result.state.wall == wall_before


def test_finalize_settlement_draws_base_ma_count(monkeypatch):
    agents = _build_agents(AgentDecision(action=PASS, reason="ok", raw=None))
    engine = MahjongEngine(agents=agents, seed=456)
    seeded_state = engine.init_game()

    monkeypatch.setattr(engine, "init_game", lambda: seeded_state)
    monkeypatch.setattr(engine, "_process_after_draw_phase", _force_win_phase)

    result = engine.run(auto_settle=False)
    assert result.win_context is not None

    result.win_context.ma_count = 1
    seeded_state.wall = ["7T", "8T", "9T"]

    settlement = engine.finalize_settlement(seeded_state, result.win_context)

    assert settlement.ma_tiles == ["9T"]
    assert seeded_state.wall == ["7T", "8T"]


def test_finalize_settlement_chain_draw_when_ma_is_two(monkeypatch):
    agents = _build_agents(AgentDecision(action=PASS, reason="ok", raw=None))
    engine = MahjongEngine(agents=agents, seed=789)
    seeded_state = engine.init_game()

    monkeypatch.setattr(engine, "init_game", lambda: seeded_state)
    monkeypatch.setattr(engine, "_process_after_draw_phase", _force_win_phase)

    result = engine.run(auto_settle=False)
    assert result.win_context is not None

    result.win_context.ma_count = 1
    seeded_state.wall = ["5T", "9T", "2B", "2T"]

    settlement = engine.finalize_settlement(seeded_state, result.win_context)

    assert settlement.ma_tiles == ["2T", "2B", "9T"]
    assert seeded_state.wall == ["5T"]
    assert settlement.ma_unit_scores == [3, 3, 10]
    assert settlement.ma_unit_total == 16
