from maque.rules import HU, PENG, legal_actions_on_discard, legal_actions_on_qianggang
from maque.state import PlayerState


def test_discard_claim_has_no_hu_and_no_chi():
    player = PlayerState(seat="S", hand=["3W", "3W", "3W", "7T"])
    options = legal_actions_on_discard(player, "3W")
    actions = {o.action for o in options}
    assert "PASS" in actions
    assert PENG in actions
    assert "GANG_MING" in actions
    assert HU not in actions
    assert "CHI" not in actions


def test_qianggang_can_hu():
    player = PlayerState(
        seat="S",
        hand=[
            "1W", "2W", "3W",
            "4W", "5W", "6W",
            "7W", "8W", "9W",
            "2T", "3T", "4T",
            "5B",
        ],
    )
    options = legal_actions_on_qianggang(player, "5B")
    actions = {o.action for o in options}
    assert HU in actions

