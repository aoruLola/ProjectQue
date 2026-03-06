from maque.cli import _resolve_model_arg


def test_resolve_model_uses_env_when_default(monkeypatch):
    monkeypatch.setenv("MAQUE_MODEL", "Pro/deepseek-ai/DeepSeek-V3.2")
    assert _resolve_model_arg("gpt-4.1-mini") == "Pro/deepseek-ai/DeepSeek-V3.2"


def test_resolve_model_keeps_explicit_arg(monkeypatch):
    monkeypatch.setenv("MAQUE_MODEL", "Pro/deepseek-ai/DeepSeek-V3.2")
    assert _resolve_model_arg("qwen/qwen3-32b") == "qwen/qwen3-32b"


def test_resolve_model_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("MAQUE_MODEL", raising=False)
    assert _resolve_model_arg("gpt-4.1-mini") == "gpt-4.1-mini"
