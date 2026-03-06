import sys
import types

from maque.agents.llm import OpenAILLMAgent
from maque.rules import ActionOption


class _FakeCompletions:
    response_content = '{"action":"PASS","reason":"ok"}'
    last_create_kwargs = None

    def create(self, **kwargs):
        _FakeCompletions.last_create_kwargs = kwargs
        message = types.SimpleNamespace(content=_FakeCompletions.response_content)
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])


class _FakeOpenAI:
    last_kwargs = None

    def __init__(self, **kwargs):
        _FakeOpenAI.last_kwargs = kwargs
        self.chat = types.SimpleNamespace(completions=_FakeCompletions())


def test_llm_uses_custom_base_url_env(monkeypatch):
    fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)

    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")
    monkeypatch.setenv("MAQUE_OPENAI_BASE_URL", "https://example-proxy/v1")

    agent = OpenAILLMAgent(model="gpt-4.1-mini")
    decision = agent.decide("E", {"self_hand": ["1T"]}, [ActionOption("PASS")])

    assert decision.action == "PASS"
    assert _FakeOpenAI.last_kwargs["api_key"] == "dummy-key"
    assert _FakeOpenAI.last_kwargs["base_url"] == "https://example-proxy/v1"


def test_cli_base_url_overrides_env(monkeypatch):
    fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)

    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")
    monkeypatch.setenv("MAQUE_OPENAI_BASE_URL", "https://env-url/v1")

    agent = OpenAILLMAgent(model="gpt-4.1-mini", base_url="https://arg-url/v1")
    decision = agent.decide("E", {"self_hand": ["1T"]}, [ActionOption("PASS")])

    assert decision.action == "PASS"
    assert _FakeOpenAI.last_kwargs["base_url"] == "https://arg-url/v1"


def test_llm_prompt_includes_house_rules(monkeypatch):
    fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")
    monkeypatch.setenv("MAQUE_OPENAI_BASE_URL", "https://example-proxy/v1")
    _FakeCompletions.response_content = '{"action":"PASS","reason":"ok"}'

    agent = OpenAILLMAgent(model="gpt-4.1-mini")
    decision = agent.decide("E", {"self_hand": ["WB", "1T"]}, [ActionOption("PASS")])

    assert decision.action == "PASS"
    user_payload = _FakeCompletions.last_create_kwargs["messages"][1]["content"]
    assert "house_rules" in user_payload
    assert "WB" in user_payload
    assert "ghost" in user_payload


def test_llm_discarding_ghost_is_overridden(monkeypatch):
    fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")
    _FakeCompletions.response_content = '{"action":"DISCARD","tile":"WB","reason":"test"}'

    agent = OpenAILLMAgent(model="gpt-4.1-mini")
    legal = [ActionOption("DISCARD", "WB"), ActionOption("DISCARD", "9B")]
    context = {"self_hand": ["WB", "9B"]}
    decision = agent.decide("E", context, legal)

    assert decision.action == "DISCARD"
    assert decision.tile == "9B"
    assert "ghost" in decision.reason.lower()
