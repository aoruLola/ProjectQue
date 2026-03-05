from pathlib import Path

from maque.agents.fallback import RuleSafeAgent
from maque.agents.llm import OpenAILLMAgent
from maque.engine import MahjongEngine
from maque.logging.replay import EventLogger, ReplayView
from maque.rules import ActionOption, DISCARD
from maque.tiles import SEATS


def test_fixed_seed_game_runs_to_completion(tmp_path: Path):
    agents = {seat: RuleSafeAgent() for seat in SEATS}
    logger = EventLogger(tmp_path)
    engine = MahjongEngine(agents=agents, event_logger=logger, seed=42)

    result = engine.run()

    assert result.state.events
    for seat in SEATS:
        assert len(result.state.discard_view.recent_by_player[seat]) <= 2

    if result.settlement:
        assert sum(result.settlement.final_delta_by_player.values()) == 0


def test_llm_agent_fallback_on_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    agent = OpenAILLMAgent(model="gpt-4.1-mini", fallback=RuleSafeAgent())
    legal = [ActionOption(DISCARD, "9W")]
    context = {"self_hand": ["9W", "1W"]}

    decision = agent.decide("E", context, legal)

    assert decision.action == DISCARD
    assert decision.tile == "9W"
    assert decision.raw is not None
    assert "LLM_ERROR" in decision.raw


def test_replay_reads_log(tmp_path: Path):
    agents = {seat: RuleSafeAgent() for seat in SEATS}
    logger = EventLogger(tmp_path)
    engine = MahjongEngine(agents=agents, event_logger=logger, seed=7)
    result = engine.run()

    assert result.log_path
    lines = ReplayView.replay(result.log_path)
    assert lines

