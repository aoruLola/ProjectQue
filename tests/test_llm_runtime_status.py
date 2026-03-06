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


def test_llm_status_shows_connected_after_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    agents = _build_agents(AgentDecision(action=PASS, reason="ok", raw='{"action":"PASS"}'))
    engine = MahjongEngine(agents=agents, ai_seats={"E"})
    state = engine.init_game()

    engine._decide("E", state, [ActionOption(PASS)])
    status = engine._build_context_for_seat(state, "E")["llm_status"]

    assert status["configured"] is True
    assert status["truly_connected"] is True
    assert status["code"] == "connected"


def test_llm_status_shows_fallback_after_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    agents = _build_agents(AgentDecision(action=PASS, reason="fb", raw="LLM_ERROR: timeout"))
    engine = MahjongEngine(agents=agents, ai_seats={"E"})
    state = engine.init_game()

    engine._decide("E", state, [ActionOption(PASS)])
    status = engine._build_context_for_seat(state, "E")["llm_status"]

    assert status["configured"] is True
    assert status["truly_connected"] is False
    assert status["code"] == "failed"
    assert "timeout" in status["last_error"]
    assert status["label"] == "已调用(回退中)"


def test_llm_status_shows_no_key_when_not_configured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    agents = _build_agents(AgentDecision(action=PASS, reason="ok", raw=None))
    engine = MahjongEngine(agents=agents, ai_seats={"E"})
    state = engine.init_game()

    status = engine._build_context_for_seat(state, "E")["llm_status"]
    assert status["configured"] is False
    assert status["truly_connected"] is False
    assert status["code"] == "no_key"
    assert "OPENAI_API_KEY" in status["last_error"]


def test_llm_status_probing_before_first_attempt(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    agents = _build_agents(AgentDecision(action=PASS, reason="ok", raw=None))
    engine = MahjongEngine(agents=agents, ai_seats={"E"})
    state = engine.init_game()

    status = engine._build_context_for_seat(state, "E")["llm_status"]
    assert status["code"] == "probing"
    assert status["label"] == "已配置(待调用)"


def test_llm_status_not_pending_after_ai_action_event(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    agents = _build_agents(AgentDecision(action=PASS, reason="ok", raw=None))
    engine = MahjongEngine(agents=agents, ai_seats={"E"})
    state = engine.init_game()

    engine._record_event(
        state,
        ActionEvent(turn=0, player="E", action="DISCARD", tile="1T"),
    )
    status = engine._build_context_for_seat(state, "E")["llm_status"]
    assert status["label"] != "已配置(待调用)"
