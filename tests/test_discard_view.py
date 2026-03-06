from maque.state import DiscardViewState


def test_discard_view_recent_two_and_history_compact():
    dv = DiscardViewState()

    dv.add_discard("E", "1T")
    dv.add_discard("E", "2T")
    dv.add_discard("E", "3T")

    assert list(dv.recent_by_player["E"]) == ["2T", "3T"]
    assert dv.history_compact == ["1T", "2T", "3T"]


def test_discard_view_history_is_tile_only():
    dv = DiscardViewState()
    discards = [("S", "1T"), ("E", "2B"), ("S", "3T"), ("N", "4B")]
    for seat, tile in discards:
        dv.add_discard(seat, tile)

    assert dv.history_compact == ["1T", "2B", "3T", "4B"]
    assert all(isinstance(t, str) and ":" not in t for t in dv.history_compact)

