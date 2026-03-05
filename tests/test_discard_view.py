from maque.state import DiscardViewState


def test_discard_view_recent_two_and_history_compact():
    dv = DiscardViewState()

    dv.add_discard("E", "1W")
    dv.add_discard("E", "2W")
    dv.add_discard("E", "3W")

    assert list(dv.recent_by_player["E"]) == ["2W", "3W"]
    assert dv.history_compact == ["1W"]


def test_discard_view_history_is_tile_only():
    dv = DiscardViewState()
    for tile in ["1W", "2W", "3W", "4W"]:
        dv.add_discard("S", tile)

    assert dv.history_compact == ["1W", "2W"]
    assert all(isinstance(t, str) and ":" not in t for t in dv.history_compact)

