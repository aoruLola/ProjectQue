from maque.agents.human import HumanAgent
from maque.cli import _seat_cn


def test_cli_seat_cn_mapping():
    assert _seat_cn("E") == "东风"
    assert _seat_cn("S") == "南风"
    assert _seat_cn("W") == "西风"
    assert _seat_cn("N") == "北风"


def test_human_seat_cn_mapping():
    assert HumanAgent._seat_cn("E") == "东风"
    assert HumanAgent._seat_cn("S") == "南风"
    assert HumanAgent._seat_cn("W") == "西风"
    assert HumanAgent._seat_cn("N") == "北风"
