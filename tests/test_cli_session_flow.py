from argparse import Namespace
from types import SimpleNamespace

from maque.cli import run_play
from maque.engine import GameResult, WinContext
from maque.rules import HuResult
from maque.scoring import Settlement


class _DummyHuman:
    def __init__(self) -> None:
        self.render_calls = []
        self.ma_calls = []
        self.hu_wait_calls = []

    def render_view(self, *args, **kwargs):
        self.render_calls.append((args, kwargs))

    def render_ma_screen(self, **kwargs):
        self.ma_calls.append(kwargs)

    def render_hu_wait_screen(self, **kwargs):
        self.hu_wait_calls.append(kwargs)


class _DummyLogger:
    def __init__(self, _log_dir):
        self.path = "dummy.log"


class _FakeEngine:
    created = []
    round_index = 0

    def __init__(self, *args, dealer=None, **kwargs):
        self.dealer = dealer
        self.run_calls = []
        self.finalize_calls = 0
        _FakeEngine.created.append(self)

    def _build_context_for_seat(self, _state, _seat):
        return {
            "turn": 0,
            "dealer": self.dealer,
            "current": "E",
            "wall_count": 10,
            "last_event": None,
            "discard_view": {"recent_by_player": {"E": [], "S": [], "W": [], "N": []}, "history_compact": []},
            "indexed_hand": [],
            "public_melds": {"E": [], "S": [], "W": [], "N": []},
            "llm_status": {"code": "disabled", "label": "disabled", "last_error": ""},
        }

    def run(self, auto_settle=True):
        self.run_calls.append(auto_settle)
        idx = _FakeEngine.round_index
        _FakeEngine.round_index += 1

        winner = "S" if idx == 0 else "E"
        state = SimpleNamespace(
            winner=winner,
            win_source="zimo",
            wall=["1T", "2T", "3T"],
            players={
                "E": SimpleNamespace(hand=["1B", "2B", "3B"]),
                "S": SimpleNamespace(hand=["1T", "9T", "EW"]),
                "W": SimpleNamespace(hand=[]),
                "N": SimpleNamespace(hand=[]),
            },
        )
        ctx = WinContext(
            winner=winner,
            win_source="zimo",
            hu_result=HuResult(is_hu=True, pattern="normal", is_wugui=False, source="zimo"),
            baopei_payer=None,
            ma_count=1,
        )
        return GameResult(state=state, settlement=None, log_path=None, win_context=ctx)

    def finalize_settlement(self, state, win_context):
        self.finalize_calls += 1
        state.wall = state.wall[1:]
        if win_context.winner == "S":
            delta = {"E": -1, "S": 1, "W": 0, "N": 0}
        else:
            delta = {"E": 2, "S": -1, "W": -1, "N": 0}
        return Settlement(
            winner=win_context.winner,
            losers=["E", "W", "N"],
            base=1,
            multipliers=["normal", "ma_unit+11"],
            ma_tiles=["1T"],
            ma_unit_scores=[11],
            ma_unit_total=11,
            final_delta_by_player=delta,
            baopei_payer=None,
        )


def test_run_play_interactive_manual_settle_and_winner_is_next_dealer(monkeypatch, capsys, tmp_path):
    _FakeEngine.created = []
    _FakeEngine.round_index = 0

    monkeypatch.setattr("maque.cli.OpenAILLMAgent", lambda *args, **kwargs: object())
    human = _DummyHuman()
    monkeypatch.setattr("maque.cli.HumanAgent", lambda: human)
    monkeypatch.setattr("maque.cli.EventLogger", _DummyLogger)
    monkeypatch.setattr("maque.cli.MahjongEngine", _FakeEngine)
    monkeypatch.setattr("maque.cli._load_env_file", lambda *args, **kwargs: None)
    monkeypatch.setattr("maque.cli._show_start_screen", lambda *args, **kwargs: None)
    monkeypatch.setattr("maque.cli._show_table_setup", lambda *args, **kwargs: None)

    table_iter = iter([
        ("E", 1, 2, 111),
        ("W", 3, 4, 222),
    ])
    monkeypatch.setattr("maque.cli._table_setup", lambda seed=None: next(table_iter))

    input_iter = iter(["", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: next(input_iter))

    args = Namespace(model="gpt-4.1-mini", base_url=None, seed=42, log_dir=str(tmp_path), interactive=True)
    code = run_play(args)

    assert code == 0
    assert len(_FakeEngine.created) == 2
    assert _FakeEngine.created[0].dealer == "E"
    assert _FakeEngine.created[1].dealer == "S"
    assert _FakeEngine.created[0].run_calls == [False]
    assert _FakeEngine.created[1].run_calls == [False]
    assert _FakeEngine.created[0].finalize_calls == 1
    assert _FakeEngine.created[1].finalize_calls == 1
    assert len(human.hu_wait_calls) == 2
    assert len(human.ma_calls) == 2
    assert human.ma_calls[0]["winner_seat"] == "S"
    assert human.ma_calls[0]["ma_unit_scores"] == [11]
    assert human.ma_calls[0]["round_delta"] == {"E": -100, "S": 100, "W": 0, "N": 0}

    out = capsys.readouterr().out
    assert "Total Leaderboard" in out
    assert "E): +100" in out
    assert "S): +0" in out


def test_run_play_non_interactive_keeps_auto_settle(monkeypatch, tmp_path):
    _FakeEngine.created = []
    _FakeEngine.round_index = 0

    monkeypatch.setattr("maque.cli.OpenAILLMAgent", lambda *args, **kwargs: object())
    monkeypatch.setattr("maque.cli.EventLogger", _DummyLogger)
    monkeypatch.setattr("maque.cli.MahjongEngine", _FakeEngine)
    monkeypatch.setattr("maque.cli._load_env_file", lambda *args, **kwargs: None)
    monkeypatch.setattr("maque.cli._show_start_screen", lambda *args, **kwargs: None)
    monkeypatch.setattr("maque.cli._show_table_setup", lambda *args, **kwargs: None)
    monkeypatch.setattr("maque.cli._table_setup", lambda seed=None: ("E", 1, 2, 111))

    args = Namespace(model="gpt-4.1-mini", base_url=None, seed=42, log_dir=str(tmp_path), interactive=False)
    code = run_play(args)

    assert code == 0
    assert len(_FakeEngine.created) == 1
    assert _FakeEngine.created[0].run_calls == [True]
