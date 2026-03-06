from maque.agents.human import HumanAgent


def test_should_hide_other_players_draw_event():
    event = {"player": "S", "action": "DRAW", "tile": "8T"}
    assert HumanAgent._should_show_last_event("E", event) is False


def test_should_show_other_players_discard_event():
    event = {"player": "S", "action": "DISCARD", "tile": "8T"}
    assert HumanAgent._should_show_last_event("E", event) is True


def test_should_show_self_draw_event():
    event = {"player": "E", "action": "DRAW", "tile": "8T"}
    assert HumanAgent._should_show_last_event("E", event) is True


def test_current_discard_event_only_for_discard_action():
    draw_event = {"player": "S", "action": "DRAW", "tile": "8T"}
    assert HumanAgent._current_discard_event("E", draw_event) is None

    hu_event = {"player": "S", "action": "HU", "tile": "8T"}
    assert HumanAgent._current_discard_event("E", hu_event) is None


def test_current_discard_event_contains_actor_and_tile():
    event = {"player": "S", "action": "DISCARD", "tile": "8T"}
    current = HumanAgent._current_discard_event("E", event)
    assert current == {"player": "S", "tile": "8T"}


def test_resolve_current_discard_keeps_previous_discard_until_next_discard():
    last_discard = ("W", "3B")
    draw_event = {"player": "N", "action": "DRAW", "tile": "7T"}
    current = HumanAgent._resolve_current_discard("E", last_discard, draw_event)
    assert current == {"player": "W", "tile": "3B"}


def test_resolve_current_discard_falls_back_to_last_event():
    current = HumanAgent._resolve_current_discard("E", None, {"player": "S", "action": "DISCARD", "tile": "8T"})
    assert current == {"player": "S", "tile": "8T"}
