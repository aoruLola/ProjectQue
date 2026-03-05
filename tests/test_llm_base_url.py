import sys
import types

from maque.agents.llm import OpenAILLMAgent
from maque.rules import ActionOption


class _FakeCompletions:
    def create(self, **kwargs):
        message = types.SimpleNamespace(content='{"action":"PASS","reason":"ok"}')
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
    decision = agent.decide("E", {"self_hand": ["1W"]}, [ActionOption("PASS")])

    assert decision.action == "PASS"
    assert _FakeOpenAI.last_kwargs["api_key"] == "dummy-key"
    assert _FakeOpenAI.last_kwargs["base_url"] == "https://example-proxy/v1"


def test_cli_base_url_overrides_env(monkeypatch):
    fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)

    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")
    monkeypatch.setenv("MAQUE_OPENAI_BASE_URL", "https://env-url/v1")

    agent = OpenAILLMAgent(model="gpt-4.1-mini", base_url="https://arg-url/v1")
    decision = agent.decide("E", {"self_hand": ["1W"]}, [ActionOption("PASS")])

    assert decision.action == "PASS"
    assert _FakeOpenAI.last_kwargs["base_url"] == "https://arg-url/v1"
