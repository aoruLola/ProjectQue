from maque.rules import HU, PENG, legal_actions_on_discard, legal_actions_on_qianggang
from maque.state import PlayerState


def test_discard_claim_has_no_hu_and_no_chi():
    player = PlayerState(seat="S", hand=["3T", "3T", "3T", "7B"])
    options = legal_actions_on_discard(player, "3T")
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
            "1T", "2T", "3T",
            "4T", "5T", "6T",
            "7T", "8T", "9T",
            "2B", "3B", "4B",
            "5B",
        ],
    )
    options = legal_actions_on_qianggang(player, "5B")
    actions = {o.action for o in options}
    assert HU in actions

