from maque.cli import _build_ai_decision_wrapper


class _DummyHuman:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def render_view(self, *args, **kwargs) -> None:
        self.calls.append({"args": args, "kwargs": kwargs})


def test_wrapper_not_built_when_non_interactive():
    wrapper = _build_ai_decision_wrapper(False, None, "E")
    assert wrapper is None


def test_wrapper_has_no_thinking_animation():
    human = _DummyHuman()
    wrapper = _build_ai_decision_wrapper(True, human, "E")
    assert wrapper is not None

    result = wrapper("S", {"turn": 1}, lambda: "ok")

    assert result == "ok"
    assert len(human.calls) == 1
    kwargs = human.calls[0]["kwargs"]
    assert kwargs["thinking_seat"] == "S"
    assert kwargs["thinking_text"] == "思考中"
